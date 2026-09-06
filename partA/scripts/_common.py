"""Shared helpers for the audit scripts: import the ORIGINAL fertility.py
functions unmodified, so every bug demonstration runs against the real
code the previous intern shipped, not a paraphrase of it."""
import pathlib
import sys

STARTER_KIT = pathlib.Path(__file__).resolve().parents[2] / "original"
sys.path.insert(0, str(STARTER_KIT))

import fertility as orig  # noqa: E402  (the audited script, unmodified)

CORPUS_SAMPLE = STARTER_KIT / "corpus_sample"
CORPUS_FULL = pathlib.Path(__file__).resolve().parents[1] / "corpus"
