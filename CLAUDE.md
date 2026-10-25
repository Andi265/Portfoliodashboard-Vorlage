# Portfoliodashboard

Personal portfolio assistant for one investor with a Scalable Capital account: two Claude routines (Morning-Briefing,
Dinner-Briefing) analyse the depot, markets and news, keep a shared journal and publish one fixed, private dashboard
page ("Atlas Briefing"). They never trade. Replies to the user are in German, in simple language.

`settings.json` holds the personal settings (name, time zone, routine times, strategy, thresholds, price-alert limit,
push yes/no, dashboard link); `python settings.py` prints and checks them, `python settings.py cron` prints the UTC cron
lines for the snapshot workflow. Change settings only through the project skill
`.claude/skills/portfolio-einstellungen/`.

## Parts
- `atlas-terminal/`: Python finance terminal (FastAPI + SQLite). Fetches real data from free sources without API keys:
  Yahoo Finance via yfinance (delayed prices, fixed world universe in `app/config.py` without the user's own holdings,
  market overview by region), Google News RSS by company name plus FinBERT (`ProsusAI/finbert`, local CPU) for
  sentiment, SEC EDGAR for quarterly fundamentals of US companies (User-Agent with contact e-mail from the secret
  `SEC_CONTACT_EMAIL`). FRED data comes only from `dashboard/fred.json` (raw answers of the FRED connector, written by
  the routines); the FRED CSV download is not reachable from data centres and is not used.
  Risk metrics (`app/metrics.py`): log returns on adjusted closes; volatility std·√252; return mean·252; Sharpe with the
  ECB deposit rate (ECBDFR/100); beta against `EUNL.DE` (MSCI World in EUR) on common days; max drawdown; per stock
  its own last 252 trading days; correlation on common days. Tests: `python -m pytest atlas-terminal/tests -q`.
- `atlas-snapshot/`: written by `.github/workflows/atlas-snapshot.yml` about 45 minutes before each routine
  (`python -m app.export`; the slot check runs without dependencies, two UTC cron times per slot for summer/winter
  time, one export per slot and day). The routines read these JSON files and need no network access for them.
- `dashboard/`: `build.py` (standard library only) merges `briefing.json` (written by the routines, format in
  `SCHEMA.md`), `fred.json`, the snapshot and `settings.json` into `atlas-briefing.html` (template `template.html`).
  It computes values, weights, allocation and level distances itself. Do not hand-edit the generated HTML.
- `prompts/morning-briefing.md`, `prompts/dinner-briefing.md`: the routine prompts. Every personal value comes from
  `settings.json`.
- `portfolio-journal.md`: shared memory (status, current signals, open points, universe proposals, log, archive).

## Rules
- Never place, preview or confirm orders and never change savings plans. Scalable write access only for watchlists
  and price alerts.
- Only real data. If a source fails, show "Daten nicht verfügbar" with the error; never estimate.
- The routines push directly to `main` (`git push origin HEAD:main`) and commit only `portfolio-journal.md`,
  `dashboard/briefing.json`, `dashboard/fred.json`, and after a confirmed universe change `atlas-terminal/app/config.py`
  (only `UNIVERSE_REGIONS` and `NAMES`).
- The dashboard is one private artifact at the fixed link in `settings.json`; routines republish to that link, never
  create a new one.
- Signals are analyses, not investment advice. The user decides.
- Keep LF line endings. On Windows use a short path for the virtual environment and `git config core.longpaths true`.
