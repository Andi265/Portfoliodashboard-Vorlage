"""Zentrale Konfiguration von Atlas Terminal."""
import os

# Festes Ticker-Universum: weltweite Marktführer (Yahoo-Ticker). Bewusst ohne die eigenen
# Depotpositionen, die bewerten die Routinen unter „Signale“.
UNIVERSE_REGIONS = {
    "USA": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "V", "AMD"],
    "Europa": ["SAP.DE", "SIE.DE", "ALV.DE", "MC.PA", "NOVO-B.CO", "ASML.AS"],
    "Asien": ["7203.T", "2330.TW", "005930.KS"],
}
UNIVERSE = [t for ts in UNIVERSE_REGIONS.values() for t in ts]

# Marktübersicht (nur Kurse), nach Regionen
MARKET_GROUPS = {
    "Welt": ["EUNL.DE", "EEM"],
    "Europa": ["^GDAXI", "^STOXX50E", "^FTSE"],
    "USA": ["SPY", "QQQ", "DIA", "IWM", "^VIX"],
    "Asien": ["^N225", "^HSI", "000001.SS", "^NSEI"],
    "Währungen & Rohstoffe": ["EURUSD=X", "GC=F", "BZ=F", "BTC-USD"],
}
MARKET_OVERVIEW = [t for ts in MARKET_GROUPS.values() for t in ts]

NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "AMZN": "Amazon", "GOOGL": "Alphabet",
    "META": "Meta Platforms", "TSLA": "Tesla", "JPM": "JPMorgan Chase", "V": "Visa", "AMD": "AMD",
    "SAP.DE": "SAP", "SIE.DE": "Siemens", "ALV.DE": "Allianz", "MC.PA": "LVMH", "NOVO-B.CO": "Novo Nordisk",
    "ASML.AS": "ASML", "7203.T": "Toyota", "2330.TW": "TSMC", "005930.KS": "Samsung Electronics",
    "EUNL.DE": "MSCI World (iShares, EUR)", "EEM": "MSCI Emerging Markets (iShares)",
    "^GDAXI": "DAX", "^STOXX50E": "Euro Stoxx 50", "^FTSE": "FTSE 100",
    "SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq 100 (QQQ)", "DIA": "Dow Jones (DIA)", "IWM": "Russell 2000 (IWM)", "^VIX": "VIX",
    "^N225": "Nikkei 225", "^HSI": "Hang Seng", "000001.SS": "Shanghai Composite", "^NSEI": "Nifty 50",
    "EURUSD=X": "EUR/USD", "GC=F": "Gold (USD/oz)", "BZ=F": "Brent-Öl (USD/bbl)", "BTC-USD": "Bitcoin (USD)",
}
# Google-News-Suche über den Firmennamen (englische Schlagzeilen für FinBERT)
NEWS_QUERY = {t: NAMES[t] for t in UNIVERSE if "." in t or t == "V"}

# Quartalszahlen über SEC EDGAR gibt es nur für US-Unternehmen
SEC_TICKERS = UNIVERSE_REGIONS["USA"]
ETFS = {"SPY", "QQQ", "DIA", "IWM", "^VIX", "EUNL.DE", "EEM"}

# Risiko: Beta gegen MSCI World in EUR, risikofreier Zins = EZB-Einlagenzins
BENCHMARK = "EUNL.DE"
RISK_FREE_SERIES = "ECBDFR"

ALL_PRICE_TICKERS = sorted(set(UNIVERSE) | set(MARKET_OVERVIEW))

# FRED-Reihen, wie sie die Routinen über den FRED-Connector in dashboard/fred.json ablegen
FRED_SERIES = {
    "DFF": "Fed Funds Effective Rate",
    "DGS3MO": "US Treasury 3M",
    "DGS2": "US Treasury 2Y",
    "DGS10": "US Treasury 10Y",
    "CPI_YOY": "US-Inflation (CPI) im Jahresvergleich (%)",
    "UNRATE": "US-Arbeitslosenquote",
    "ECBDFR": "EZB-Einlagenzins",
    "HICP_YOY": "Euro-Raum-Inflation (HVPI) im Jahresvergleich (%)",
    "BUND10": "Rendite Bundesanleihe 10J (Monatsdurchschnitt)",
}

# Datenbank: DATABASE_URL (z. B. PostgreSQL), sonst SQLite-Datei
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///atlas.db")

# SEC verlangt einen aussagekräftigen User-Agent mit Kontakt-E-Mail
SEC_CONTACT_EMAIL = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
SEC_USER_AGENT = f"AtlasTerminal/1.0 ({SEC_CONTACT_EMAIL})" if SEC_CONTACT_EMAIL else ""
SEC_MAX_RPS = 5  # deutlich unter dem SEC-Limit von 10/s

RUN_SCHEDULER = os.environ.get("RUN_SCHEDULER", "1") == "1"
HTTP_TIMEOUT = 20
