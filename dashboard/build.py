"""Baut das Briefing-Dashboard (eine einzelne HTML-Datei) aus
  - dashboard/briefing.json   (von der Routine geschrieben: Depot, Signale, News, Termine …)
  - atlas-snapshot/*.json     (vom GitHub-Workflow geschrieben: Markt, Makro, Stimmung, Risiko)

Nur Standardbibliothek. Depotwerte, Gewichtungen und Allokation rechnet dieses Skript selbst
aus Stückzahl × Kurs, damit keine Zahl von Hand übertragen werden muss.

  python dashboard/build.py
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
KERN_KINDS = set(SETTINGS["strategy"].get("kern_kinds", ["ETF-Kern"]))
MAX_SINGLE_STOCK_PCT = float(SETTINGS["strategy"]["max_single_stock_pct"])
LEVEL_NEAR_PCT = float(SETTINGS["thresholds"].get("level_near_pct", 2))


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def depot_block(depot):
    """Ergänzt value_eur, weight_pct und die Allokation Kern/Satellit."""
    if not depot:
        return None
    positions = depot.get("positions", [])
    for p in positions:
        if p.get("value_eur") is None and p.get("qty") is not None and p.get("price") is not None:
            p["value_eur"] = p["qty"] * p["price"]
    invested = sum(p.get("value_eur") or 0 for p in positions)
    cash = depot.get("cash_eur") or 0
    total = invested + cash
    for p in positions:
        p["weight_pct"] = (p["value_eur"] / total * 100) if total and p.get("value_eur") is not None else None
        p["over_limit"] = p.get("kind") == "Aktie" and (p["weight_pct"] or 0) > MAX_SINGLE_STOCK_PCT
    positions.sort(key=lambda p: p.get("value_eur") or 0, reverse=True)
    kern = sum(p["value_eur"] or 0 for p in positions if p.get("kind") in KERN_KINDS)
    sat = invested - kern
    depot["computed"] = {
        "invested_eur": invested, "total_eur": total,
        "kern_pct": kern / invested * 100 if invested else None,
        "satellit_pct": sat / invested * 100 if invested else None,
        "max_single_stock_pct": MAX_SINGLE_STOCK_PCT,
        "check_vs_reported": (depot.get("reported_total_eur") - total) if depot.get("reported_total_eur") else None,
    }
    return depot


def levels_block(levels):
    """Abstand Kurs → Level und Status (erreicht / nah ≤ 2 % / offen) aus Kurs und Level berechnen."""
    for lv in levels or []:
        price, level = lv.get("price"), lv.get("level")
        if not isinstance(price, (int, float)) or not isinstance(level, (int, float)) or not price:
            continue
        lv["distance_pct"] = (level / price - 1) * 100
        down = lv.get("direction", "DOWN") == "DOWN"
        crossed = price <= level if down else price >= level
        lv["status"] = "erreicht" if crossed else ("nah" if abs(lv["distance_pct"]) <= LEVEL_NEAR_PCT else "offen")
    return sorted(levels or [], key=lambda x: abs(x.get("distance_pct") or 999))


def atlas_block(snap: Path):
    meta = load(snap / "meta.json")
    if meta is None:
        return {"available": False, "error": f"Kein Snapshot unter {snap}"}
    briefing = load(snap / "briefing.json", {})
    risk = load(snap / "risk.json", {})
    names = meta.get("names") or {}
    groups = meta.get("market_groups") or {"USA": ["SPY", "QQQ", "DIA", "IWM", "^VIX"]}
    overview = {}
    for g, tickers in groups.items():
        for t in tickers:
            q = (briefing.get("quotes") or {}).get(t) or {}
            overview[t] = {k: q.get(k) for k in ("price", "change", "change_pct", "currency", "updated_at", "error")}
            overview[t].update(name=names.get(t, t), group=g)
    sentiment = {}
    for t, s in (briefing.get("news_sentiment") or {}).items():
        avg = s.get("average") if isinstance(s, dict) else None
        sentiment[t] = ({"label": avg["label"], "label_de": avg["label_de"], "net": avg["net_score"],
                         "n": avg["n"], "updated_at": s.get("updated_at")}
                        if avg else {"error": s.get("error") if isinstance(s, dict) else "keine Daten"})
    universe = meta.get("universe") or []
    region_of = {t: r for r, ts in (meta.get("universe_regions") or {}).items() for t in ts}
    trends = {}
    for t in universe:
        q = load(snap / (meta.get("files") or {}).get(t, f"quote/{t}.json"), {})
        h = q.get("history") or {}
        if h.get("available") and (h.get("data") or {}).get("summary"):
            trends[t] = dict(h["data"]["summary"], name=names.get(t, t), region=region_of.get(t, ""),
                             currency=((q.get("quote") or {}).get("data") or {}).get("currency"))
    return {
        "available": True,
        "generated_at": meta.get("generated_at"),
        "slot": meta.get("slot"),
        "failed_sources": meta.get("failed_sources", []),
        "overview": overview,
        "macro": briefing.get("macro") or {},
        "sentiment": sentiment,
        "trends": trends,
        "risk": (risk.get("data") or {}).get("rows") if risk.get("available") else None,
        "risk_error": None if risk.get("available") else risk.get("error"),
        "benchmark": (risk.get("data") or {}).get("benchmark") or {"ticker": meta.get("benchmark")},
        "risk_free_series": meta.get("risk_free_series", "ECBDFR"),
        "groups": list(groups),
    }


def _obs(resp):
    """Neueste gültige Beobachtung aus einer fred-get-series-observations-Antwort (desc sortiert)."""
    rows = []
    for o in (resp or {}).get("observations") or []:
        date, val = (o[0], o[1]) if isinstance(o, (list, tuple)) else (o.get("date"), o.get("value"))
        try:
            rows.append({"date": date, "value": float(val)})
        except (TypeError, ValueError):
            continue  # FRED markiert fehlende Werte mit "."
    return sorted(rows, key=lambda r: r["date"], reverse=True)


def merge_fred_connector(atlas, fred):
    """Ergänzt Makrowerte und Sharpe aus dashboard/fred.json (FRED-Connector), wo der Snapshot
    keine FRED-Daten hat. Werte werden nur übernommen, nie geschätzt."""
    if not fred or not atlas.get("available"):
        return atlas
    src = "FRED"
    series = fred.get("series") or {}
    macro = atlas.setdefault("macro", {})
    latest = {k: (_obs(v) or [None])[0] for k, v in series.items()}
    for key in ("DFF", "DGS3MO", "DGS2", "DGS10", "CPI_YOY", "UNRATE", "ECBDFR", "HICP_YOY", "BUND10"):
        snap = macro.get(key) or {}
        conn = latest.get(key)
        if conn and (snap.get("error") or snap.get("value") is None or conn["date"] > snap.get("date", "")):
            macro[key] = dict(conn, source=src)
    d10, d2 = latest.get("DGS10"), latest.get("DGS2")
    s = macro.get("2s10s") or {}
    if d10 and d2 and d10["date"] == d2["date"] and (s.get("error") or s.get("value") is None or d10["date"] > s.get("date", "")):
        macro["2s10s"] = {"date": d10["date"], "value": d10["value"] - d2["value"], "source": f"{src} (DGS10 − DGS2)"}
    rf = latest.get(atlas.get("risk_free_series", "ECBDFR"))
    if rf and atlas.get("risk"):
        for r in atlas["risk"]:
            # gleiche Definition wie im Terminal: (ann. Rendite − EZB-Einlagenzins/100) / ann. Volatilität
            if r.get("sharpe") is None and r.get("ann_vol"):
                r["sharpe"] = (r["ann_return"] - rf["value"] / 100) / r["ann_vol"]
                r["sharpe_rf"] = {"value": rf["value"], "date": rf["date"], "source": src}
    # FRED gilt nicht als ausgefallen, wenn alle Makrowerte vorliegen (egal über welchen Weg)
    if all((macro.get(k) or {}).get("value") is not None for k in ("DFF", "DGS10", "2s10s", "CPI_YOY")):
        atlas["failed_sources"] = [k for k in atlas.get("failed_sources", []) if not k.startswith("fred:")]
        for k in list(macro):
            macro[k].pop("source", None)
    return atlas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefing", default=str(ROOT / "dashboard" / "briefing.json"))
    ap.add_argument("--fred", default=str(ROOT / "dashboard" / "fred.json"))
    ap.add_argument("--snapshot", default=str(ROOT / "atlas-snapshot"))
    ap.add_argument("--template", default=str(ROOT / "dashboard" / "template.html"))
    ap.add_argument("--out", default=str(ROOT / "dashboard" / "atlas-briefing.html"))
    args = ap.parse_args()

    b = load(Path(args.briefing))
    if b is None:
        raise SystemExit(f"{args.briefing} fehlt")
    b["depot"] = depot_block(b.get("depot"))
    b["target_kern_pct"] = SETTINGS["strategy"]["target_kern_pct"]
    b["price_alert_limit"] = SETTINGS.get("price_alert_limit")
    b["levels"] = levels_block(b.get("levels"))
    b["atlas"] = merge_fred_connector(atlas_block(Path(args.snapshot)), load(Path(args.fred)))
    b["built_at"] = datetime.now(timezone.utc).isoformat()

    payload = json.dumps(b, ensure_ascii=False, default=str).replace("</", "<\\/")
    html = Path(args.template).read_text(encoding="utf-8").replace("/*__BRIEFING_DATA__*/{}", payload)
    if "/*__BRIEFING_DATA__*/" in html:
        raise SystemExit("Platzhalter im Template nicht ersetzt")
    Path(args.out).write_text(html, encoding="utf-8")
    c = (b["depot"] or {}).get("computed") or {}
    print(f"Dashboard geschrieben: {args.out} · Depot {c.get('total_eur', 0):,.2f} € · "
          f"Kern {c.get('kern_pct') or 0:.1f} % / Satellit {c.get('satellit_pct') or 0:.1f} % · "
          f"Abweichung zu Scalable {c.get('check_vs_reported')}")


if __name__ == "__main__":
    main()
