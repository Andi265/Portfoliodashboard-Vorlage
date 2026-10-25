"""Risikokennzahlen exakt nach Spezifikation (Tagesdaten, letzte 252 Handelstage)."""
import math

import numpy as np

TRADING_DAYS = 252


def log_returns(prices):
    """r_t = ln(P_t / P_{t-1}) auf Basis bereinigter Schlusskurse."""
    p = np.asarray(prices, dtype=float)
    return np.log(p[1:] / p[:-1])


def annualized_volatility(r):
    """std(r) * sqrt(252), Stichproben-Standardabweichung (ddof=1)."""
    return float(np.std(np.asarray(r, dtype=float), ddof=1) * math.sqrt(TRADING_DAYS))


def annualized_return(r):
    """mean(r) * 252."""
    return float(np.mean(np.asarray(r, dtype=float)) * TRADING_DAYS)


def sharpe_ratio(r, risk_free):
    """(annualisierte Rendite - rf) / annualisierte Volatilität; rf = DGS3MO / 100."""
    vol = annualized_volatility(r)
    if vol == 0:
        return float("nan")
    return (annualized_return(r) - risk_free) / vol


def beta(r_asset, r_market):
    """Cov(r_Aktie, r_SPY) / Var(r_SPY), beide mit ddof=1."""
    a = np.asarray(r_asset, dtype=float)
    m = np.asarray(r_market, dtype=float)
    cov = np.cov(a, m, ddof=1)[0, 1]
    var = np.var(m, ddof=1)
    return float(cov / var)


def max_drawdown(prices):
    """Größter Rückgang vom laufenden Hoch zum Tief, als negativer Anteil (z. B. -0.25)."""
    p = np.asarray(prices, dtype=float)
    running_max = np.maximum.accumulate(p)
    return float(np.min(p / running_max - 1.0))


def correlation_matrix(returns_by_ticker: dict):
    """Pearson-Korrelation der täglichen Renditen (gleich lange, datumsgleiche Reihen)."""
    tickers = list(returns_by_ticker)
    mat = np.corrcoef(np.vstack([returns_by_ticker[t] for t in tickers]))
    return tickers, mat.tolist()


def last_window(rows, window: int = TRADING_DAYS + 1):
    """Eigene letzte `window` Handelstage eines Werts (252 Renditen = 253 Kurse)."""
    rows = [r for r in rows if r.get("adj_close") is not None][-window:]
    return [r["date"] for r in rows], [r["adj_close"] for r in rows]


def align_on_dates(histories: dict, window: int = TRADING_DAYS + 1):
    """Richtet bereinigte Schlusskurse mehrerer Ticker auf gemeinsame Handelstage aus
    und nimmt die letzten `window` Tage (252 Renditen = 253 Kurse)."""
    common = None
    for rows in histories.values():
        dates = {r["date"] for r in rows if r.get("adj_close") is not None}
        common = dates if common is None else common & dates
    dates = sorted(common or [])[-window:]
    aligned = {}
    for t, rows in histories.items():
        by_date = {r["date"]: r["adj_close"] for r in rows}
        aligned[t] = [by_date[d] for d in dates]
    return dates, aligned
