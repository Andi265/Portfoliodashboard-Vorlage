"""Makrodaten von FRED. Quelle ist der FRED-Connector: Die Routinen rufen ihn auf und speichern
die Rohantworten in dashboard/fred.json. Dieses Modul liest die Datei in die Datenbank ein.

Werte stimmen mit dem FRED-CSV-Download überein (am 23.10.2026 für CPIAUCSL vollständig
geprüft: 956 Werte seit 1947, keine Abweichung).
"""
import json
import os
from pathlib import Path

from .. import db
from ..config import FRED_SERIES

SOURCE = "FRED, Federal Reserve Bank of St. Louis"
FRED_FILE = Path(os.environ.get("ATLAS_FRED_FILE", Path(__file__).resolve().parents[3] / "dashboard" / "fred.json"))


def parse_observations(resp):
    """Antwort von fred-get-series-observations → aufsteigende [{date, value}], ohne fehlende Werte."""
    rows = []
    for o in (resp or {}).get("observations") or []:
        date, val = (o[0], o[1]) if isinstance(o, (list, tuple)) else (o.get("date"), o.get("value"))
        try:
            rows.append({"date": date, "value": float(val)})
        except (TypeError, ValueError):
            continue  # FRED markiert fehlende Werte mit "."
    if not rows:
        raise RuntimeError("Antwort enthält keine Werte")
    return sorted(rows, key=lambda r: r["date"])


def refresh_all(path: Path = FRED_FILE):
    db.delete_prefix_except("fred:", {f"fred:{sid}" for sid in FRED_SERIES})
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        for sid in FRED_SERIES:
            db.store_error(f"fred:{sid}", f"{SOURCE} ({sid})", f"{path.name} fehlt (wird von den Routinen geschrieben)")
        return
    series = data.get("series") or {}
    for sid in FRED_SERIES:
        src = f"{SOURCE} ({sid})"
        try:
            if sid not in series:
                raise RuntimeError(f"Reihe fehlt in {path.name} (Stand {data.get('fetched_at', '?')})")
            db.store_ok(f"fred:{sid}", src, parse_observations(series[sid]))
        except Exception as e:  # noqa: BLE001
            db.store_error(f"fred:{sid}", src, f"{type(e).__name__}: {e}")
