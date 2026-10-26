"""Snapshot-Export für GitHub Actions: Daten abrufen und als JSON-Dateien schreiben.

  python -m app.export --out ../atlas-snapshot --slot auto     # Zeitfenster prüfen (Workflow)
  python -m app.export --out ../atlas-snapshot --slot manual   # immer ausführen

Die Routinen lesen nur diese Dateien. Jede Datei enthält Quelle, Zeitstempel und Fehler
je Datenpunkt; fehlgeschlagene Quellen erscheinen als "available": false mit Fehlertext.
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import (BENCHMARK, MARKET_GROUPS, MARKET_OVERVIEW, NAMES, RISK_FREE_SERIES, SEC_TICKERS, UNIVERSE,
                     UNIVERSE_REGIONS)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # Repo-Wurzel für settings.py
import settings as user_settings  # noqa: E402

_CFG = user_settings.load()
BERLIN = ZoneInfo(_CFG["timezone"])  # Zeitzone des Nutzers (Name historisch)
log = logging.getLogger("atlas.export")

# Cron läuft in UTC; der Workflow startet je Slot zweimal (Sommer-/Winterzeit).
# Ein Lauf zählt, wenn er nach Slot-Beginn (Berliner Zeit) startet und der Slot heute noch fehlt.
SLOTS = user_settings.slots(_CFG)  # aus den Routine-Zeiten in settings.json abgeleitet


def current_slot(now):
    for name, (start, end) in SLOTS.items():
        if start <= now.time() < end:
            return name
    return None


def quote_summary(q, keep_days=60):
    """Kennzahlen aus der 1-Jahres-Historie plus die letzten `keep_days` Handelstage."""
    h = q["history"]
    if not h["available"]:
        return q
    rows = h["data"]["rows"]
    last = rows[-1]

    def perf(n):
        if len(rows) <= n:
            return None
        base = rows[-1 - n]["adj_close"]
        return (last["adj_close"] / base - 1) * 100 if base else None

    h["data"]["summary"] = {
        "date": last["date"], "close": last["close"],
        "sma50": last["sma50"], "sma200": last["sma200"],
        "above_sma50": last["sma50"] is not None and last["close"] > last["sma50"],
        "above_sma200": last["sma200"] is not None and last["close"] > last["sma200"],
        "perf_1m_pct": perf(21), "perf_6m_pct": perf(126), "perf_1y_pct": perf(len(rows) - 1),
        "high_52w": h["data"]["high_52w"], "low_52w": h["data"]["low_52w"],
        "pct_below_52w_high": (last["close"] / h["data"]["high_52w"] - 1) * 100,
        "basis": "Performance auf bereinigten Schlusskursen; SMA auf Schlusskursen",
    }
    h["data"]["rows"] = rows[-keep_days:]
    return q


ALL = list(dict.fromkeys(UNIVERSE + MARKET_OVERVIEW))


def safe_name(t):
    """Dateiname für Ticker wie ^GDAXI, EURUSD=X, GC=F."""
    return t.replace("^", "").replace("=", "_")


def write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="atlas-snapshot")
    ap.add_argument("--slot", default="auto", help="auto | manual | morgen | abend")
    ap.add_argument("--check", action="store_true",
                    help="nur prüfen, ob ein Lauf fällig ist (schreibt run=true/false nach $GITHUB_OUTPUT)")
    args = ap.parse_args()
    out = Path(args.out)

    now = datetime.now(BERLIN)
    # "request": von einer Routine angefordert -> immer ausführen; liegt die Zeit in einem Slot, zählt er als erledigt
    slot = current_slot(now) if args.slot in ("auto", "request") else args.slot
    if args.slot == "request" and slot is None:
        slot = "request"
    meta_path = out / "meta.json"
    prev = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    due = True
    if args.slot == "auto":
        if slot is None:
            print(f"Kein Slot um {now:%H:%M} Berliner Zeit – übersprungen (Sommer-/Winterzeit-Duplikat).")
            due = False
        elif prev.get("slots", {}).get(slot) == now.date().isoformat():
            print(f"Slot {slot} für {now.date()} existiert bereits – übersprungen.")
            due = False
    if args.check:
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a", encoding="utf-8") as f:
                f.write(f"run={'true' if due else 'false'}\n")
        print(f"run={'true' if due else 'false'} (Slot {slot}, {now:%Y-%m-%d %H:%M} Berlin)")
        return 0
    if not due:
        return 0

    # Schwere Importe erst hier, damit --check ohne Abhängigkeiten läuft
    from . import db, jobs
    from .fetchers import fred, sec

    db.init_db()
    # Einträge zu Tickern, die nicht mehr im Universum/der Übersicht sind, entfernen
    for prefix, keep in (("quote:", ALL), ("history:", ALL), ("news:", UNIVERSE), ("fa:", SEC_TICKERS)):
        db.delete_prefix_except(prefix, {prefix + t for t in keep})
    jobs.job_prices(force=True)
    jobs.job_news()
    fred.refresh_all()
    sec.refresh(UNIVERSE)

    from . import main as api  # liest ausschließlich aus der DB
    write(out / "briefing.json", api.briefing(",".join(UNIVERSE)))
    write(out / "markets.json", api.markets(",".join(UNIVERSE)))
    write(out / "risk.json", api.risk(",".join(UNIVERSE)))
    write(out / "eco.json", api.eco())
    write(out / "news.json", api.news_api(",".join(UNIVERSE)))
    for sub in ("quote", "fa"):  # alte Dateien entfernter Ticker nicht stehen lassen
        for f in (out / sub).glob("*.json"):
            f.unlink()
    for t in ALL:
        write(out / "quote" / f"{safe_name(t)}.json", quote_summary(api.quote(t, range="1Y")))
        if t in SEC_TICKERS:
            write(out / "fa" / f"{safe_name(t)}.json", api.fundamentals(t))
    status = db.status_all()
    write(out / "status.json", status)

    slots = prev.get("slots", {})
    if slot in SLOTS:
        slots[slot] = now.date().isoformat()
    failed = [s["key"] for s in status if s["error"]]
    write(meta_path, {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_at_local": datetime.now(BERLIN).isoformat(),
        "timezone": _CFG["timezone"],
        "slot": slot,
        "slots": slots,
        "failed_sources": failed,
        "universe": UNIVERSE,
        "universe_regions": UNIVERSE_REGIONS,
        "market_groups": MARKET_GROUPS,
        "names": NAMES,
        "files": {t: f"quote/{safe_name(t)}.json" for t in ALL},
        "benchmark": BENCHMARK,
        "risk_free_series": RISK_FREE_SERIES,
        "note": "Kurse verzögert (delayed). Quellen: Yahoo Finance (yfinance), Google News RSS, "
                "SEC EDGAR, FRED, FinBERT (ProsusAI/finbert).",
    })
    print(f"Snapshot geschrieben nach {out} (Slot {slot}); fehlgeschlagen: {failed or 'keine'}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
