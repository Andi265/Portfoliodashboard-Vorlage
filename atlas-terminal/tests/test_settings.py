"""Tests für settings.py: Snapshot-Zeitfenster und UTC-Cron aus den Routine-Zeiten."""
import sys
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import settings  # noqa: E402

BASE = {"timezone": "Europe/Berlin", "routines": {"morning": "08:30", "evening": "17:45", "days": "1-5"},
        "strategy": {"target_kern_pct": 70, "max_single_stock_pct": 15}}


def test_slots_open_one_hour_before_routine():
    s = settings.slots(BASE)
    assert s["morgen"] == (time(7, 30), time(12, 0))
    assert s["abend"] == (time(16, 45), time(21, 15))


def test_cron_covers_summer_and_winter_time():
    # 07:45 / 17:00 Berlin = 05:45+06:45 UTC bzw. 15:00+16:00 UTC
    assert settings.cron_lines(BASE) == ["45 5,6 * * 1-5", "0 15,16 * * 1-5"]


def test_cron_other_timezone_and_days():
    cfg = dict(BASE, timezone="Europe/London", routines={"morning": "07:15", "evening": "18:00", "days": "1-6"})
    assert settings.cron_lines(cfg) == ["30 5,6 * * 1-6", "15 16,17 * * 1-6"]


def test_check_flags_bad_values():
    bad = dict(BASE, timezone="Mars/Olympus", strategy={"target_kern_pct": 120, "max_single_stock_pct": 15})
    problems = settings.check(bad)
    assert any("target_kern_pct" in p for p in problems) and any("Zeitzone" in p for p in problems)


def test_template_settings_file_is_valid():
    assert settings.check(settings.load()) == []
