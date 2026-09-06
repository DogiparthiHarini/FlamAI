#!/usr/bin/env python3
"""
build_corpus.py -- assemble the A1 eval corpus from FLORES-200 devtest.

Copies the eight language files we use (English, Hindi, Bengali, Marathi,
Kannada, Tamil, Telugu, Malayalam) out of the raw FLORES-200 download into
partA/corpus/, renames them to simple language codes, and sanity-checks
that all files are still sentence-aligned (same line count, no reordering).

Revision 2026-09-06: added Bengali (ben) and Marathi (mar) so Part A's
language coverage matches the six languages Part C's product ask targets
(Hindi, Kannada, Tamil, Telugu, Bengali, Marathi). See NOTEBOOK.md,
"Revision -- 2026-09-06" for why and what changed downstream.
"""
import pathlib

RAW = pathlib.Path(__file__).resolve().parents[2] / "raw_downloads" / "flores200_dataset" / "devtest"
OUT = pathlib.Path(__file__).resolve().parents[1] / "corpus"
OUT.mkdir(parents=True, exist_ok=True)

# FLORES-200 code -> our short code
LANGS = {
    "eng_Latn": "eng",
    "hin_Deva": "hin",
    "ben_Beng": "ben",
    "mar_Deva": "mar",
    "kan_Knda": "kan",
    "tam_Taml": "tam",
    "tel_Telu": "tel",
    "mal_Mlym": "mal",
}

counts = {}
for flores_code, short in LANGS.items():
    src = RAW / f"{flores_code}.devtest"
    lines = src.read_text(encoding="utf-8").splitlines()
    dst = OUT / f"{short}.txt"
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    counts[short] = len(lines)
    print(f"{short:5s} <- {flores_code:10s} {len(lines)} lines -> {dst}")

assert len(set(counts.values())) == 1, f"LINE COUNT MISMATCH, corpus is not parallel: {counts}"
print(f"\nOK: all {len(LANGS)} files have {list(counts.values())[0]} parallel lines.")
