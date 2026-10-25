"""Macht das Paket app importierbar, egal aus welchem Ordner pytest startet."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
