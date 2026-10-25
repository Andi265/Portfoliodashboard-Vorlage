# Portfoliodashboard-Vorlage

Vorlage für ein persönliches Portfoliodashboard, das Claude für dich einrichtet und betreibt. Es liest dein Depot bei
Scalable Capital über den Scalable-Connector, **führt aber nie Trades aus**.

- **Atlas Terminal:** Kurse (verzögert) für Märkte weltweit (MSCI World, Emerging Markets, DAX, Euro Stoxx 50, FTSE 100,
  US-Indizes, VIX, Nikkei, Hang Seng, Shanghai, Nifty 50, EUR/USD, Gold, Brent, Bitcoin) und ein weltweites Universum
  von Marktführern mit Trend (SMA 50/200), Volatilität, Beta gegen den MSCI World, Sharpe-Ratio, Drawdown, Korrelation,
  News mit FinBERT-Stimmung und SEC-Quartalszahlen für US-Werte. Nur kostenlose Quellen ohne API-Schlüssel.
- **Makrodaten** über den FRED-Connector: Fed Funds, US-Renditen, 2s10s, US-Inflation, US-Arbeitslosenquote,
  EZB-Einlagenzins, Inflation im Euro-Raum, Rendite der Bundesanleihe.
- **Morning-Briefing** und **Dinner-Briefing** als Claude-Routinen an Werktagen, beide auf einer festen, angepinnten
  Seite „Atlas Briefing“ im Terminal-Design, auf Wunsch mit Push-Nachricht aufs Handy. Das Dinner-Briefing macht die
  Startanalyse, freitags den Wochenrückblick und am Monatsende den Portfolio-Check samt Vorschlägen für das Universum.
- **Journal:** gemeinsames Gedächtnis beider Routinen (Signale, offene Punkte, Verlauf).
- **Datenabruf:** ein GitHub-Ablauf holt etwa 45 Minuten vor jeder Routine frische Daten und legt sie als Snapshot
  im Repository ab.

## Einrichtung

1. Öffne die Claude-App, wechsle in den **Code**-Tab und starte eine neue Sitzung in einem neuen, leeren Ordner mit
   kurzem Pfad (z. B. `Dokumente/Portfoliodashboard`).
2. Kopiere den gesamten Inhalt von [`EINRICHTUNG.md`](EINRICHTUNG.md) in diese Sitzung und schicke ihn ab.
3. Claude führt dich Schritt für Schritt durch alles, mit einer Frage pro Nachricht. Du musst keine Dateien anfassen.

Voraussetzungen: Depot bei Scalable Capital, GitHub-Konto, Claude-Abo mit Routinen, in claude.ai verbundene
Connectoren **Scalable Capital** und **FRED**.

Daraus entsteht dein eigenes, privates Repository. Persönliche Werte (Name, Zeitzone, Uhrzeiten, Strategie, Schwellen,
Push ja/nein, Link der Seite) stehen danach in `settings.json`.

## Was hier nicht drin ist

Diese Vorlage enthält keine personenbezogenen Daten: keine Depot- oder Kontodaten, keine Signale, keinen
Journal-Verlauf, keinen Datenstand, keine E-Mail-Adresse, keine Links oder Routinen eines anderen Nutzers. Alles
Persönliche entsteht erst bei deiner Einrichtung in deinem eigenen, privaten Repository.

## Technik

Python (FastAPI, SQLite, yfinance, feedparser, transformers/PyTorch für FinBERT; das Dashboard-Build nur mit der
Standardbibliothek), GitHub Actions, Claude-Code-Routinen. Tests: `python -m pytest atlas-terminal/tests -q`.

## Hinweis

Analysen und Signale sind Vorschläge einer KI und **keine Anlageberatung**. Entscheidungen triffst du selbst. Kurse
sind verzögert. Dies ist kein offizielles Produkt von Scalable Capital, Yahoo, der SEC oder der Federal Reserve Bank of
St. Louis und steht in keiner Verbindung zu ihnen; die Namen werden nur genannt, um die Datenquellen zu beschreiben.
