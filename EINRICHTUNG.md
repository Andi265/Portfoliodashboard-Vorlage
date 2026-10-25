# Einrichtungs-Prompt: Portfoliodashboard

> **So benutzt du diesen Text:** Öffne die Claude-App, wechsle in den **Code**-Tab und starte eine neue Sitzung in
> einem neuen, leeren Ordner mit kurzem Pfad (z. B. `Dokumente/Portfoliodashboard`). Kopiere alles ab der Linie unten
> in diese Sitzung und schicke es ab. Claude erledigt den Rest und fragt dich, wenn es etwas von dir braucht.

---

Richte für mich ein persönliches **Portfoliodashboard** ein. Es liest mein Depot bei Scalable Capital über den
Scalable-Connector, analysiert Märkte, Makrodaten und News und zeigt jeden Werktag ein **Morning-Briefing** und ein
**Dinner-Briefing** auf einer festen, privaten Seite („Atlas Briefing“). Es führt **nie** Trades aus.

**Die Vorlage liegt hier:** https://github.com/Andi265/Portfoliodashboard-Vorlage (öffentlich, Vorlage-Repository).
Daraus legst du mein eigenes, **privates** Repository an. Lies nach dem Anlegen zuerst `README.md` und `CLAUDE.md` in
meinem Repository. Dort steht, wie alles zusammenspielt.

## Regeln für dich

- Sprich Deutsch, in einfacher Sprache, per Du. Ich bin kein Programmierer und fasse keine Dateien an: Du führst alle
  Befehle aus und erklärst kurz, was passiert.
- **Eine Frage pro Nachricht.** Zeig bei Einstellungen den vorgeschlagenen Wert und frag, ob er passt.
- **Keine Trades, keine Sparplan-Änderungen**, auch nicht während der Einrichtung. In Scalable nur lesen; schreiben nur
  bei Watchlist und Preisalarmen, und während der Einrichtung gar nicht.
- **Keine Passwörter oder Tokens im Chat.** GitHub melde ich im Browser an. Meine E-Mail-Adresse geht nur mit meinem
  ausdrücklichen Ja an GitHub (als Secret für die SEC-Abfragen).
- **Nur echte Daten.** Fällt eine Quelle aus, zeig „Daten nicht verfügbar“ mit dem Fehler, nie geschätzte Werte.
- Bevor du etwas mit Außenwirkung tust (Repository anlegen, Secret setzen, Seite veröffentlichen), sag in einem Satz,
  was passiert. Prüfe nach jedem Schritt, ob er geklappt hat, und sag es mir kurz.
- Klappt etwas nicht, such die Ursache, statt es zu umgehen.
- Analysen und Signale sind keine Anlageberatung. Entscheidungen treffe ich selbst.

## Skills

| Skill | Wofür |
|---|---|
| `artifact-design` | vor dem ersten Veröffentlichen der Seite laden (gehört zum Artifact-Tool) |
| `portfolio-einstellungen` | Projekt-Skill im Repository: „Einstellungen anzeigen“, „Strategie ändern“, „Schwellen ändern“, „Uhrzeiten ändern“, „Push an/aus“, „Universum anzeigen“ |
| `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:executing-plans`, `superpowers:test-driven-development` | für spätere Änderungen am Dashboard: erst klären, dann ein Plan zum Freigeben, dann testgetrieben umsetzen |

Die `superpowers`-Skills kommen aus dem Plugin **superpowers** im offiziellen Plugin-Marktplatz
(`claude-plugins-official`). Für die Einrichtung selbst brauchst du es nicht.

## Schritt 1: Voraussetzungen prüfen

Frag kurz nach (eine Frage pro Nachricht, nur was du nicht selbst prüfen kannst):
- ein **Depot bei Scalable Capital**
- ein **GitHub-Konto** (kostenlos reicht)
- ein **Claude-Abo mit Claude Code und Routinen** (Routinen laufen in der Cloud auf claude.ai/code)
- in claude.ai verbundene Connectoren **Scalable Capital** und **FRED** (claude.ai/customize/connectors). Prüf selbst,
  ob ihre Werkzeuge in dieser Sitzung verfügbar sind (`get_portfolio_overview`, `fred-get-series-observations`). Fehlt
  einer, erklär mir, wo ich ihn verbinde, und warte.

Prüf auf dem PC selbst: `git`, die GitHub-CLI `gh` und **Python ab 3.11** (empfohlen 3.13). Fehlt etwas, schlag die
Installation vor und führe sie nach meinem Ja aus (Windows: `winget`, Mac: `brew`). Melde mich bei GitHub mit
`gh auth login --web` an (ich bestätige im Browser).

## Schritt 2: Meine Einstellungen (je eine Frage)

1. **Name** für die Anrede
2. **Zeitzone** (schlag die des PCs vor, als IANA-Name, z. B. `Europe/Berlin`)
3. **Morning-Briefing:** um wie viel Uhr? (Vorschlag 08:30, vor Börsenbeginn in Europa)
4. **Dinner-Briefing:** um wie viel Uhr? (Vorschlag 17:45, nach Börsenschluss in Europa) · an welchen Tagen? (Mo–Fr)
5. **Push-Nachrichten** aufs Handy, wenn es etwas Wichtiges gibt: ja oder nein?
6. **Meine Ziele** in einem Satz (Vorschlag: „Langfristige Gewinne mit ETFs, mittelfristig höhere Gewinne mit stabilen
   Einzelaktien“) und, wenn ich mag, **Beispiele für meine Anlagethesen** (z. B. eine Branche oder ein Trend, auf den ich
   setze)
7. **Kern/Satellit:** welcher Anteil breite ETFs (Vorschlag 70 %)?
8. **Maximale Gewichtung einer Einzelaktie** (Vorschlag 15 %)
9. **Risikotoleranz** (niedrig, mittel, hoch) und ab welchem Rückgang einer Position die Routine die These prüfen soll
   (Vorschlag mittel, 15–20 %)
10. **Sparerpauschbetrag** (1.000 € oder 2.000 € bei gemeinsamer Veranlagung)
11. **Schwellen:** Standardwerte übernehmen? (Hinweis bei vorbörslicher Bewegung ab ±3 %, Push ab ±7 %, Ursachen-Suche
    in der Tagesbilanz ab ±3 %, Preisalarm „nah“ ab 2 %). Bei Nein jede einzeln fragen.
12. **Preisalarme bei Scalable:** Free-Broker (höchstens 4) oder ein anderes Modell?
13. **Kontakt-E-Mail für die SEC:** Die US-Börsenaufsicht verlangt bei jeder Abfrage eine Kontakt-E-Mail im
    Absender. Sie wird nur als GitHub-Secret gespeichert und nur an sec.gov geschickt. Eigene Frage, mein Ja ist nötig.
14. **Name meines privaten Repositorys** (Vorschlag: `portfoliodashboard`)

Danach: Zusammenfassung zeigen, mein Ja abwarten.

## Schritt 3: Mein Repository aus der Vorlage

- `gh repo create <mein-github-name>/<repo-name> --private --template Andi265/Portfoliodashboard-Vorlage --clone`,
  dann im geklonten Ordner weiterarbeiten. Unter Windows zuerst `git config --global core.longpaths true`.
- `settings.json` ausfüllen (alle Werte aus Schritt 2; `links.atlas_briefing` folgt in Schritt 8), dann
  `python settings.py` (Prüfung muss „ok“ melden).
- Weichen meine Uhrzeiten oder Tage von 08:30 / 17:45 / Mo–Fr ab: `python settings.py cron` und die zwei `cron:`-Zeilen
  in `.github/workflows/atlas-snapshot.yml` ersetzen.
- Virtuelle Umgebung unter einem **kurzen Pfad** anlegen (Windows: z. B. `%USERPROFILE%\.portfolio-venv`; sehr lange
  Pfade brechen PyTorch und Git), dann `pip install -r atlas-terminal/requirements.txt` (dauert wegen PyTorch einige
  Minuten; im Hintergrund laufen lassen).
- Tests: `python -m pytest atlas-terminal/tests -q` (alles grün).
- Committen und auf `main` pushen.

## Schritt 4: GitHub einrichten

- Secret: `gh secret set SEC_CONTACT_EMAIL` mit der E-Mail aus Schritt 2 (über die Standardeingabe, nicht im Chat
  wiederholen).
- Schreibrechte der Abläufe: `gh api -X PUT repos/<repo>/actions/permissions/workflow -f default_workflow_permissions=write`

## Schritt 5: Mein Depot einlesen

- Hat mein Scalable-Konto mehrere Portfolios (`list_accessible_portfolios`), frag, welches gemeint ist.
- Lies `get_portfolio_overview`, `get_portfolio_holdings`, `get_portfolio_cash_breakdown`, `list_savings_plans` und
  `list_price_alerts`.
- Schlag mir für jede Position eine Einordnung vor: **ETF-Kern** (breite ETFs wie MSCI World, All-World, DAX),
  **ETF-Thema**, **Aktie** oder **Krypto**, und lass sie mich bestätigen.
- Prüf, ob eine meiner Aktien im Atlas-Universum steht (`UNIVERSE_REGIONS` in `atlas-terminal/app/config.py`). Das
  Universum soll **ohne** meine eigenen Werte sein (die bewertet die Routine unter „Signale“): Schlag mir je
  Überschneidung einen gleichwertigen Ersatz aus derselben Region vor (liquides Großunternehmen, Yahoo-Ticker vorher
  mit yfinance prüfen: 5 Jahre Tageskurse mit `Adj Close`), trag nach meinem Ja `UNIVERSE_REGIONS` und `NAMES` ein,
  Tests laufen lassen, committen.

## Schritt 6: Makrodaten über den FRED-Connector

Ruf mit `fred-get-series-observations` (Sortierung `desc`) ab und schreib die Antworten **unverändert** nach
`dashboard/fred.json` im Format aus `dashboard/SCHEMA.md` (`fetched_at`, `source`, `series`):

| Schlüssel | Aufruf |
|---|---|
| `DFF`, `DGS3MO`, `DGS2`, `DGS10`, `ECBDFR` | jeweils `series_id` wie Schlüssel, `limit: 10` |
| `CPI_YOY` | `series_id: "CPIAUCSL"`, `units_transformation: "pc1"`, `limit: 13` |
| `UNRATE` | `series_id: "UNRATE"`, `limit: 13` |
| `HICP_YOY` | `series_id: "CP0000EZ19M086NEST"`, `units_transformation: "pc1"`, `limit: 13` |
| `BUND10` | `series_id: "IRLTLT01DEM156N"`, `limit: 13` |

Prüf, dass jede Reihe aktuelle Werte hat. Committen und pushen.

## Schritt 7: Erster Datenabruf

- `gh workflow run atlas-snapshot.yml -f slot=manual`, mit `gh run watch` auf das Ende warten (beim ersten Mal einige
  Minuten wegen PyTorch und FinBERT).
- `git pull`, dann prüfen: `atlas-snapshot/meta.json` existiert, `failed_sources` ist leer.
- Schlägt der Push des Ablaufs mit einem Rechteproblem fehl: Schritt 4 (Schreibrechte) prüfen und erneut starten.

## Schritt 8: Die feste Seite „Atlas Briefing“

- Schreib `dashboard/briefing.json` nach `dashboard/SCHEMA.md` aus meinem Depot (Schritt 5): `type` „abend“,
  `title` „Dinner-Briefing“, `headline` „Ersteinrichtung: …“, `action_needed` null, Positionen mit `qty` und `price`
  (Krypto als `value_eur`), meine aktiven Preisalarme als `levels`, keine Signale (`signals_note`: „Noch keine
  Signale. Das Dinner-Briefing erstellt sie bei der Startanalyse.“), unter `events` die nächste Sparplan-Ausführung.
- `python dashboard/build.py`. Die gemeldete Abweichung zum Scalable-Gesamtwert muss unter 5 € liegen.
- Skill `artifact-design` laden. Dann `dashboard/atlas-briefing.html` als **privates** Artifact veröffentlichen
  (`icon: "chart"`) und **anpinnen**.
- Den Link in `settings.json` unter `links.atlas_briefing` eintragen, committen, pushen.
- Die Routinen ersetzen diese Seite künftig nach jedem Lauf unter demselben Link.

## Schritt 9: Die Routinen

Die beiden Routinen schicken mir persönliche Kauf- und Verkaufssignale für mein Depot. Deshalb **lege ich sie selbst
an**; du gibst mir dafür eine genaue Anleitung, Schritt für Schritt, eine Routine nach der anderen:

- Claude-App → **Code**-Tab → **Routines** → **New routine** → **Cloud** (nicht „Local“)
- **Name:** „Morning-Briefing“ bzw. „Dinner-Briefing“
- **Prompt:**
  - Morning: „Erstelle mein Morning-Briefing. Lies dazu prompts/morning-briefing.md in diesem Repository und befolge
    die Anweisungen vollständig und Schritt für Schritt. Antworte auf Deutsch.“
  - Dinner: „Erstelle mein Dinner-Briefing. Lies dazu prompts/dinner-briefing.md in diesem Repository und befolge die
    Anweisungen vollständig und Schritt für Schritt. Antworte auf Deutsch.“
- **Repository:** mein privates Repository; **Environment:** Default
- **Trigger:** Schedule → meine Tage und Uhrzeiten (Ortszeit; die Umrechnung macht claude.ai)
- **Connectors:** **Scalable Capital** und **FRED** aktiv lassen, alle anderen entfernen
- Die Routinen brauchen Zugriff auf mein Repository (Claude-GitHub-App). Fehlt er, zeig mir, wo ich ihn freigebe.

Frag danach, ob beide Routinen angelegt sind.

## Schritt 10: Testlauf

- Bitte mich, beim **Dinner-Briefing** auf **Run now** zu klicken. Der erste Lauf macht die **Startanalyse** meines
  Depots.
- Prüf danach: `git pull` zeigt einen Commit „Journal: Abend …“ auf `main`; `portfolio-journal.md` hat unter „Status“
  das Datum der Startanalyse; die Seite unter `links.atlas_briefing` ist aktualisiert (Artifact lesen).
- Frag mich, ob die Push-Nachricht angekommen ist (falls eingeschaltet). Bei Problemen: Ursache suchen und beheben.
  Typisch: Connector in der Routine nicht aktiv, Repo-Zugriff fehlt, Push landete auf einem `claude/…`-Branch.

## Schritt 11: Übergabe

Fass für mich in wenigen Zeilen zusammen:
- den Link der Seite und die Zeiten der Routinen und des Datenabrufs (45 Minuten vorher)
- wie ich Einstellungen ändere (Sätze wie „Einstellungen anzeigen“, „Strategie ändern“, „Schwellen ändern“,
  „Uhrzeiten ändern“, „Push an/aus“ in einer Claude-Code-Sitzung in diesem Ordner)
- den monatlichen **Universum-Check**: Das Dinner-Briefing schlägt am letzten Werktag des Monats Tauschkandidaten vor;
  ich antworte im Chat der Routine (z. B. „1 ja, 2 nein“) oder hake sie im Journal ab
- dass die Signale Vorschläge der Routine sind und keine Anlageberatung
- wie ich später Änderungen am Dashboard wünsche: einfach beschreiben; du gehst mit den `superpowers`-Skills vor
