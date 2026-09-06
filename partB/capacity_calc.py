#!/usr/bin/env python3
"""B1-B3 arithmetic, computed (not hand-typed) so every number here is
re-derivable by running this file against bench/bench_log.csv."""
import csv
import pathlib

BENCH = pathlib.Path(__file__).resolve().parents[1] / "original" / "bench" / "bench_log.csv"

# ---- model_spec.md, transcribed verbatim ----
LAYERS = 28
KV_HEADS = 8
HEAD_DIM = 128
BYTES_FP16 = 2
TOTAL_PARAMS = 4.2e9
GPU_MEM_GB = 24            # "1x NVIDIA L4 (24 GB)"
GPU_UTIL = 0.92            # gpu_memory_utilization
NON_KV_OVERHEAD_GB = 1.6
MAX_MODEL_LEN = 4096

GiB = 1024 ** 3

print("=" * 70)
print("B1a: exact KV-cache bytes/token")
print("=" * 70)
# GQA: cache size depends on KV heads, not Q heads. 2x for K and V.
bytes_per_token = 2 * LAYERS * KV_HEADS * HEAD_DIM * BYTES_FP16
print(f"bytes/token = 2 (K,V) x {LAYERS} layers x {KV_HEADS} kv_heads x {HEAD_DIM} head_dim x {BYTES_FP16} bytes(fp16)")
print(f"            = {bytes_per_token:,} bytes/token = {bytes_per_token/1024:.1f} KiB/token")

print()
print("=" * 70)
print("B1b: max concurrent 4096-token sequences")
print("=" * 70)
total_mem = GPU_MEM_GB * GiB
print(f"assumption: '24 GB' = 24 x 2^30 bytes = {total_mem:,} bytes (flagged assumption -- GiB, not decimal GB)")
usable = total_mem * GPU_UTIL
print(f"usable budget = {GPU_UTIL} x total_mem = {usable:,.0f} bytes ({usable/GiB:.3f} GiB)")
weights_bytes = TOTAL_PARAMS * BYTES_FP16
print(f"weights = {TOTAL_PARAMS:.2e} params x {BYTES_FP16} bytes(fp16) = {weights_bytes:,.0f} bytes ({weights_bytes/GiB:.3f} GiB)")
overhead_bytes = NON_KV_OVERHEAD_GB * GiB
print(f"non-KV overhead = {NON_KV_OVERHEAD_GB} GiB = {overhead_bytes:,.0f} bytes")
kv_budget = usable - weights_bytes - overhead_bytes
print(f"KV-cache budget = usable - weights - overhead = {kv_budget:,.0f} bytes ({kv_budget/GiB:.3f} GiB)")
max_tokens = kv_budget / bytes_per_token
print(f"max total cached tokens = {kv_budget:,.0f} / {bytes_per_token:,} = {max_tokens:,.0f} tokens")
max_seqs = max_tokens / MAX_MODEL_LEN
print(f"max concurrent {MAX_MODEL_LEN}-token sequences = {max_tokens:,.0f} / {MAX_MODEL_LEN} = {max_seqs:.2f} -> {int(max_seqs)} sequences")

print()
print("=" * 70)
print("Check prediction against the log (long-prompt sweep, prompt+gen = 4096 = max_model_len)")
print("=" * 70)
rows = list(csv.DictReader(open(BENCH)))
long_rows = [r for r in rows if int(r["prompt_len"]) == 3584]
print(f"{'batch':>6}{'kv_cache_util':>15}{'preempted_seqs':>16}{'wall_clock_s':>14}{'reported_tok_s':>16}")
for r in long_rows:
    print(f"{r['batch_size']:>6}{r['kv_cache_util']:>15}{r['preempted_seqs']:>16}{r['wall_clock_s']:>14}{r['reported_tok_s']:>16}")
print(f"\npredicted ceiling ~{int(max_seqs)} concurrent full-length seqs. "
      f"Log: batch=24 -> 0 preemptions (fits); batch=32 -> 7 preempted "
      f"(32 > {int(max_seqs)}, overflow matches prediction); batch=48 -> 23 preempted (worse overflow).")

print()
print("=" * 70)
print("B2/B3: reverse-engineer what reported_tok_s actually counts")
print("=" * 70)
print(f"{'batch':>6}{'prompt':>8}{'gen':>6}{'wall_s':>10}{'reported_tok_s':>15}{'(p+g)*n/wall':>14}{'match?':>8}")
for r in rows:
    n, p, g, w, rep = int(r["num_requests"]), int(r["prompt_len"]), int(r["gen_len"]), float(r["wall_clock_s"]), float(r["reported_tok_s"])
    predicted = (p + g) * n / w
    match = abs(predicted - rep) / rep < 0.01
    print(f"{n:>6}{p:>8}{g:>6}{w:>10.2f}{rep:>15.1f}{predicted:>14.1f}{'YES' if match else 'no':>8}")

print()
print("=" * 70)
print("Honest goodput (generated tokens/s only) -- two independent derivations, batch=24 long-prompt row")
print("=" * 70)
r24 = [r for r in long_rows if r["batch_size"] == "24"][0]
n, p, g, w, rep = int(r24["num_requests"]), int(r24["prompt_len"]), int(r24["gen_len"]), float(r24["wall_clock_s"]), float(r24["reported_tok_s"])
goodput_direct = n * g / w
goodput_from_reported = rep * (g / (p + g))
print(f"Method 1 (definition):        n*gen_len/wall_clock_s = {n}*{g}/{w} = {goodput_direct:.2f} tok/s")
print(f"Method 2 (from reported col): reported_tok_s * gen/(prompt+gen) = {rep}*({g}/{p+g}) = {goodput_from_reported:.2f} tok/s")
print(f"agreement: {'YES' if abs(goodput_direct-goodput_from_reported) < 0.5 else 'NO'} (within rounding)")

print()
print("Full goodput table (all rows), for context:")
print(f"{'batch':>6}{'prompt':>8}{'gen':>6}{'reported_tok_s':>15}{'goodput_tok_s':>15}{'goodput/reported':>18}")
for r in rows:
    n, p, g, w, rep = int(r["num_requests"]), int(r["prompt_len"]), int(r["gen_len"]), float(r["wall_clock_s"]), float(r["reported_tok_s"])
    goodput = n * g / w
    print(f"{n:>6}{p:>8}{g:>6}{rep:>15.1f}{goodput:>15.2f}{goodput/rep:>18.3f}")

print()
print("What batch48 'really' delivers vs the report's linear extrapolation:")
r48 = [r for r in long_rows if r["batch_size"] == "48"][0]
n, p, g, w, rep = int(r48["num_requests"]), int(r48["prompt_len"]), int(r48["gen_len"]), float(r48["wall_clock_s"]), float(r48["reported_tok_s"])
goodput48 = n * g / w
print(f"report's claim: batch48 ~ 3200 tok/s (linear extrapolation from batch24's 1607.4 reported_tok_s x2)")
print(f"actual log:     batch48 reported_tok_s = {rep} (LOWER than batch24's 1607.4, not higher)")
print(f"actual goodput: batch48 = {goodput48:.2f} tok/s (also lower than batch24 goodput of {goodput_direct:.2f})")
