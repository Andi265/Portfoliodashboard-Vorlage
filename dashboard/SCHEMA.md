# `dashboard/briefing.json` – Format

Die Routine schreibt diese Datei bei jedem Lauf **komplett neu**. `python dashboard/build.py` ergänzt danach:
- Depotwerte, Gewichtungen, Allokation Kern/Satellit, Überschreitung der 15-%-Grenze (aus `qty` × `price`)
- Abstand und Status jedes Preisalarms (aus `level` und `price`)
- alle Atlas-Daten (Markt, Makro, Stimmung, Trend, Risiko) direkt aus `atlas-snapshot/`

**Trage keine berechneten Werte und keine Atlas-Zahlen von Hand ein.** Nur echte Werte aus Scalable, Journal und Websuche. Fehlt ein Wert, lass das Feld weg oder setze `null`. Dann zeigt das Dashboard „—“.

```jsonc
{
  "type": "morgen",                       // "morgen" | "abend"
  "title": "Morning-Briefing",            // "Morning-Briefing" | "Dinner-Briefing"
  "created_at": "2026-10-22T06:35:00Z",   // ISO, UTC
  "action_needed": false,                 // true = heute Handlung prüfen, false = nichts zu tun
  "headline": "1–2 Sätze: das Wichtigste dieses Briefings",

  "depot": {
    "as_of": "…",                         // valuationTimestampUtc aus get_portfolio_overview
    "reported_total_eur": 25000.00,       // valuation.total
    "cash_eur": 500.00,                    // get_portfolio_cash_breakdown → cash.cashBalance
    "target_kern_pct": 70,
    "performance": { "intraday_eur": 12.50, "week_eur": -80.00, "month_eur": 310.00, "year_eur": 1900.00 },
    "positions": [
      // kind: "ETF-Kern" (breite ETFs: MSCI World, All-World, DAX) | "ETF-Thema" | "Aktie" | "Krypto"
      { "name": "Beispiel AG", "isin": "DE000BEISP01", "kind": "Aktie",
        "qty": 10, "price": 120.00,          // filled + currentQuote.midPrice aus get_portfolio_holdings
        "day_change_pct": 1.2,                      // optional, aus get_security_quote
        "note": "optional, kurz" },
      { "name": "Krypto (z. B. BTC, ETH)", "kind": "Krypto", "value_eur": 50.00 }   // nur hier value_eur direkt (valuation.crypto)
    ]
  },

  "signals": [                            // = Tabelle „Aktuelle Signale“ aus dem Journal
    { "name": "Beispiel AG", "signal": "HALTEN",   // KAUFEN | NACHKAUFEN | HALTEN | TEILVERKAUF | VERKAUFEN | BEOBACHTEN
      "zone": "—", "stop": "100 €", "target": "150 €", "horizon": "6–12 M",
      "confidence": "mittel", "since": "2026-10-22", "reason": "1 Satz", "changed": false }  // changed = in diesem Lauf neu/geändert
  ],
  "signals_note": "nur wenn signals leer ist",

  "levels": [                             // alle aktiven Preisalarme (list_price_alerts)
    { "name": "Beispiel AG", "type": "Stop", "direction": "DOWN", "level": 100, "price": 120.00 },
    { "name": "Muster SE", "type": "Kauf", "direction": "DOWN", "level": 80, "price": 86.00, "planned": true }   // planned: true = Level ohne Preisalarm (Limit erreicht)
  ],

  "market": [                             // NUR was nicht im Atlas-Snapshot steht (Indizes, EUR/USD, Gold, Öl, Bitcoin sind dort)
    { "label": "DAX (vorbörslich)", "value": "24.310", "change_pct": -0.4, "source": "Websuche, 08:20" }
  ],

  "news": [                               // nur relevante Meldungen zu Positionen/Watchlist
    { "name": "Beispiel AG", "title": "…", "publisher": "…", "published": "ISO", "link": "https://…",
      "impact": "positiv", "why": "1 Satz, warum relevant" }          // impact: positiv | neutral | negativ
  ],

  "events":      [ { "when": "22.10. 22:05", "what": "Quartalszahlen …", "relevance": "Watchlist" } ],
  "changes":     [ "Preisalarm Beispiel AG 100 € angelegt" ],
  "open_points": [ "aus dem Journal, Abschnitt „Offene Punkte“" ],
  "weekly":      [ "nur freitags abends: Stichpunkte des Wochenrückblicks" ],
  "monthly":     [ "nur am letzten Werktag des Monats: Stichpunkte des Monats-Checks" ],
  "notes":       [ "Datenhinweise, z. B. Atlas-Snapshot veraltet, Quelle ausgefallen" ]
}
```

## `dashboard/fred.json` – FRED-Connector

Rohantworten des Tools `fred-get-series-observations`, **unverändert** übernommen:

```jsonc
{ "fetched_at": "2026-10-23T06:35:00Z",
  "source": "FRED-Connector (fred-get-series-observations)",
  "series": { "DFF": { …Antwort… }, "DGS3MO": { … }, "DGS2": { … }, "DGS10": { … }, "ECBDFR": { … }, "HICP_YOY": { … }, "BUND10": { … },
              "CPI_YOY": { …Antwort für CPIAUCSL mit units_transformation "pc1"… }, "UNRATE": { … } } }
```
`build.py` nimmt jeweils die neueste gültige Beobachtung, rechnet 2s10s = DGS10 − DGS2 (gleiches Datum) und die Sharpe-Ratio = (ann. Rendite − ECBDFR/100) / ann. Volatilität (EZB-Einlagenzins).
