"use strict";
// Atlas Terminal – Frontend. Liest nur die eigene API (die wiederum nur die Datenbank liest).

const TABS = ["MKTS", "QUOTE", "FA", "RISK", "NEWS", "ECO"];
const C = { amber: "#ffb000", up: "#22dd55", down: "#ff3b3b", blue: "#5fb4ff", muted: "#8a7a5a",
            line: "#3a2a10", grid: "#1a1308", vol: "#5a4310", ma50: "#5fb4ff", ma200: "#d46bff" };

let UNIVERSE = [];
let OVERVIEW = [];
let NAMES = {};
const state = { tab: "MKTS", ticker: "AAPL", range: "1Y", watchlist: [] };

// ---------- Hilfsfunktionen ----------
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? esc(u) : "#");
const isNum = (x) => typeof x === "number" && isFinite(x);
const fmt = (x, d = 2) => (isNum(x) ? x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) : "—");
const pct = (x, d = 2) => (isNum(x) ? `${x > 0 ? "+" : ""}${fmt(x, d)}%` : "—");
const sgn = (x) => (isNum(x) ? (x > 0 ? "up" : x < 0 ? "down" : "") : "mut");
const big = (x) => {
  if (!isNum(x)) return "—";
  const a = Math.abs(x);
  if (a >= 1e12) return fmt(x / 1e12, 2) + "T";
  if (a >= 1e9) return fmt(x / 1e9, 2) + "B";
  if (a >= 1e6) return fmt(x / 1e6, 2) + "M";
  if (a >= 1e3) return fmt(x / 1e3, 1) + "K";
  return fmt(x, 0);
};
const ts = (iso) => (iso ? new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" }) : "—");

function loadWatchlist() {
  try {
    const w = JSON.parse(localStorage.getItem("atlas.watchlist") || "null");
    if (Array.isArray(w)) return w.filter((t) => UNIVERSE.includes(t));
  } catch (_) { /* Speicher evtl. blockiert */ }
  return ["AAPL", "MSFT", "NVDA", "SPY"];
}
function saveWatchlist() {
  try { localStorage.setItem("atlas.watchlist", JSON.stringify(state.watchlist)); } catch (_) { /* egal */ }
}

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

function unavailable(entry) {
  return `<div class="na"><b>Daten nicht verfügbar</b>Fehler: ${esc(entry?.error || "unbekannt")}${
    entry?.attempted_at ? `<br><span class="mut">Letzter Versuch: ${ts(entry.attempted_at)}</span>` : ""}</div>`;
}
function staleWarn(entry) {
  return entry?.available && entry?.error
    ? `<div class="warn">⚠ Letzte Aktualisierung fehlgeschlagen (${esc(entry.error)}). Angezeigt: letzter erfolgreicher Stand.</div>` : "";
}

function panel(title, entry, body, { cls = "", delayed = false } = {}) {
  const meta = `Quelle: ${esc(entry?.source || "—")} · Zuletzt aktualisiert: ${ts(entry?.updated_at)}`;
  return `<section class="panel ${cls}">
    <div class="ph"><h2>${esc(title)}${delayed ? '<span class="delayed">DELAYED</span>' : ""}</h2><div class="meta">${meta}</div></div>
    <div class="pb">${entry && !entry.available ? unavailable(entry) : body + staleWarn(entry)}</div></section>`;
}

// ---------- SVG-Charts ----------
function lineChart(series, { h = 220, w = 900, yFmt = (v) => fmt(v, 2), zero = false } = {}) {
  const all = series.flatMap((s) => s.points.filter((p) => isNum(p.y)));
  if (!all.length) return '<div class="na"><b>Daten nicht verfügbar</b>Keine Datenpunkte</div>';
  const xs = [...new Set(series.flatMap((s) => s.points.map((p) => p.x)))].sort();
  const xi = new Map(xs.map((x, i) => [x, i]));
  let lo = Math.min(...all.map((p) => p.y)), hi = Math.max(...all.map((p) => p.y));
  if (zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  if (lo === hi) { lo -= 1; hi += 1; }
  const pad = { l: 8, r: 58, t: 8, b: 18 };
  const X = (i) => pad.l + (i / Math.max(1, xs.length - 1)) * (w - pad.l - pad.r);
  const Y = (v) => pad.t + (1 - (v - lo) / (hi - lo)) * (h - pad.t - pad.b);
  let g = "";
  for (let k = 0; k <= 4; k++) {
    const v = lo + ((hi - lo) * k) / 4;
    g += `<line x1="${pad.l}" x2="${w - pad.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="${C.grid}"/><text x="${w - pad.r + 4}" y="${Y(v) + 3}">${yFmt(v)}</text>`;
  }
  const ticks = 6;
  for (let k = 0; k < ticks; k++) {
    const i = Math.round((k / (ticks - 1)) * (xs.length - 1));
    g += `<text x="${X(i)}" y="${h - 4}" text-anchor="${k === 0 ? "start" : k === ticks - 1 ? "end" : "middle"}">${xs[i]}</text>`;
  }
  if (zero) g += `<line x1="${pad.l}" x2="${w - pad.r}" y1="${Y(0)}" y2="${Y(0)}" stroke="${C.muted}" stroke-dasharray="3 3"/>`;
  const paths = series.map((s) => {
    let d = "", pen = false;
    for (const p of s.points) {
      if (!isNum(p.y)) { pen = false; continue; }
      d += `${pen ? "L" : "M"}${X(xi.get(p.x)).toFixed(1)},${Y(p.y).toFixed(1)}`;
      pen = true;
    }
    return `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.width || 1.4}"/>`;
  }).join("");
  const legend = series.length > 1 ? `<div class="legend">${series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.label)}</span>`).join("")}</div>` : "";
  return `${legend}<svg viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="none" style="height:${h}px">${g}${paths}</svg>`;
}

function volumeBars(rows, { h = 70, w = 900 } = {}) {
  const vols = rows.map((r) => r.volume || 0);
  const max = Math.max(...vols, 1);
  const pad = { l: 8, r: 58 };
  const bw = (w - pad.l - pad.r) / rows.length;
  const bars = rows.map((r, i) => {
    const bh = ((r.volume || 0) / max) * (h - 12);
    const up = i === 0 || r.close >= rows[i - 1].close;
    return `<rect x="${(pad.l + i * bw).toFixed(1)}" y="${(h - bh).toFixed(1)}" width="${Math.max(0.6, bw - 0.6).toFixed(1)}" height="${bh.toFixed(1)}" fill="${up ? "#1d6b33" : "#7a2323"}"/>`;
  }).join("");
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="none" style="height:${h}px">${bars}<text x="${w - pad.r + 4}" y="10">Vol ${big(max)}</text></svg>`;
}

// ---------- Ansichten ----------
async function viewMKTS() {
  const d = await api(`/api/markets?watchlist=${state.watchlist.join(",")}`);
  const m = d.macro;
  const cell = (k, label, unit = "%") => {
    const e = m[k];
    return `<div class="cell"><div class="k">${label}</div>${
      e.available ? `<div class="v">${fmt(e.data.value, 2)}${unit}</div><div class="s">Stand ${esc(e.data.date)} · ${esc(e.source)} · akt. ${ts(e.updated_at)}</div>`
                  : `<div class="na"><b>Daten nicht verfügbar</b>${esc(e.error)}</div>`}</div>`;
  };
  const macroEntry = { available: true, source: "FRED (DFF, DGS10, DGS2, CPI, ECBDFR, HVPI, Bund 10J)", updated_at: m.DFF.updated_at, error: null };
  const strip = panel("MAKRO", macroEntry, `<div class="strip">${cell("DFF", "FED FUNDS")}${cell("DGS10", "UST 10Y")}${cell("2s10s", "2s10s SPREAD", " pp")}${cell("CPI_YOY", "US CPI YoY")}${cell("ECBDFR", "EZB EINLAGE")}${cell("HICP_YOY", "HVPI EURO YoY")}${cell("BUND10", "BUND 10Y (Ø Monat)")}</div>`);

  const qrow = (t) => {
    const q = d.quotes[t];
    if (!q || !q.available) return `<tr><td class="tk" data-t="${esc(t)}">${esc(t)}</td><td colspan="5" class="l down">Daten nicht verfügbar: ${esc(q?.error)}</td></tr>`;
    const x = q.data;
    return `<tr><td class="tk" data-t="${esc(t)}">${esc(t)}<br><span class="mut">${esc(NAMES[t] || "")}</span></td><td>${fmt(x.price)}</td><td class="${sgn(x.change)}">${fmt(x.change)}</td><td class="${sgn(x.change_pct)}">${pct(x.change_pct)}</td><td class="mut">${esc(x.currency || "")}</td><td class="mut">${ts(q.updated_at)}</td></tr>`;
  };
  const head = "<tr><th>Ticker</th><th>Kurs</th><th>Δ</th><th>Δ %</th><th>Whg</th><th>Aktualisiert</th></tr>";
  const firstQ = (list) => d.quotes[list.find((t) => d.quotes[t]?.available)] || d.quotes[list[0]];
  const ov = panel("MÄRKTE", firstQ(d.overview) && { ...firstQ(d.overview), available: true }, `<table>${head}${Object.entries(d.groups).map(([g, ts]) => `<tr><th class="l" colspan="6" style="color:var(--amber);padding-top:6px">${esc(g)}</th></tr>${ts.map(qrow).join("")}`).join("")}</table>`, { cls: "w6", delayed: true });
  const wlChooser = `<div class="wl">${UNIVERSE.map((t) => `<label><input type="checkbox" value="${t}" ${state.watchlist.includes(t) ? "checked" : ""}>${t}</label>`).join("")}</div>`;
  const wl = panel("BEOBACHTUNGSLISTE", firstQ(d.watchlist) && { ...firstQ(d.watchlist), available: true },
    `${wlChooser}<table style="margin-top:6px">${head}${d.watchlist.map(qrow).join("")}</table>`, { cls: "w6", delayed: true });
  $("#view").innerHTML = strip + ov + wl;
  document.querySelectorAll(".wl input").forEach((cb) => cb.addEventListener("change", () => {
    state.watchlist = [...document.querySelectorAll(".wl input:checked")].map((i) => i.value);
    if (!state.watchlist.length) state.watchlist = [UNIVERSE[0]];
    saveWatchlist();
    render();
  }));
}

async function viewQUOTE() {
  const t = state.ticker;
  const d = await api(`/api/quote/${encodeURIComponent(t)}?range=${state.range}`);
  const q = d.quote, h = d.history;
  const qBody = q.available ? `<div class="strip">
      <div class="cell"><div class="k">${esc(t)} LETZTER KURS</div><div class="v">${fmt(q.data.price)} <span class="${sgn(q.data.change)}" style="font-size:13px">${fmt(q.data.change)} (${pct(q.data.change_pct)})</span></div><div class="s">Vortagesschluss ${fmt(q.data.previous_close)} ${esc(q.data.currency || "")} · ${esc(q.data.exchange || "")}</div></div>
      ${h.available ? `<div class="cell"><div class="k">52W HOCH</div><div class="v">${fmt(h.data.high_52w)}</div><div class="s">bis ${esc(h.data.last_date)}</div></div>
      <div class="cell"><div class="k">52W TIEF</div><div class="v">${fmt(h.data.low_52w)}</div><div class="s">bis ${esc(h.data.last_date)}</div></div>` : ""}</div>` : "";
  let chart = "";
  if (h.available) {
    const rows = h.data.rows;
    const ranges = `<div class="ranges">${["1M", "6M", "1Y", "5Y"].map((r) => `<button data-r="${r}" class="${r === state.range ? "active" : ""}">${r}</button>`).join("")}</div>`;
    chart = ranges + lineChart([
      { label: "Schlusskurs", color: C.amber, points: rows.map((r) => ({ x: r.date, y: r.close })), width: 1.6 },
      { label: "SMA 50", color: C.ma50, points: rows.map((r) => ({ x: r.date, y: r.sma50 })) },
      { label: "SMA 200", color: C.ma200, points: rows.map((r) => ({ x: r.date, y: r.sma200 })) },
    ], { h: 260 }) + volumeBars(rows);
  }
  $("#view").innerHTML = panel(`QUOTE · ${t}`, q, qBody, { delayed: true }) + panel(`CHART · ${t} · ${state.range}`, h, chart, { delayed: true });
  document.querySelectorAll(".ranges button").forEach((b) => b.addEventListener("click", () => { state.range = b.dataset.r; render(); }));
}

async function viewFA() {
  const t = state.ticker;
  const d = await api(`/api/fa/${encodeURIComponent(t)}`);
  const e = d.fa;
  let body = "", filings = "";
  if (e.available) {
    const x = e.data;
    const rows = x.quarters.map((q) => `<tr><td>${esc(q.period_end)}${q.derived_q4 ? ' <span class="mut" title="Q4 = Geschäftsjahr minus Q1–Q3">(Q4 abgel.)</span>' : ""}</td>
      <td>${big(q.revenue)}</td><td class="${sgn(q.net_income)}">${big(q.net_income)}</td><td>${fmt(q.eps_diluted)}</td>
      <td>${isNum(q.gross_margin) ? fmt(q.gross_margin, 1) + "%" : "—"}</td><td class="${sgn(q.net_margin)}">${isNum(q.net_margin) ? fmt(q.net_margin, 1) + "%" : "—"}</td></tr>`).join("");
    body = `<div class="mut">${esc(x.entity)} · CIK ${esc(x.cik)} · Umsatzposition: ${esc(x.revenue_concept || "—")} · Bruttomarge aus: ${esc(x.gross_profit_basis || "nicht berichtet")}</div>
      <table><tr><th>Quartalsende</th><th>Umsatz</th><th>Jahresüberschuss</th><th>EPS verw.</th><th>Bruttomarge</th><th>Nettomarge</th></tr>${rows}</table>
      <div class="warn">„—“ = von der SEC für dieses Quartal nicht separat berichtet. Q4-Werte für Umsatz/Gewinn sind aus dem 10-K abgeleitet (Geschäftsjahr minus Q1–Q3); EPS wird nicht abgeleitet.</div>`;
    filings = ["10-K", "10-Q", "8-K"].map((f) => (x.filings[f] || []).map((r) =>
      `<tr><td>${esc(r.form)}</td><td>${esc(r.filing_date)}</td><td>${esc(r.report_date || "")}</td><td class="l">${esc(r.description || "")}</td><td class="l"><a href="${safeUrl(r.url)}" target="_blank" rel="noopener">Dokument öffnen</a></td></tr>`).join("")).join("");
    filings = `<table><tr><th>Form</th><th>Eingereicht</th><th>Berichtsdatum</th><th class="l">Beschreibung</th><th class="l">Link</th></tr>${filings}</table>`;
  }
  $("#view").innerHTML = panel(`FA · ${t} · LETZTE 8 QUARTALE`, e, body) + panel(`FILINGS · ${t} · 10-K / 10-Q / 8-K`, e, filings);
}

function heatColor(v) {
  // -1 rot · 0 dunkel · +1 grün
  const a = Math.min(1, Math.abs(v));
  return v >= 0 ? `rgba(34,221,85,${0.15 + 0.85 * a})` : `rgba(255,59,59,${0.15 + 0.85 * a})`;
}

async function viewRISK() {
  const e = await api(`/api/risk?tickers=${state.watchlist.join(",")}`);
  let body = "", heat = "";
  if (e.available) {
    const x = e.data;
    body = `<div class="mut">Je Wert die eigenen letzten 252 Handelstage (tägl. Log-Renditen, bereinigte Schlusskurse, Börsenwährung) · Beta vs. ${esc(x.benchmark.name)} auf gemeinsamen Handelstagen · risikofreier Zins: ${x.risk_free.error ? `<span class="down">Daten nicht verfügbar</span>` : `EZB-Einlagenzins ${fmt(x.risk_free.value * 100, 2)}% (Stand ${esc(x.risk_free.date)})`}</div>
      ${x.risk_free.error ? `<div class="na">${esc(x.risk_free.error)}</div>` : ""}
      <table><tr><th>Ticker</th><th>Vol. p.a.</th><th>Rendite p.a. (log)</th><th>Sharpe</th><th>Beta MSCI World</th><th>Max. Drawdown</th><th>Fenster</th></tr>${x.rows.map((r) => r.error
        ? `<tr><td class="tk">${esc(r.ticker)}</td><td colspan="6" class="l down">Daten nicht verfügbar: ${esc(r.error)}</td></tr>`
        : `<tr><td class="tk" data-t="${esc(r.ticker)}">${esc(r.ticker)}</td><td>${fmt(r.ann_vol * 100, 1)}%</td><td class="${sgn(r.ann_return)}">${pct(r.ann_return * 100, 1)}</td><td class="${sgn(r.sharpe)}">${fmt(r.sharpe, 2)}</td><td>${fmt(r.beta, 2)}</td><td class="down">${fmt(r.max_drawdown * 100, 1)}%</td><td class="mut">${esc(r.window.start)} – ${esc(r.window.end)}</td></tr>`).join("")}</table>`;
    const c = x.correlation;
    heat = `<table class="heat"><tr><th></th>${c.tickers.map((t) => `<th>${esc(t)}</th>`).join("")}</tr>${c.tickers.map((t, i) =>
      `<tr><th>${esc(t)}</th>${c.matrix[i].map((v) => `<td style="background:${heatColor(v)};color:${Math.abs(v) < 0.45 ? "#ffcc66" : "#000"}">${fmt(v, 2)}</td>`).join("")}</tr>`).join("")}</table>`;
  }
  $("#view").innerHTML = panel("RISK · BEOBACHTUNGSLISTE", e, body, { cls: "w6", delayed: true }) + panel(`KORRELATION (TÄGL. LOG-RENDITEN)${e.available && e.data.correlation.window ? ` · ${e.data.correlation.window.start} – ${e.data.correlation.window.end}` : ""}`, e, heat, { cls: "w6", delayed: true });
}

async function viewNEWS() {
  const list = state.watchlist.includes(state.ticker) ? [state.ticker, ...state.watchlist.filter((t) => t !== state.ticker)] : [state.ticker, ...state.watchlist];
  const d = await api(`/api/news?tickers=${[...new Set(list)].join(",")}`);
  const html = Object.entries(d).map(([t, e]) => {
    if (!e.available) return panel(`NEWS · ${t}`, e, "");
    const x = e.data;
    const avg = x.average ? `<span class="sent ${x.average.label}">Ø ${esc(x.average.label_de)} ${fmt(x.average.net_score, 2)}</span> <span class="mut">(${x.average.counts.positive}+ / ${x.average.counts.neutral}= / ${x.average.counts.negative}− aus ${x.average.n})</span>` : "";
    const notes = [x.sentiment_error && `Stimmung nicht verfügbar: ${x.sentiment_error}`, ...(x.feed_errors || [])].filter(Boolean).map((n) => `<div class="warn">${esc(n)}</div>`).join("");
    const rows = x.items.map((i) => `<tr><td class="mut">${ts(i.published)}</td><td class="l"><a href="${safeUrl(i.link)}" target="_blank" rel="noopener">${esc(i.title)}</a></td><td class="l mut">${esc(i.publisher || "—")}</td><td><span class="feed">${esc(i.feed)}</span></td><td>${i.sentiment ? `<span class="sent ${i.sentiment.label}">${esc(i.sentiment.label_de)}</span> ${fmt(i.sentiment.confidence * 100, 0)}%` : "—"}</td></tr>`).join("");
    const counts = x.feed_counts ? `<div class="mut">Rohtreffer je Feed: ${Object.entries(x.feed_counts).map(([k, v]) => `${esc(k)} ${v}`).join(" · ")} (angezeigt: 10 aktuellste, Duplikate entfernt)</div>` : "";
    return panel(`NEWS · ${t}`, e, `<div>Durchschnittliche Stimmung: ${avg}</div>${counts}${notes}<table><tr><th>Datum</th><th class="l">Schlagzeile</th><th class="l">Herausgeber</th><th>Feed</th><th>FinBERT (Konfidenz)</th></tr>${rows}</table>`);
  }).join("");
  $("#view").innerHTML = html;
}

async function viewECO() {
  const d = await api("/api/eco");
  const s = d.series;
  const since = (rows, years) => {
    if (!rows) return [];
    const cut = new Date(); cut.setFullYear(cut.getFullYear() - years);
    const c = cut.toISOString().slice(0, 10);
    return rows.filter((r) => r.date >= c);
  };
  const pts = (rows) => rows.map((r) => ({ x: r.date, y: r.value }));
  const ratesOk = ["DFF", "DGS3MO", "DGS2", "DGS10"].filter((k) => s[k].available);
  const ratesEntry = { available: ratesOk.length > 0, source: "FRED (DFF, DGS3MO, DGS2, DGS10)", updated_at: ratesOk.length ? s[ratesOk[0]].updated_at : null,
    error: ["DFF", "DGS3MO", "DGS2", "DGS10"].filter((k) => !s[k].available).map((k) => `${k}: ${s[k].error}`).join(" | ") || null };
  const colors = { DFF: C.amber, DGS3MO: C.muted, DGS2: C.blue, DGS10: C.up };
  const rates = lineChart(ratesOk.map((k) => ({ label: `${k} · ${s[k].name}`, color: colors[k], points: pts(since(s[k].data, 5)) })), { yFmt: (v) => fmt(v, 1) + "%" });
  const cpi = s.CPI_YOY.available ? lineChart([{ label: "CPI YoY", color: C.amber, points: pts(since(s.CPI_YOY.data, 10)) }], { yFmt: (v) => fmt(v, 1) + "%", zero: true }) : "";
  const un = s.UNRATE.available ? lineChart([{ label: "UNRATE", color: C.blue, points: pts(since(s.UNRATE.data, 10)) }], { yFmt: (v) => fmt(v, 1) + "%" }) : "";
  const curvePts = d.curve.filter((c) => isNum(c.value));
  const curveEntry = { available: curvePts.length > 0, source: "FRED (DGS3MO, DGS2, DGS10)", updated_at: s.DGS10.updated_at,
    error: d.curve.filter((c) => c.error).map((c) => `${c.series}: ${c.error}`).join(" | ") || null };
  let curve = "";
  if (curvePts.length) {
    const w = 400, h = 200, lo = Math.min(...curvePts.map((c) => c.value), 0), hi = Math.max(...curvePts.map((c) => c.value)) * 1.1 || 1;
    const X = (i) => 40 + (i * (w - 80)) / 2, Y = (v) => 15 + (1 - (v - lo) / (hi - lo)) * (h - 45);
    const path = d.curve.map((c, i) => (isNum(c.value) ? `${i === 0 ? "M" : "L"}${X(i)},${Y(c.value)}` : "")).join("");
    curve = `<svg viewBox="0 0 ${w} ${h}" width="100%" style="height:${h}px"><path d="${path}" stroke="${C.amber}" fill="none" stroke-width="2"/>${d.curve.map((c, i) => isNum(c.value)
      ? `<circle cx="${X(i)}" cy="${Y(c.value)}" r="4" fill="${C.amber}"/><text x="${X(i)}" y="${Y(c.value) - 9}" text-anchor="middle" style="fill:#ffcc66">${fmt(c.value, 2)}%</text><text x="${X(i)}" y="${h - 6}" text-anchor="middle">${c.tenor} (${esc(c.date)})</text>`
      : `<text x="${X(i)}" y="${h - 6}" text-anchor="middle" style="fill:#ff3b3b">${c.tenor}: n/v</text>`).join("")}</svg>`;
  }
  $("#view").innerHTML = panel("ZINSEN (5 JAHRE)", ratesEntry, rates, { cls: "w8" }) + panel("ZINSSTRUKTURKURVE AKTUELL", curveEntry, curve, { cls: "w4" })
    + panel("CPI IM JAHRESVERGLEICH (10 JAHRE)", s.CPI_YOY, cpi, { cls: "w6" }) + panel("ARBEITSLOSENQUOTE (10 JAHRE)", s.UNRATE, un, { cls: "w6" });
}

const VIEWS = { MKTS: viewMKTS, QUOTE: viewQUOTE, FA: viewFA, RISK: viewRISK, NEWS: viewNEWS, ECO: viewECO };

// ---------- Navigation ----------
function msg(text) {
  const m = $("#msg");
  m.hidden = !text;
  m.textContent = text || "";
}

async function render() {
  document.querySelectorAll("#fkeys button").forEach((b) => b.classList.toggle("active", b.dataset.tab === state.tab));
  $("#tickerSel").value = state.ticker;
  try {
    await VIEWS[state.tab]();
    document.querySelectorAll("#view .tk[data-t]").forEach((el) => el.addEventListener("click", () => go("QUOTE", el.dataset.t)));
  } catch (err) {
    $("#view").innerHTML = `<section class="panel"><div class="pb">${unavailable({ error: err.message })}</div></section>`;
  }
  history.replaceState(null, "", `#${state.tab}/${state.ticker}`);
}

function go(tab, ticker) {
  if (ticker) state.ticker = ticker;
  state.tab = tab;
  msg("");
  render();
}

function runCommand(raw) {
  const parts = raw.trim().toUpperCase().split(/\s+/).filter(Boolean);
  if (!parts.length) return;
  const known = [...UNIVERSE, ...OVERVIEW];
  if (TABS.includes(parts[0]) && parts.length === 1) return go(parts[0]);
  const [t, fn] = parts;
  if (!known.includes(t)) return msg(`Unbekannter Befehl oder Ticker „${t}“. Universum: ${UNIVERSE.join(" ")} · Funktionen: ${TABS.join(" ")}`);
  const tab = fn ? (fn === "DES" || fn === "GP" ? "QUOTE" : fn) : "QUOTE";
  if (!TABS.includes(tab)) return msg(`Unbekannte Funktion „${fn}“. Erlaubt: ${TABS.join(" ")}`);
  if (tab === "FA" && !UNIVERSE.includes(t)) return msg(`${t} ist nicht im Universum für FA`);
  go(tab, t);
}

async function init() {
  const u = await api("/api/universe");
  UNIVERSE = u.universe;
  OVERVIEW = u.market_overview;
  NAMES = u.names || {};
  state.watchlist = loadWatchlist();
  $("#tickerSel").innerHTML = UNIVERSE.map((t) => `<option>${t}</option>`).join("");
  $("#tickerSel").addEventListener("change", (e) => go(state.tab === "MKTS" || state.tab === "ECO" || state.tab === "RISK" ? "QUOTE" : state.tab, e.target.value));
  document.querySelectorAll("#fkeys button").forEach((b) => b.addEventListener("click", () => go(b.dataset.tab)));
  $("#cmdform").addEventListener("submit", (e) => { e.preventDefault(); runCommand($("#cmd").value); $("#cmd").value = ""; });
  document.addEventListener("keydown", (e) => {
    const m = /^F([1-6])$/.exec(e.key);
    if (m) { e.preventDefault(); go(TABS[Number(m[1]) - 1]); }
    else if (e.key === "/" && document.activeElement !== $("#cmd")) { e.preventDefault(); $("#cmd").focus(); }
  });
  const fromHash = () => {
    const [tab, tk] = decodeURIComponent(location.hash.slice(1)).split("/");
    const changed = (TABS.includes(tab) && tab !== state.tab) || ([...UNIVERSE, ...OVERVIEW].includes(tk) && tk !== state.ticker);
    if (TABS.includes(tab)) state.tab = tab;
    if ([...UNIVERSE, ...OVERVIEW].includes(tk)) state.ticker = tk;
    return changed;
  };
  fromHash();
  window.addEventListener("hashchange", () => { if (fromHash()) render(); });
  const tick = () => { $("#clock").textContent = new Date().toLocaleString("de-DE") + " · NY " + new Date().toLocaleTimeString("de-DE", { timeZone: "America/New_York" }); };
  tick(); setInterval(tick, 1000);
  setInterval(render, 5 * 60 * 1000); // Anzeige neu aus der DB lesen
  render();
}

init().catch((e) => { $("#view").innerHTML = unavailable({ error: e.message }); });
