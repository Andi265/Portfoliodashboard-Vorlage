"""Persönliche Einstellungen aus settings.json (nur Standardbibliothek).

  python settings.py          # Einstellungen anzeigen und prüfen
  python settings.py cron     # UTC-Cron-Zeilen für den Snapshot-Workflow (vor jeder Routine)
"""
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
FILE = ROOT / "settings.json"
SNAPSHOT_LEAD_MIN = 45    # Snapshot startet 45 Minuten vor der Routine
SLOT_OPEN_BEFORE_MIN = 60  # ab 60 Minuten vor der Routine zählt ein Lauf zum Slot
SLOT_LENGTH_H = 4.5        # danach zählt er noch 4,5 Stunden (verspätete GitHub-Starts)


def load(path: Path = FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def slots(cfg: dict) -> dict:
    """Zeitfenster (lokale Zeit) je Slot: {"morgen": (start, ende), "abend": (start, ende)}."""
    out = {}
    for name, key in (("morgen", "morning"), ("abend", "evening")):
        r = datetime.combine(date(2000, 1, 3), _hm(cfg["routines"][key]))
        start = r - timedelta(minutes=SLOT_OPEN_BEFORE_MIN)
        end = start + timedelta(hours=SLOT_LENGTH_H)
        out[name] = (start.time(), end.time() if end.date() == start.date() else time(23, 59))
    return out


def cron_lines(cfg: dict) -> list:
    """UTC-Cron je Slot für Sommer- und Winterzeit (GitHub plant nur in UTC)."""
    tz = ZoneInfo(cfg["timezone"])
    days = cfg["routines"].get("days", "1-5")
    lines = []
    for key in ("morning", "evening"):
        local = datetime.combine(date(2000, 1, 3), _hm(cfg["routines"][key])) - timedelta(minutes=SNAPSHOT_LEAD_MIN)
        hours = set()
        for probe in (date(2026, 1, 15), date(2026, 7, 15)):  # Winter- und Sommerzeit
            utc = datetime.combine(probe, local.time(), tzinfo=tz).astimezone(ZoneInfo("UTC"))
            hours.add(utc.hour)
        lines.append(f'{local.minute} {",".join(str(h) for h in sorted(hours))} * * {days}')
    return lines


def check(cfg: dict) -> list:
    problems = []
    s = cfg.get("strategy", {})
    if not 0 < s.get("target_kern_pct", 0) < 100:
        problems.append("strategy.target_kern_pct muss zwischen 0 und 100 liegen")
    if not 0 < s.get("max_single_stock_pct", 0) <= 100:
        problems.append("strategy.max_single_stock_pct muss zwischen 0 und 100 liegen")
    try:
        ZoneInfo(cfg["timezone"])
    except Exception:  # noqa: BLE001
        problems.append(f"Unbekannte Zeitzone {cfg.get('timezone')!r}")
    for key in ("morning", "evening"):
        try:
            _hm(cfg["routines"][key])
        except Exception:  # noqa: BLE001
            problems.append(f"routines.{key} muss HH:MM sein")
    return problems


if __name__ == "__main__":
    cfg = load()
    if len(sys.argv) > 1 and sys.argv[1] == "cron":
        print("\n".join(cron_lines(cfg)))
        sys.exit(0)
    print(json.dumps(cfg, ensure_ascii=False, indent=1))
    print("Snapshot-Slots:", {k: f"{a:%H:%M}–{b:%H:%M}" for k, (a, b) in slots(cfg).items()})
    print("Workflow-Cron (UTC):", cron_lines(cfg))
    problems = check(cfg)
    print("Prüfung:", "ok" if not problems else problems)
    sys.exit(1 if problems else 0)
