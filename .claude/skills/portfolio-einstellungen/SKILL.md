---
name: portfolio-einstellungen
description: Persönliche Einstellungen des Portfoliodashboards anzeigen oder ändern. Auslöser sind Sätze wie „Einstellungen anzeigen“, „Strategie ändern“, „Kern/Satellit ändern“, „maximale Gewichtung ändern“, „Risikotoleranz ändern“, „Sparerpauschbetrag ändern“, „Schwellen ändern“, „Uhrzeiten ändern“, „Push an“, „Push aus“, „Anlagethesen ändern“ oder „Universum anzeigen“. Schreibt settings.json und bei neuen Uhrzeiten den Zeitplan in .github/workflows/atlas-snapshot.yml.
---

# Portfolio-Einstellungen

Der Nutzer ändert hier die persönlichen Werte seines Portfoliodashboards. Sein Name steht in `settings.json` (`name`).
Er muss kein Programmierer sein: Sprich Deutsch, in einfacher Sprache, per Du. Er fasst keine Dateien an; du
erledigst alles im Repository-Ordner.

## Dialogregeln
- **Eine Frage pro Nachricht.** Zeig bei jeder Frage den **aktuellen Wert**: „Bisher: …. Soll das so bleiben?“
- Bei einer Änderung nur die betroffenen Werte durchgehen (Tabelle unten).
- Am Ende eine **Zusammenfassung zum Bestätigen**. Erst nach einem klaren Ja schreibst du.
- Fachbegriffe kurz erklären (z. B. „Kern = breite ETFs, die per Sparplan bespart und nicht getradet werden“).
- Das sind persönliche Vorgaben für die Routinen, keine Anlageberatung. Schlag Standardwerte vor, entscheiden tut der
  Nutzer.

## Ablauf
1. `git pull`, dann `python settings.py` ausführen und lesen.
2. **„Einstellungen anzeigen“:** Werte in einfachen Worten wiedergeben, dazu die Snapshot-Zeiten. Nichts ändern. Fertig.
   **„Universum anzeigen“:** `UNIVERSE_REGIONS` aus `atlas-terminal/app/config.py` mit Namen nach Regionen zeigen und
   erklären, dass Änderungen über den monatlichen Universum-Check des Dinner-Briefings laufen.
3. Fragen stellen, eine pro Nachricht.
4. Zusammenfassung zeigen, bestätigen lassen.
5. `settings.json` schreiben (UTF-8, LF), dann `python settings.py` (Prüfung muss „ok“ melden; sonst korrigieren).
6. **Bei neuen Uhrzeiten oder Tagen:** `python settings.py cron` ausführen und die zwei `cron:`-Zeilen in
   `.github/workflows/atlas-snapshot.yml` ersetzen. Sag dem Nutzer, dass er auch die Uhrzeiten seiner beiden Routinen
   anpassen muss (claude.ai/code → Routines → Routine → Edit → Trigger).
7. Committen („Einstellungen: …“) und auf `main` pushen. Kurz sagen, ab wann die Änderung wirkt (nächster Lauf).

## Werte

| Thema | Schlüssel | Standard |
|---|---|---|
| Anrede | `name` | – |
| Zeitzone | `timezone` | Europe/Berlin |
| Uhrzeiten | `routines.morning`, `routines.evening`, `routines.days` | 08:30, 17:45, 1-5 (Mo–Fr) |
| Ziele | `strategy.goals` | ETFs langfristig, stabile Einzelaktien mittelfristig |
| Anlagethesen als Beispiele | `strategy.thesis_examples` | leer |
| Kern/Satellit | `strategy.target_kern_pct` | 70 |
| Max. Gewicht Einzelaktie | `strategy.max_single_stock_pct` | 15 |
| Risikotoleranz | `strategy.risk_tolerance`, `strategy.max_drawdown_exit_pct` | mittel, 15–20 |
| Sparerpauschbetrag | `strategy.sparerpauschbetrag_eur` | 1000 (Paare 2000) |
| Was als Kern zählt | `strategy.kern_kinds` | ["ETF-Kern"] |
| Hinweis vorbörslich | `thresholds.premarket_info_pct` | 3 |
| Push bei Kursbewegung | `thresholds.push_move_pct` | 7 |
| Ursachen-Suche Tagesbilanz | `thresholds.daily_cause_pct` | 3 |
| Level „nah“ | `thresholds.level_near_pct` | 2 |
| Max. Preisalarme (Scalable) | `price_alert_limit` | 4 (Free-Broker) |
| Push-Nachrichten | `push_notifications` | true |
| Dashboard-Link | `links.atlas_briefing` | wird bei der Einrichtung gesetzt, nicht ändern |
