"""Frischen Atlas-Snapshot anfordern und darauf warten (nur Standardbibliothek).

  python atlas_sync.py --request   Abruf bei GitHub anfordern und warten, bis er auf main liegt (max. 9 min)
  python atlas_sync.py             nur warten, bis der Snapshot frisch ist

Die Anfrage ist ein leerer Commit mit der Nachricht "[atlas-sync] …" auf einem eigenen Branch
claude/atlas-sync-<Zeit>. Darauf startet .github/workflows/atlas-snapshot.yml, schreibt den Snapshot nach main
und löscht den Branch. Der Commit wird mit commit-tree gebaut und nie in den lokalen Branch übernommen.
"""
import argparse
import json
import secrets
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SYNC_MARKER = "[atlas-sync]"  # Commit-Nachricht, auf die der Workflow reagiert
META = "atlas-snapshot/meta.json"


def git(*args, run=subprocess.run):
    return run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def request_sync(now=None, run=subprocess.run) -> str | None:
    """Push einen leeren Anfrage-Commit auf einen neuen claude/atlas-sync-…-Branch. Gibt den Branch zurück."""
    now = now or datetime.now(timezone.utc)
    branch = f"claude/atlas-sync-{now:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
    commit = git("commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m",
                 f"{SYNC_MARKER} Abruf angefordert {now:%Y-%m-%d %H:%M} UTC", run=run)
    sha = commit.stdout.strip()
    if commit.returncode or not sha:
        print(f"Anfrage-Commit fehlgeschlagen: {commit.stderr.strip()}")
        return None
    push = git("push", "-q", "origin", f"{sha}:refs/heads/{branch}", run=run)
    if push.returncode:
        print(f"Push der Anfrage fehlgeschlagen: {push.stderr.strip()}")
        return None
    return branch


def remote_generated_at(run=subprocess.run) -> datetime | None:
    """generated_at des Snapshots auf origin/main, frisch geholt."""
    git("fetch", "-q", "origin", "main", run=run)
    shown = git("show", f"origin/main:{META}", run=run)
    try:
        return datetime.fromisoformat(json.loads(shown.stdout)["generated_at"])
    except (ValueError, KeyError, TypeError):
        return None


def wait_for(requested: datetime, timeout_min: float, generated_at=remote_generated_at,
             sleep=time.sleep, clock=time.monotonic) -> int:
    """Warten, bis ein Snapshot ab `requested` auf main liegt. 0 = da, 1 = nicht rechtzeitig."""
    deadline = clock() + timeout_min * 60
    while True:
        last = generated_at()
        if last is not None and last >= requested - timedelta(seconds=60):  # 60 s für Uhrabweichungen
            print(f"Frischer Atlas-Snapshot von {last.astimezone():%H:%M} liegt auf main.")
            return 0
        if clock() + 20 > deadline:
            stand = f"{last.astimezone():%d.%m. %H:%M}" if last else "unbekannt"
            print(f"Der angeforderte Atlas-Snapshot kam nicht rechtzeitig (letzter Stand {stand}). "
                  "Arbeite mit dem vorhandenen Stand weiter und nenne das in der Ausgabe und unter notes.")
            return 1
        sleep(20)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", action="store_true", help="zuerst einen frischen Snapshot bei GitHub anfordern")
    ap.add_argument("--timeout-min", type=float, default=9)
    ap.add_argument("--max-age-min", type=float, default=30, help="ohne --request: so alt darf der Snapshot sein")
    args = ap.parse_args()
    if args.request:
        requested = datetime.now(timezone.utc)
        branch = request_sync(requested)
        if branch is None:
            print("Konnte keinen Snapshot anfordern; arbeite mit dem vorhandenen Stand weiter und nenne das.")
            git("pull", "-q", "--ff-only", "origin", "main")
            return 1
        print(f"Atlas-Snapshot angefordert ({branch}); warte darauf …", flush=True)
        code = wait_for(requested, args.timeout_min)
    else:
        code = wait_for(datetime.now(timezone.utc) - timedelta(minutes=args.max_age_min), args.timeout_min)
    git("pull", "-q", "--ff-only", "origin", "main")
    return code


if __name__ == "__main__":
    sys.exit(main())
