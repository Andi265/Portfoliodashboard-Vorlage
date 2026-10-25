# Atlas Terminal

Mini-Finanzterminal (FastAPI + SQLite/PostgreSQL) mit ausschließlich echten Daten aus kostenlosen Quellen ohne API-Schlüssel:
Yahoo Finance (yfinance, delayed), Google News RSS, SEC EDGAR, FRED (über den FRED-Connector der Routinen, `dashboard/fred.json`) und FinBERT (lokal).

## Architektur
- `app/jobs.py`: Scheduler. **Nur hier** wird mit externen Quellen gesprochen.
  - Kurse: alle 15 Min. Mo–Fr 09:30–16:15 New York
  - News + FinBERT: alle 30 Min.
  - SEC: täglich 06:05 New York, fehlgeschlagene Abrufe werden stündlich neu versucht
  - FRED: bei jedem Lauf aus `dashboard/fred.json` (die Routinen holen die Werte über den FRED-Connector)
- `app/db.py`: Cache-Tabelle `cache` (Schlüssel → JSON, Quelle, Zeitstempel, letzter Fehler)
- `app/main.py`: API, liest **nur** aus der Datenbank. `static/`: Oberfläche
- Fällt eine Quelle aus, bleibt der letzte echte Stand mit Warnung sichtbar. Gab es nie Daten, zeigt die App „Daten nicht verfügbar“ und den Fehler.

## Befehle
`AAPL` → QUOTE · `AAPL FA` → Fundamentaldaten · `NVDA NEWS` · `RISK` · `ECO` · `MKTS` · F1–F6 für die Register · `/` fokussiert die Befehlszeile

## API (auch für Routinen/Agenten)
`/api/briefing`, `/api/markets?watchlist=…`, `/api/quote/{T}?range=1M|6M|1Y|5Y`, `/api/fa/{T}`, `/api/risk?tickers=…`, `/api/news?tickers=…`, `/api/eco`, `/api/status`

## Lokal starten
```bash
pip install -r requirements.txt
export SEC_CONTACT_EMAIL="name@example.com"   # Pflicht für SEC EDGAR
python -m app.jobs all                         # einmal alles befüllen (optional, macht der Server sonst selbst)
uvicorn app.main:app --port 8000
```
Ohne `DATABASE_URL` nutzt die App lokal SQLite (`atlas.db`).

## Tests
```bash
python -m pytest tests/test_metrics.py -v     # Kennzahlen an Hand-Beispielen
python -m tests.verify_ticker AAPL            # Kurs + 1J-Vol gegen frische yfinance-Daten
```

## Betrieb über GitHub Actions (Snapshot)
Der Workflow `.github/workflows/atlas-snapshot.yml` im Repo-Stamm läuft Mo–Fr gegen 07:45 und 17:00 Berliner Zeit:
Tests → alle Quellen abrufen → `python -m app.export` schreibt JSON nach `atlas-snapshot/` → Commit.
Die SQLite-Datenbank wird zwischen den Läufen per Actions-Cache aufbewahrt, sodass bei einem Quellenausfall der letzte echte Stand erhalten bleibt.
Benötigtes Repository-Secret: `SEC_CONTACT_EMAIL`.

Manuell: `python -m app.export --out ../atlas-snapshot --slot manual`
