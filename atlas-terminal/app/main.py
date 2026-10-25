"""Atlas Terminal – FastAPI-Backend. Liest ausschließlich aus der Datenbank."""
import logging
import math
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db, jobs, metrics
from .config import (BENCHMARK, ETFS, FRED_SERIES, MARKET_GROUPS, MARKET_OVERVIEW, NAMES, RISK_FREE_SERIES,
                     RUN_SCHEDULER, SEC_TICKERS, UNIVERSE, UNIVERSE_REGIONS)

logging.basicConfig(level=logging.INFO)
STATIC = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    sched = jobs.start_scheduler() if RUN_SCHEDULER else None
    yield
    if sched:
        sched.shutdown(wait=False)


app = FastAPI(title="Atlas Terminal", lifespan=lifespan)


def _clean(x):
    """NaN/Inf sind kein gültiges JSON."""
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    return x


def _tickers(param: str | None, default):
    if not param:
        return list(default)
    ts = [t.strip().upper() for t in param.split(",") if t.strip()]
    bad = [t for t in ts if t not in UNIVERSE]
    if bad:
        raise HTTPException(400, f"Nicht im Universum: {', '.join(bad)}")
    return ts


def _panel(entry, data=None):
    """Einheitliche Hülle: Daten + Quelle + Zeitstempel + Fehler."""
    return {"available": entry["available"], "source": entry["source"],
            "updated_at": entry["updated_at"], "error": entry["error"],
            "data": entry["data"] if data is None else data}


def _last(rows):
    return rows[-1] if rows else None


def macro_strip():
    out = {}
    for sid in ("DFF", "DGS10", "DGS2", "DGS3MO"):
        e = db.load(f"fred:{sid}")
        out[sid] = _panel(e, _last(e["data"]) if e["available"] else None)
    d10, d2 = out["DGS10"], out["DGS2"]
    if d10["available"] and d2["available"]:
        out["2s10s"] = {"available": True, "source": "FRED (DGS10 - DGS2)",
                        "updated_at": min(d10["updated_at"], d2["updated_at"]), "error": None,
                        "data": {"date": min(d10["data"]["date"], d2["data"]["date"]),
                                 "value": d10["data"]["value"] - d2["data"]["value"]}}
    else:
        out["2s10s"] = {"available": False, "source": "FRED (DGS10 - DGS2)", "updated_at": None,
                        "error": d10["error"] or d2["error"], "data": None}
    for sid in ("CPI_YOY", "UNRATE", "ECBDFR", "HICP_YOY", "BUND10"):
        e = db.load(f"fred:{sid}")
        out[sid] = _panel(e, _last(e["data"]) if e["available"] else None)
    return out


@app.get("/api/universe")
def universe():
    return {"universe": UNIVERSE, "universe_regions": UNIVERSE_REGIONS, "market_overview": MARKET_OVERVIEW,
            "market_groups": MARKET_GROUPS, "names": NAMES, "etfs": sorted(ETFS), "sec_tickers": SEC_TICKERS,
            "benchmark": BENCHMARK, "risk_free_series": RISK_FREE_SERIES}


@app.get("/api/markets")
def markets(watchlist: str | None = None):
    wl = _tickers(watchlist, UNIVERSE)
    quotes = {t: _panel(db.load(f"quote:{t}")) for t in dict.fromkeys(MARKET_OVERVIEW + wl)}
    return _clean({"overview": MARKET_OVERVIEW, "groups": MARKET_GROUPS, "names": NAMES, "watchlist": wl,
                   "quotes": quotes, "macro": macro_strip()})


def _sma(values, n):
    out, s = [], 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out


RANGES = {"1M": 21, "6M": 126, "1Y": 252, "5Y": 1260}


@app.get("/api/quote/{ticker}")
def quote(ticker: str, range: str = Query("1Y", pattern="^(1M|6M|1Y|5Y)$")):
    t = ticker.upper()
    if t not in UNIVERSE and t not in MARKET_OVERVIEW:
        raise HTTPException(404, f"{t} ist nicht im Universum")
    h = db.load(f"history:{t}")
    hist = None
    if h["available"]:
        rows = h["data"]
        closes = [r["close"] for r in rows]
        sma50, sma200 = _sma(closes, 50), _sma(closes, 200)
        last_year = rows[-252:]
        n = RANGES[range]
        hist = {
            "rows": [dict(r, sma50=sma50[i], sma200=sma200[i])
                     for i, r in enumerate(rows)][-n:],
            "high_52w": max(r["high"] for r in last_year),
            "low_52w": min(r["low"] for r in last_year),
            "last_date": rows[-1]["date"],
        }
    return _clean({"ticker": t, "quote": _panel(db.load(f"quote:{t}")),
                   "history": _panel(h, hist)})


@app.get("/api/fa/{ticker}")
def fundamentals(ticker: str):
    t = ticker.upper()
    if t not in UNIVERSE:
        raise HTTPException(404, f"{t} ist nicht im Universum")
    if t not in SEC_TICKERS:
        return {"ticker": t, "etf": False, "fa": {
            "available": False, "source": "SEC EDGAR", "updated_at": None, "data": None,
            "error": f"{NAMES.get(t, t)} ist kein US-Unternehmen: SEC EDGAR enthält keine Quartalsberichte (10-Q)"}}
    return _clean({"ticker": t, "etf": False, "fa": _panel(db.load(f"fa:{t}"))})


def compute_risk(tickers):
    """Je Wert: Volatilität, Rendite, Sharpe und Drawdown auf den eigenen letzten 252 Handelstagen.
    Beta paarweise gegen den Benchmark (MSCI World in EUR) auf gemeinsamen Handelstagen.
    Korrelationen auf den gemeinsamen Handelstagen aller gewählten Werte."""
    hist, errors, updated = {}, {}, []
    for t in dict.fromkeys([BENCHMARK] + tickers):
        e = db.load(f"history:{t}")
        if e["available"]:
            hist[t] = e["data"]
            updated.append(e["updated_at"])
        else:
            errors[t] = e["error"]
    if BENCHMARK not in hist:
        raise RuntimeError(f"Benchmark {BENCHMARK} fehlt (für Beta nötig): {errors.get(BENCHMARK)}")
    rf_e = db.load(f"fred:{RISK_FREE_SERIES}")
    rf_point = rf_e["data"][-1] if rf_e["available"] else None
    rf = rf_point["value"] / 100 if rf_point else None
    rf_error = None if rf_point else f"Sharpe nicht verfügbar – {RISK_FREE_SERIES} fehlt: {rf_e['error']}"
    rows = []
    for t in tickers:
        if t not in hist:
            rows.append({"ticker": t, "name": NAMES.get(t, t), "error": errors.get(t)})
            continue
        dates, prices = metrics.last_window(hist[t])
        r = metrics.log_returns(prices)
        bdates, bp = metrics.align_on_dates({t: hist[t], BENCHMARK: hist[BENCHMARK]})
        rows.append({
            "ticker": t, "name": NAMES.get(t, t),
            "ann_vol": metrics.annualized_volatility(r),
            "ann_return": metrics.annualized_return(r),
            "sharpe": metrics.sharpe_ratio(r, rf) if rf is not None else None,
            "beta": metrics.beta(metrics.log_returns(bp[t]), metrics.log_returns(bp[BENCHMARK])),
            "max_drawdown": metrics.max_drawdown(prices),
            "window": {"start": dates[0], "end": dates[-1], "returns": len(r)},
            "beta_window": {"start": bdates[0], "end": bdates[-1], "returns": len(bdates) - 1},
        })
    corr_t = [t for t in tickers if t in hist]
    cdates, cprices = metrics.align_on_dates({t: hist[t] for t in corr_t}) if corr_t else ([], {})
    crets = {t: metrics.log_returns(p) for t, p in cprices.items()}
    corr = metrics.correlation_matrix({t: crets[t] for t in corr_t}) if len(corr_t) > 1 else (corr_t, [[1.0]] if corr_t else [])
    return {
        "benchmark": {"ticker": BENCHMARK, "name": NAMES.get(BENCHMARK, BENCHMARK)},
        "risk_free": {"value": rf, "series": RISK_FREE_SERIES, "date": rf_point["date"] if rf_point else None,
                      "error": rf_error},
        "rows": rows,
        "correlation": {"tickers": corr[0], "matrix": corr[1],
                        "window": {"start": cdates[0], "end": cdates[-1], "returns": len(cdates) - 1} if cdates else None},
        "updated_at": min(updated) if updated else None,
        "rf_updated_at": rf_e["updated_at"],
    }


@app.get("/api/risk")
def risk(tickers: str | None = None):
    ts = _tickers(tickers, UNIVERSE)
    src = f"Berechnet aus Yahoo Finance (bereinigte Schlusskurse, delayed); Beta vs. {NAMES[BENCHMARK]}; rf = FRED {RISK_FREE_SERIES}"
    try:
        data = compute_risk(ts)
        return _clean({"available": True, "source": src, "updated_at": data["updated_at"],
                       "error": None, "data": data})
    except Exception as e:  # noqa: BLE001
        return {"available": False, "source": src, "updated_at": None,
                "error": f"{type(e).__name__}: {e}", "data": None}


@app.get("/api/news")
def news_api(tickers: str | None = None):
    ts = _tickers(tickers, UNIVERSE)
    return _clean({t: _panel(db.load(f"news:{t}")) for t in ts})


@app.get("/api/eco")
def eco():
    series = {}
    for sid, name in FRED_SERIES.items():
        e = db.load(f"fred:{sid}")
        series[sid] = dict(_panel(e), name=name)
    curve = []
    for sid, label in (("DGS3MO", "3M"), ("DGS2", "2Y"), ("DGS10", "10Y")):
        s = series[sid]
        curve.append({"tenor": label, "series": sid,
                      "value": s["data"][-1]["value"] if s["available"] else None,
                      "date": s["data"][-1]["date"] if s["available"] else None,
                      "error": None if s["available"] else s["error"]})
    return _clean({"series": series, "curve": curve})


@app.get("/api/briefing")
def briefing(tickers: str | None = None):
    """Kompakte Zusammenfassung für Routinen/Agenten: Märkte, Makro, Risiko, Stimmung."""
    ts = _tickers(tickers, UNIVERSE)
    m = markets(",".join(ts))
    quotes = {t: (q["data"] if q["available"] else {"error": q["error"]}) | {"updated_at": q["updated_at"]}
              for t, q in m["quotes"].items()}
    macro = {k: (v["data"] if v["available"] else {"error": v["error"]}) for k, v in m["macro"].items()}
    r = risk(",".join(ts))
    sentiment = {}
    for t, n in news_api(",".join(ts)).items():
        if not n["available"]:
            sentiment[t] = {"error": n["error"]}
            continue
        d = n["data"]
        sentiment[t] = {"average": d["average"], "updated_at": n["updated_at"],
                        "headlines": [{"title": i["title"], "publisher": i["publisher"],
                                       "published": i["published"], "feed": i["feed"], "link": i["link"],
                                       "sentiment": (i.get("sentiment") or {}).get("label"),
                                       "confidence": (i.get("sentiment") or {}).get("confidence")}
                                      for i in d["items"][:5]]}
    return _clean({"note": "Kurse verzögert (delayed). Alle Werte stammen aus der Datenbank von Atlas Terminal.",
                   "quotes": quotes, "macro": macro,
                   "risk": r["data"] if r["available"] else {"error": r["error"]},
                   "news_sentiment": sentiment})


@app.get("/api/status")
def status():
    return db.status_all()


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
