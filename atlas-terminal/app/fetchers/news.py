"""Nachrichten: zuerst yfinance Ticker.news, immer ergänzt durch den Google-News-RSS-Feed.
Gespeichert werden die 10 aktuellsten Schlagzeilen je Ticker, jeweils mit FinBERT-Bewertung."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import requests
import yfinance as yf

from .. import db
from ..config import HTTP_TIMEOUT, NEWS_QUERY
from . import sentiment

GOOGLE_URL = "https://news.google.com/rss/search?q={q}+stock&hl=en-US&gl=US&ceid=US:en"
SOURCE = "Yahoo Finance (yfinance) + Google News RSS; Stimmung: FinBERT (ProsusAI/finbert)"
MAX_ITEMS = 10


def _iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def fetch_yahoo(ticker: str):
    items = []
    for n in yf.Ticker(ticker).news or []:
        c = n.get("content") or n  # neues und altes yfinance-Format
        title = c.get("title")
        if not title:
            continue
        link = ((c.get("canonicalUrl") or {}).get("url")
                or (c.get("clickThroughUrl") or {}).get("url") or c.get("link"))
        publisher = (c.get("provider") or {}).get("displayName") or c.get("publisher")
        pub = c.get("pubDate") or c.get("displayTime")
        if pub:
            published = _iso(datetime.fromisoformat(pub.replace("Z", "+00:00")))
        elif c.get("providerPublishTime"):
            published = _iso(datetime.fromtimestamp(c["providerPublishTime"], tz=timezone.utc))
        else:
            published = None
        items.append({"title": title, "publisher": publisher, "published": published,
                      "link": link, "feed": "Yahoo"})
    return items


def fetch_google(ticker: str):
    url = GOOGLE_URL.format(q=quote_plus(NEWS_QUERY.get(ticker, ticker)))
    resp = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": "AtlasTerminal/1.0"})
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"RSS nicht lesbar: {feed.bozo_exception}")
    items = []
    for e in feed.entries:
        publisher = (e.get("source") or {}).get("title")
        title = e.get("title", "")
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3]  # Google hängt " - Herausgeber" an
        published = _iso(parsedate_to_datetime(e.published)) if e.get("published") else None
        items.append({"title": title, "publisher": publisher, "published": published,
                      "link": e.get("link"), "feed": "Google News"})
    return items


def collect(ticker: str):
    items, errors, counts = [], [], {}
    for name, fn in (("Yahoo", fetch_yahoo), ("Google News", fetch_google)):
        try:
            got = fn(ticker)
            counts[name] = len(got)
            items += got
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {type(e).__name__}: {e}")
    seen, unique = set(), []
    for it in sorted(items, key=lambda i: i["published"] or "", reverse=True):
        key = it["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique[:MAX_ITEMS], errors, counts


def refresh(tickers):
    for t in tickers:
        key = f"news:{t}"
        try:
            items, errors, counts = collect(t)
            if not items:
                raise RuntimeError("Keine Schlagzeilen gefunden. " + " | ".join(errors))
            try:
                for it, s in zip(items, sentiment.score([i["title"] for i in items])):
                    it["sentiment"] = s
                sent_error = None
            except Exception as e:  # noqa: BLE001
                sent_error = f"FinBERT: {type(e).__name__}: {e}"
            db.store_ok(key, SOURCE, {
                "items": items,
                "average": sentiment.aggregate(items),
                "feed_errors": errors,
                "feed_counts": counts,
                "sentiment_error": sent_error,
            })
        except Exception as e:  # noqa: BLE001
            db.store_error(key, SOURCE, f"{type(e).__name__}: {e}")
