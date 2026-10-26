"""Tests für atlas_sync.py: Anfrage-Commit und Warten auf den frischen Snapshot (ohne Netzwerk)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import atlas_sync  # noqa: E402

T0 = datetime(2026, 10, 26, 7, 30, tzinfo=timezone.utc)


def test_request_pushes_marker_commit_to_own_branch():
    calls = []
    def run(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="abc123\n" if "commit-tree" in cmd else "", stderr="")
    branch = atlas_sync.request_sync(T0, run=run)
    assert branch.startswith("claude/atlas-sync-20261026-073000-")
    tree = next(c for c in calls if "commit-tree" in c)
    assert tree[tree.index("-m") + 1].startswith("[atlas-sync]")          # der Workflow reagiert auf diese Marke
    push = next(c for c in calls if "push" in c)
    assert push[-1] == f"abc123:refs/heads/{branch}"                       # nie der lokale Branch


def test_request_reports_failed_push():
    def run(cmd, **kw):
        return SimpleNamespace(returncode=1 if "push" in cmd else 0, stdout="abc\n", stderr="denied")
    assert atlas_sync.request_sync(T0, run=run) is None


def test_wait_returns_when_fresh_snapshot_arrives():
    seen = iter([T0 - timedelta(days=3), T0 - timedelta(days=3), T0 + timedelta(minutes=4)])
    clock = iter(range(0, 10_000, 20))
    assert atlas_sync.wait_for(T0, 9, generated_at=lambda: next(seen), sleep=lambda s: None, clock=lambda: next(clock)) == 0


def test_wait_gives_up_after_timeout():
    clock = iter(range(0, 10_000, 60))
    assert atlas_sync.wait_for(T0, 1, generated_at=lambda: T0 - timedelta(days=3), sleep=lambda s: None,
                               clock=lambda: next(clock)) == 1
