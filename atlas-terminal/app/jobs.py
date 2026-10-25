"""Zeitgesteuerte Abrufe. Nur diese Jobs sprechen mit externen Quellen; die Web-App liest
ausschließlich aus der Datenbank.

  Kurse:            alle 15 Min. während der US-Börsenzeiten (Mo–Fr 09:30–16:00 New York)
  News + Stimmung:  alle 30 Min.
  SEC:              einmal täglich
  FRED:             bei jedem Lauf aus dashboard/fred.json (FRED-Connector der Routinen)

Manuell: python -m app.jobs [prices|news|fundamentals|fred|all]
"""
import logging
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

from . import db
from .config import ALL_PRICE_TICKERS, UNIVERSE
from .fetchers import fred, market, news, sec

log = logging.getLogger("atlas.jobs")
NY = ZoneInfo("America/New_York")


def us_market_open(now=None):
    now = (now or datetime.now(NY)).astimezone(NY)
    return now.weekday() < 5 and time(9, 30) <= now.time() <= time(16, 15)


def job_prices(force=False):
    if not force and not us_market_open():
        return
    log.info("Kurse abrufen")
    market.refresh_quotes(ALL_PRICE_TICKERS)
    market.refresh_histories(ALL_PRICE_TICKERS)


def job_news():
    log.info("News + FinBERT")
    news.refresh(UNIVERSE)


def job_daily():
    log.info("FRED + SEC")
    fred.refresh_all()
    sec.refresh(UNIVERSE)


def job_retry_failed():
    """Stündlich: tägliche Quellen erneut abrufen, wenn der letzte Versuch fehlschlug."""
    failed = [r["key"] for r in db.status_all() if r["error"]]
    failed_fa = [k.split(":", 1)[1] for k in failed if k.startswith("fa:")]
    if failed_fa:
        sec.refresh(failed_fa)


def bootstrap():
    """Beim Start: fehlende Datensätze einmalig befüllen (auch außerhalb der Börsenzeiten)."""
    keys = {r["key"] for r in db.status_all() if r["available"]}
    if not all(f"history:{t}" in keys for t in ALL_PRICE_TICKERS):
        job_prices(force=True)
    if not any(k.startswith("fred:") for k in keys):
        fred.refresh_all()
    if not any(k.startswith("fa:") for k in keys):
        sec.refresh(UNIVERSE)
    if not any(k.startswith("news:") for k in keys):
        job_news()


def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler(timezone=NY)
    sched.add_job(job_prices, "cron", day_of_week="mon-fri", hour="9-16", minute="0,15,30,45",
                  id="prices", max_instances=1, coalesce=True)
    sched.add_job(job_news, "interval", minutes=30, id="news", max_instances=1, coalesce=True)
    sched.add_job(job_daily, "cron", hour=6, minute=5, id="daily", max_instances=1, coalesce=True)
    sched.add_job(job_retry_failed, "interval", minutes=60, id="retry", max_instances=1, coalesce=True)
    sched.add_job(bootstrap, id="bootstrap", max_instances=1)  # sofort, im Hintergrund
    sched.start()
    return sched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db.init_db()
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("prices", "all"):
        job_prices(force=True)
    if what in ("fred", "all"):
        fred.refresh_all()
    if what in ("fundamentals", "all"):
        sec.refresh(UNIVERSE)
    if what in ("news", "all"):
        job_news()
    for r in db.status_all():
        print(f"{r['key']:<18} {'OK ' if r['available'] else '-- '} {r['error'] or ''}")
