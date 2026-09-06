#!/usr/bin/env python3
"""
BUG 3 (code bug / statistical): fertility.py:64-67 averages the
PER-LINE ratio (macro-average = mean of tokens_i/words_i), not the
CORPUS ratio (micro-average = sum(tokens_i)/sum(words_i)). These are
not the same number whenever line lengths vary, and macro-averaging
lets short lines (where BPE boundary effects are proportionally larger)
dominate the mean regardless of how much text they actually represent.
Standard fertility definitions in the tokenizer literature (e.g. Rust
et al. 2021 "How Good is Your Tokenizer?") use the corpus-level
(micro) ratio for exactly this reason.
"""
from _common import orig, CORPUS_SAMPLE, CORPUS_FULL

encode = orig.load_tokenizer("gpt2")


def macro_and_micro(lines, encode):
    tot_tokens = tot_words = 0
    per_line = []
    for line in lines:
        line = line.lower()
        tokens = encode(line)
        words = line.split(" ")
        per_line.append(len(tokens) / len(words))
        tot_tokens += len(tokens)
        tot_words += len(words)
    macro = sum(per_line) / len(per_line)
    micro = tot_tokens / tot_words
    return macro, micro


for label, corpus_dir, files in [
    ("SAMPLE", CORPUS_SAMPLE, {"eng": "eng_sample.txt", "hin": "hin_sample.txt"}),
    ("FULL FLORES-200", CORPUS_FULL, {lang: f"{lang}.txt" for lang in
                                       ["eng", "hin", "ben", "mar", "kan", "tam", "tel", "mal"]}),
]:
    print(f"--- {label} ---")
    vals = {}
    for lang, fname in files.items():
        lines = orig.read_lines(str(corpus_dir / fname))
        macro, micro = macro_and_micro(lines, encode)
        vals[lang] = (macro, micro)
        pct = (macro - micro) / micro * 100
        print(f"{lang}: macro(as-shipped)={macro:.4f}  micro(corpus total)={micro:.4f}  "
              f"macro overstates by {pct:+.2f}%")
    if "eng" in vals and "hin" in vals:
        macro_ratio = vals["hin"][0] / vals["eng"][0]
        micro_ratio = vals["hin"][1] / vals["eng"][1]
        print(f"  hin/eng ratio: macro={macro_ratio:.3f}  micro={micro_ratio:.3f}  "
              f"({(macro_ratio/micro_ratio - 1)*100:+.2f}% difference from averaging choice alone)")
    print()
