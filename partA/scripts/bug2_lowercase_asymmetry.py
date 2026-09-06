#!/usr/bin/env python3
"""
BUG 2 (code bug): fertility.py:60 does `line = line.lower()` "so casing
doesn't add noise to the comparison" -- applied uniformly to every
language. But `.lower()` is a Latin/Cyrillic/Greek-casing operation:
Devanagari, Kannada, Tamil, Telugu and Malayalam have no case distinction
at all, so `.lower()` is a no-op there. The "denoising" step is real for
English (and shrinks its token count, because GPT-2's BPE vocab has
dedicated merges for common lowercase words but often falls back to
more, shorter tokens for capitalized/rare-case forms) and exactly zero
for every Indic language in scope. That means the preprocessing is NOT
applied symmetrically across the languages being compared, and it
moves the English number specifically -- which is the denominator of
every cross-language ratio in the report.
"""
from _common import orig, CORPUS_SAMPLE, CORPUS_FULL

encode = orig.load_tokenizer("gpt2")


def is_noop_lower(lines):
    changed = sum(1 for l in lines if l.lower() != l)
    return changed, len(lines)


def fertility(lines, encode, do_lower):
    per_line = []
    for line in lines:
        if do_lower:
            line = line.lower()
        tokens = encode(line)
        words = line.split(" ")
        per_line.append(len(tokens) / len(words))
    return sum(per_line) / len(per_line)


print("Is .lower() a no-op for each language? (lines changed / total)\n")
for label, corpus_dir, files in [
    ("SAMPLE", CORPUS_SAMPLE, {"eng": "eng_sample.txt", "hin": "hin_sample.txt"}),
    ("FULL FLORES-200", CORPUS_FULL, {lang: f"{lang}.txt" for lang in
                                       ["eng", "hin", "ben", "mar", "kan", "tam", "tel", "mal"]}),
]:
    print(f"--- {label} ---")
    for lang, fname in files.items():
        lines = orig.read_lines(str(corpus_dir / fname))
        changed, total = is_noop_lower(lines)
        fert_with = fertility(lines, encode, do_lower=True)
        fert_without = fertility(lines, encode, do_lower=False)
        pct = (fert_with - fert_without) / fert_without * 100
        print(f"{lang}: lower() changes {changed:4d}/{total} lines | "
              f"fertility WITH lower()={fert_with:.4f}  WITHOUT={fert_without:.4f}  "
              f"delta={pct:+.2f}%")
    print()

print("=== Net effect on the headline eng-vs-X ratio (FULL corpus, gpt2) ===")
eng_lines = orig.read_lines(str(CORPUS_FULL / "eng.txt"))
eng_with = fertility(eng_lines, encode, True)
eng_without = fertility(eng_lines, encode, False)
for lang in ["hin", "ben", "mar", "kan", "tam", "tel", "mal"]:
    lines = orig.read_lines(str(CORPUS_FULL / f"{lang}.txt"))
    x_with = fertility(lines, encode, True)   # identical to x_without for these scripts
    ratio_with = x_with / eng_with
    ratio_without = x_with / eng_without
    print(f"{lang}/eng ratio AS SHIPPED (both lowercased) = {ratio_with:.3f}   "
          f"IF NEITHER is lowercased = {ratio_without:.3f}   "
          f"(ratio inflated by {(ratio_with/ratio_without - 1)*100:+.2f}% due to lowercasing only touching eng)")
