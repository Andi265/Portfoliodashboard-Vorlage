"""Marktdaten über yfinance (Yahoo Finance, verzögert)."""
import math

import yfinance as yf

from .. import db

SOURCE = "Yahoo Finance via yfinance (delayed)"


def _num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def fetch_history(ticker: str):
    """Tageskurse der letzten 5 Jahre inkl. bereinigtem Schlusskurs und Volumen."""
    df = yf.Ticker(ticker).history(period="5y", interval="1d", auto_adjust=False, actions=False)
    if df is None or df.empty:
        raise RuntimeError(f"yfinance lieferte keine Kurshistorie für {ticker}")
    rows = []
    for idx, r in df.iterrows():
        rows.append({
            "date": idx.strftime("%Y-%m-%d"),
            "open": _num(r.get("Open")), "high": _num(r.get("High")),
            "low": _num(r.get("Low")), "close": _num(r.get("Close")),
            "adj_close": _num(r.get("Adj Close")), "volume": _num(r.get("Volume")),
        })
    rows = [r for r in rows if r["close"] is not None]
    return rows


def fetch_quote(ticker: str):
    """Aktuelle (verzögerte) Notierung."""
    fi = yf.Ticker(ticker).fast_info
    last = _num(fi.get("lastPrice"))
    prev = _num(fi.get("previousClose"))
    if last is None:
        raise RuntimeError(f"yfinance lieferte keinen aktuellen Kurs für {ticker}")
    change = (last - prev) if prev else None
    return {
        "ticker": ticker,
        "price": last,
        "previous_close": prev,
        "change": change,
        "change_pct": (change / prev * 100) if prev else None,
        "currency": fi.get("currency"),
        "exchange": fi.get("exchange"),
        "delayed": True,
    }


def refresh_quotes(tickers):
    for t in tickers:
        try:
            db.store_ok(f"quote:{t}", SOURCE, fetch_quote(t))
        except Exception as e:  # noqa: BLE001 – Fehler wird angezeigt, nicht verschluckt
            db.store_error(f"quote:{t}", SOURCE, f"{type(e).__name__}: {e}")


def refresh_histories(tickers):
    for t in tickers:
        try:
            db.store_ok(f"history:{t}", SOURCE, fetch_history(t))
        except Exception as e:  # noqa: BLE001
            db.store_error(f"history:{t}", SOURCE, f"{type(e).__name__}: {e}")
