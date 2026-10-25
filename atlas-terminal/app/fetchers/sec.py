"""Fundamentaldaten und Filings aus SEC EDGAR (companyfacts, submissions).
Jede Anfrage trägt einen User-Agent mit Kontakt-E-Mail; maximal SEC_MAX_RPS Anfragen/s."""
import threading
import time
from datetime import date

import requests

from .. import db
from ..config import HTTP_TIMEOUT, SEC_MAX_RPS, SEC_TICKERS, SEC_USER_AGENT

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SOURCE = "SEC EDGAR (data.sec.gov companyfacts/submissions)"

REVENUE_CONCEPTS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                    "SalesRevenueNet", "RevenuesNetOfInterestExpense"]
COST_CONCEPTS = ["CostOfRevenue", "CostOfGoodsAndServicesSold"]

_lock = threading.Lock()
_last_request = 0.0


def _get(url):
    global _last_request
    if not SEC_USER_AGENT:
        raise RuntimeError("SEC_CONTACT_EMAIL ist nicht gesetzt (SEC verlangt einen User-Agent mit Kontakt-E-Mail)")
    with _lock:
        wait = 1.0 / SEC_MAX_RPS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
    resp = requests.get(url, timeout=HTTP_TIMEOUT,
                        headers={"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    resp.raise_for_status()
    return resp.json()


def cik_map():
    data = _get(TICKER_MAP_URL)
    return {v["ticker"].upper(): int(v["cik_str"]) for v in data.values()}


def _days(start, end):
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _entries(facts, concept, unit):
    node = facts.get("facts", {}).get("us-gaap", {}).get(concept)
    if not node or unit not in node.get("units", {}):
        return []
    return [e for e in node["units"][unit]
            if e.get("start") and e.get("form") in ("10-Q", "10-K", "10-Q/A", "10-K/A")]


def quarterly_series(facts, concept, unit="USD", derive_q4=True):
    """Quartalswerte {end: {value, start, derived}}. Fehlendes Q4 wird bei Stromgrößen als
    Geschäftsjahr minus Summe Q1–Q3 abgeleitet und als 'derived' markiert."""
    entries = _entries(facts, concept, unit)
    quarters, annuals = {}, {}
    for e in sorted(entries, key=lambda e: e.get("filed", "")):  # spätere Filings überschreiben
        d = _days(e["start"], e["end"])
        if 80 <= d <= 100:
            quarters[e["end"]] = {"value": e["val"], "start": e["start"], "derived": False}
        elif 350 <= d <= 380:
            annuals[e["end"]] = {"value": e["val"], "start": e["start"]}
    if derive_q4:
        for end, a in annuals.items():
            if end in quarters:
                continue
            inside = [q for qe, q in quarters.items() if q["start"] >= a["start"] and qe < end]
            if len(inside) == 3:
                last_q_end = max(qe for qe, q in quarters.items() if q["start"] >= a["start"] and qe < end)
                quarters[end] = {"value": a["value"] - sum(q["value"] for q in inside),
                                 "start": last_q_end, "derived": True}
    return quarters


def _best_concept(facts, candidates):
    best, best_end = None, ""
    for c in candidates:
        es = _entries(facts, c, "USD")
        if es:
            end = max(e["end"] for e in es)
            if end > best_end:
                best, best_end = c, end
    return best


def build_fundamentals(facts, n=8):
    rev_c = _best_concept(facts, REVENUE_CONCEPTS)
    rev = quarterly_series(facts, rev_c) if rev_c else {}
    ni = quarterly_series(facts, "NetIncomeLoss")
    eps = quarterly_series(facts, "EarningsPerShareDiluted", unit="USD/shares", derive_q4=False)
    gp = quarterly_series(facts, "GrossProfit")
    gp_note = "GrossProfit"
    if not gp:
        cost_c = _best_concept(facts, COST_CONCEPTS)
        if cost_c and rev:
            cost = quarterly_series(facts, cost_c)
            gp = {e: {"value": rev[e]["value"] - cost[e]["value"],
                      "derived": rev[e]["derived"] or cost[e]["derived"]}
                  for e in rev if e in cost}
            gp_note = f"{rev_c} - {cost_c}"
        else:
            gp_note = None
    ends = sorted(rev or ni, reverse=True)[:n]
    rows = []
    for end in ends:
        r, i, e, g = rev.get(end), ni.get(end), eps.get(end), gp.get(end)
        rv = r["value"] if r else None
        rows.append({
            "period_end": end,
            "revenue": rv,
            "net_income": i["value"] if i else None,
            "eps_diluted": e["value"] if e else None,
            "gross_margin": (g["value"] / rv * 100) if (g and rv) else None,
            "net_margin": (i["value"] / rv * 100) if (i and rv) else None,
            "derived_q4": bool((r and r["derived"]) or (i and i["derived"])),
        })
    return {"entity": facts.get("entityName"), "revenue_concept": rev_c,
            "gross_profit_basis": gp_note, "quarters": rows}


def build_filings(subs, cik, per_form=3):
    recent = subs.get("filings", {}).get("recent", {})
    out = {"10-K": [], "10-Q": [], "8-K": []}
    for i, form in enumerate(recent.get("form", [])):
        if form in out and len(out[form]) < per_form:
            acc = recent["accessionNumber"][i]
            doc = recent["primaryDocument"][i]
            out[form].append({
                "form": form,
                "filing_date": recent["filingDate"][i],
                "report_date": recent.get("reportDate", [None] * (i + 1))[i],
                "description": recent.get("primaryDocDescription", [""] * (i + 1))[i],
                "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}",
            })
    return out


def refresh(tickers):
    stocks = [t for t in tickers if t in SEC_TICKERS]
    try:
        ciks = cik_map()
    except Exception as e:  # noqa: BLE001
        for t in stocks:
            db.store_error(f"fa:{t}", SOURCE, f"CIK-Zuordnung: {type(e).__name__}: {e}")
        return
    for t in stocks:
        key = f"fa:{t}"
        try:
            cik = ciks.get(t)
            if cik is None:
                raise RuntimeError(f"Kein CIK für {t} gefunden")
            facts = _get(FACTS_URL.format(cik=cik))
            subs = _get(SUBMISSIONS_URL.format(cik=cik))
            data = build_fundamentals(facts)
            data["cik"] = cik
            data["filings"] = build_filings(subs, cik)
            db.store_ok(key, SOURCE, data)
        except Exception as e:  # noqa: BLE001
            db.store_error(key, SOURCE, f"{type(e).__name__}: {e}")
