"""Unit-Tests der Risikokennzahlen an kleinen, von Hand gerechneten Beispielen.

Beispiel-Renditen r = [0.01, -0.01, 0.02, 0.00]
  mean(r)            = 0.02 / 4 = 0.005           -> ann. Rendite = 0.005 * 252 = 1.26
  Abweichungen       = 0.005, -0.015, 0.015, -0.005
  Quadratsumme       = 0.000025 + 0.000225 + 0.000225 + 0.000025 = 0.0005
  Varianz (ddof=1)   = 0.0005 / 3
  ann. Vol           = sqrt(0.0005/3 * 252) = sqrt(0.042) = 0.2049390153
  Sharpe (rf = 4 %)  = (1.26 - 0.04) / sqrt(0.042) = 5.952990
"""
import math

import pytest

from app import metrics
from app.fetchers.fred import parse_observations
from app.fetchers.sec import quarterly_series

R = [0.01, -0.01, 0.02, 0.00]


def prices_from(returns, p0=100.0):
    p = [p0]
    for r in returns:
        p.append(p[-1] * math.exp(r))
    return p


def test_log_returns():
    r = metrics.log_returns([100, 110, 99])
    assert r[0] == pytest.approx(math.log(1.1))          # 0.0953102
    assert r[1] == pytest.approx(math.log(0.9))          # -0.1053605
    assert metrics.log_returns(prices_from(R)) == pytest.approx(R)


def test_annualized_return():
    assert metrics.annualized_return(R) == pytest.approx(1.26)


def test_annualized_volatility():
    assert metrics.annualized_volatility(R) == pytest.approx(math.sqrt(0.042))
    assert metrics.annualized_volatility(R) == pytest.approx(0.2049390153, abs=1e-9)


def test_sharpe_ratio():
    # rf = DGS3MO / 100, z. B. DGS3MO = 4.00 -> 0.04
    assert metrics.sharpe_ratio(R, 4.00 / 100) == pytest.approx(1.22 / math.sqrt(0.042))
    assert metrics.sharpe_ratio(R, 0.04) == pytest.approx(5.952990, abs=1e-6)


def test_beta():
    market = [0.02, -0.02, 0.04, 0.00]            # Markt = 2 * Aktie
    # Cov(r, 2r) / Var(2r) = 2 Var / 4 Var = 0.5
    assert metrics.beta(R, market) == pytest.approx(0.5)
    # Aktie = 3 * Markt -> Beta 3
    assert metrics.beta([3 * m for m in market], market) == pytest.approx(3.0)
    # Markt gegen sich selbst -> 1
    assert metrics.beta(market, market) == pytest.approx(1.0)


def test_max_drawdown():
    # Hoch 120 -> Tief 90 = -25 %; später 130 -> 104 = -20 % -> Maximum ist -25 %
    assert metrics.max_drawdown([100, 120, 90, 95, 130, 104]) == pytest.approx(-0.25)
    assert metrics.max_drawdown([1, 2, 3, 4]) == pytest.approx(0.0)


def test_correlation_matrix():
    a, b, c, d = [1, 2, 3, 4], [2, 4, 6, 8], [4, 3, 2, 1], [1, -1, 1, -1]
    tickers, m = metrics.correlation_matrix({"A": a, "B": b, "C": c, "D": d})
    assert tickers == ["A", "B", "C", "D"]
    assert m[0][0] == pytest.approx(1.0)
    assert m[0][1] == pytest.approx(1.0)                      # perfekt gleichläufig
    assert m[0][2] == pytest.approx(-1.0)                     # perfekt gegenläufig
    # cov-Summe = -2, Quadratsummen 5 und 4 -> -2 / sqrt(20)
    assert m[0][3] == pytest.approx(-2 / math.sqrt(20))       # -0.4472136
    assert m[3][0] == pytest.approx(m[0][3])                  # symmetrisch


def test_align_on_dates_uses_common_days_and_window():
    h = {
        "X": [{"date": f"2024-01-0{i}", "adj_close": float(i)} for i in range(1, 7)],
        "Y": [{"date": f"2024-01-0{i}", "adj_close": float(10 * i)} for i in range(2, 7)],
    }
    dates, p = metrics.align_on_dates(h, window=3)
    assert dates == ["2024-01-04", "2024-01-05", "2024-01-06"]
    assert p["X"] == [4.0, 5.0, 6.0] and p["Y"] == [40.0, 50.0, 60.0]


def test_fred_connector_observations_parse_and_skip_missing():
    resp = {"observations": [["2026-10-21", "4.25"], ["2026-10-20", "."], ["2026-10-17", "4.26"]]}
    assert parse_observations(resp) == [{"date": "2026-10-17", "value": 4.26}, {"date": "2026-10-21", "value": 4.25}]


def test_sec_quarters_and_derived_q4():
    def e(start, end, val, form="10-Q", filed="2024-01-01"):
        return {"start": start, "end": end, "val": val, "form": form, "filed": filed}
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        e("2023-01-01", "2023-03-31", 10), e("2023-04-01", "2023-06-30", 20),
        e("2023-07-01", "2023-09-30", 30), e("2023-01-01", "2023-12-31", 100, form="10-K"),
    ]}}}}}
    q = quarterly_series(facts, "Revenues")
    assert q["2023-06-30"]["value"] == 20 and not q["2023-06-30"]["derived"]
    assert q["2023-12-31"]["value"] == 40 and q["2023-12-31"]["derived"]   # 100 - (10+20+30)


def test_export_quote_summary():
    from app.export import quote_summary
    rows = [{"date": f"d{i:03d}", "close": 100.0 + i, "adj_close": 100.0 + i, "sma50": 90.0, "sma200": None}
            for i in range(30)]
    q = {"history": {"available": True, "data": {"rows": rows, "high_52w": 140.0, "low_52w": 95.0}}}
    s = quote_summary(q, keep_days=5)["history"]["data"]
    assert len(s["rows"]) == 5
    sm = s["summary"]
    assert sm["close"] == 129.0 and sm["above_sma50"] is True and sm["above_sma200"] is False
    assert sm["perf_1m_pct"] == pytest.approx((129 / 108 - 1) * 100)   # 21 Handelstage zurück
    assert sm["perf_6m_pct"] is None                                     # zu wenig Historie
    assert sm["pct_below_52w_high"] == pytest.approx((129 / 140 - 1) * 100)


def test_fred_refresh_reads_connector_file(tmp_path, monkeypatch):
    import json
    from app.fetchers import fred as fr
    f = tmp_path / "fred.json"
    f.write_text(json.dumps({"fetched_at": "x", "series": {"DFF": {"observations": [["2026-10-21", "3.88"]]}}}))
    stored = {}
    monkeypatch.setattr(fr.db, "store_ok", lambda k, s, d: stored.__setitem__(k, d))
    monkeypatch.setattr(fr.db, "store_error", lambda k, s, e: stored.__setitem__(k, "ERR " + e))
    monkeypatch.setattr(fr.db, "delete_prefix_except", lambda p, keep: stored.__setitem__("_keep", keep))
    fr.refresh_all(f)
    assert "fred:CPIAUCSL" not in stored["_keep"] and "fred:CPI_YOY" in stored["_keep"]
    assert stored["fred:DFF"] == [{"date": "2026-10-21", "value": 3.88}]
    assert stored["fred:DGS10"].startswith("ERR") and "fehlt" in stored["fred:DGS10"]   # fehlende Reihe = Fehler, kein Wert


def test_last_window_uses_own_trading_days():
    rows = [{"date": f"d{i:03d}", "adj_close": float(100 + i)} for i in range(300)] + [{"date": "x", "adj_close": None}]
    dates, prices = metrics.last_window(rows)
    assert len(prices) == 253 and len(metrics.log_returns(prices)) == 252      # 252 Renditen
    assert dates[-1] == "d299" and prices[0] == 147.0                           # ohne Lücke (None) am Ende
