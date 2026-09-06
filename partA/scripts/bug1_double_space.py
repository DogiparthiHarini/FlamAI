#!/usr/bin/env python3
"""
BUG 1 (code bug): `words = line.split(" ")` in fertility.py:62 does not
collapse runs of whitespace. A double space produces a phantom empty-
string "word", inflating len(words) and therefore *deflating* the
reported fertility (tokens/word) for any affected line.

Evidence: isolate the lines with a double space, show split(" ") vs
split() word counts, then show the effect on the corpus-level number
fertility.py actually prints (with the real gpt2 tokenizer, real
analyze() logic copy for the two variants).
"""
from _common import orig, CORPUS_SAMPLE, CORPUS_FULL

encode = orig.load_tokenizer("gpt2")


def analyze_variant(lines, encode, split_fn):
    """Same math as fertility.analyze(), parameterized on the word-split
    function so we can isolate ONLY that one change."""
    per_line_fertility = []
    for line in lines:
        line = line.lower()
        tokens = encode(line)
        words = split_fn(line)
        per_line_fertility.append(len(tokens) / len(words))
    return sum(per_line_fertility) / len(per_line_fertility)


def find_double_space_lines(lines):
    return [(i, l) for i, l in enumerate(lines) if "  " in l]


for label, path in [("SAMPLE (corpus_sample)", CORPUS_SAMPLE / "eng_sample.txt"),
                     ("SAMPLE (corpus_sample)", CORPUS_SAMPLE / "hin_sample.txt")]:
    lines = orig.read_lines(str(path))
    hits = find_double_space_lines(lines)
    print(f"\n=== {path.name} ===")
    print(f"lines with a double space: {len(hits)} / {len(lines)}")
    for i, l in hits:
        buggy = l.lower().split(" ")
        fixed = l.lower().split()
        print(f"  line {i}: split(' ') -> {len(buggy)} words (incl. {buggy.count('')} empty) "
              f"| split() -> {len(fixed)} words | text: {l!r}")

    fert_buggy = analyze_variant(lines, encode, lambda s: s.split(" "))
    fert_fixed = analyze_variant(lines, encode, lambda s: s.split())
    pct = (fert_buggy - fert_fixed) / fert_fixed * 100
    print(f"  corpus fertility  buggy split(' ')={fert_buggy:.4f}   fixed split()={fert_fixed:.4f}   "
          f"distortion={pct:+.2f}%")

print("\n=== FULL FLORES-200 corpus (1012 lines/lang) -- does the bug survive at scale? ===")
for lang in ["eng", "hin", "ben", "mar", "kan", "tam", "tel", "mal"]:
    path = CORPUS_FULL / f"{lang}.txt"
    lines = orig.read_lines(str(path))
    hits = find_double_space_lines(lines)
    fert_buggy = analyze_variant(lines, encode, lambda s: s.split(" "))
    fert_fixed = analyze_variant(lines, encode, lambda s: s.split())
    pct = (fert_buggy - fert_fixed) / fert_fixed * 100
    print(f"{lang}: double-space lines={len(hits):4d}/{len(lines)}  "
          f"buggy={fert_buggy:.4f}  fixed={fert_fixed:.4f}  distortion={pct:+.3f}%")
