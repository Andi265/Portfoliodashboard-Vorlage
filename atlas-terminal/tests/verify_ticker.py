"""Abgleich eines Tickers: Datenbank/API gegen eine unabhängige manuelle Rechnung
auf frisch aus yfinance geladenen Daten.

  python -m tests.verify_ticker AAPL
"""
import math
import sys

import yfinance as yf

from app import db
from app.fetchers import market
from app.main import compute_risk, quote

TOL_PRICE = 1e-6
TOL_VOL = 1e-9


def manual_vol(adj_closes):
    """Reine Python-Rechnung ohne numpy: Log-Renditen, Stichproben-Std, * sqrt(252)."""
    r = [math.log(adj_closes[i] / adj_closes[i - 1]) for i in range(1, len(adj_closes))]
    mean = sum(r) / len(r)
    var = sum((x - mean) ** 2 for x in r) / (len(r) - 1)
    return math.sqrt(var) * math.sqrt(252), len(r)


def main(t="AAPL"):
    db.init_db()
    ok = True

    # 1) Aktueller Kurs: Job schreibt in die DB, API liest ihn – Vergleich mit direktem yfinance-Abruf
    market.refresh_quotes([t])
    api_q = quote(t, range="1Y")["quote"]
    fresh_price = float(yf.Ticker(t).fast_info["lastPrice"])
    db_price = api_q["data"]["price"]
    d = abs(db_price - fresh_price)
    print(f"[Kurs]       DB/API {db_price:.4f}  |  yfinance jetzt {fresh_price:.4f}  |  Δ {d:.6f}")
    print(f"             DB-Stand {api_q['updated_at']}")
    if d > TOL_PRICE:
        print("             HINWEIS: Abweichung, weil sich der verzögerte Kurs seit dem letzten Job bewegt hat.")
        ok = ok and False

    # 2) 1-Jahres-Volatilität: API vs. manuelle Rechnung auf denselben gespeicherten yfinance-Daten
    hist = db.load(f"history:{t}")["data"]
    risk = compute_risk([t])
    row = next(r for r in risk["rows"] if r["ticker"] == t)
    api_vol = row["ann_vol"]
    w = row["window"]
    window = [r["adj_close"] for r in hist if w["start"] <= r["date"] <= w["end"]]
    man_vol, n = manual_vol(window)
    print(f"[Vol 1J]     API {api_vol:.10f}  |  manuell {man_vol:.10f}  |  Δ {abs(api_vol - man_vol):.2e}  ({n} Renditen, {w['start']}–{w['end']})")
    ok = ok and abs(api_vol - man_vol) < TOL_VOL

    # 3) Gespeicherte Historie vs. frischer yfinance-Download (gleiche Daten?)
    df = yf.Ticker(t).history(period="2y", interval="1d", auto_adjust=False, actions=False)
    fresh = {i.strftime("%Y-%m-%d"): float(v) for i, v in df["Adj Close"].items()}
    common = [r for r in hist if r["date"] in fresh and w["start"] <= r["date"] <= w["end"]]
    maxdiff = max(abs(r["adj_close"] - fresh[r["date"]]) / fresh[r["date"]] for r in common)
    fresh_vol, _ = manual_vol([fresh[r["date"]] for r in common])
    print(f"[Historie]   {len(common)} gemeinsame Tage, max. rel. Abweichung DB vs. frisch {maxdiff:.2e}")
    print(f"[Vol frisch] manuell auf frischem Download {fresh_vol:.10f}  |  Δ zu API {abs(fresh_vol - api_vol):.2e}")
    print("ERGEBNIS:", "ÜBEREINSTIMMUNG" if ok else "ABWEICHUNG (siehe oben)")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else "AAPL") else 1)
