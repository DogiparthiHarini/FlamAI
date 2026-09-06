# Part B — Capacity reconciliation

All numbers below are computed by [`capacity_calc.py`](capacity_calc.py), not hand-typed:

```bash
python3 partB/capacity_calc.py
```
**Full output saved to:** [`capacity_calc_output.txt`](capacity_calc_output.txt). Part B has no
dependency on the Part A corpus, so the 2026-09-06 corpus expansion (adding Bengali/Marathi,
see [NOTEBOOK.md](../NOTEBOOK.md)) does not touch anything below — re-running produced
byte-identical output to the original pass, confirmed by diff.

## B1 — KV-cache bytes/token and max concurrent 4096-token sequences

**(a) KV-cache bytes/token, exact:**

With GQA, the KV cache stores K and V per **KV head** (8), not per query head (24) — that's
the entire point of GQA, and the reason it's cheaper than MHA here.

```
bytes/token = 2 (K,V) × layers × kv_heads × head_dim × bytes_per_element(fp16)
            = 2 × 28 × 8 × 128 × 2
            = 114,688 bytes/token  =  112.0 KiB/token  (exact — no rounding)
```

**(b) Max concurrent 4096-token sequences:**

```
total_mem   = 24 GiB = 25,769,803,776 bytes        [assumption: "24 GB" read as 2^30-based GiB — see note]
usable      = 0.92 × total_mem                     = 23,708,219,474 bytes   (gpu_memory_utilization)
weights     = 4.2e9 params × 2 bytes (fp16)        =  8,400,000,000 bytes
overhead    = 1.6 GiB                              =  1,717,986,918 bytes
KV budget   = usable − weights − overhead          = 13,590,232,556 bytes  (12.66 GiB)
max tokens  = KV budget / 114,688 bytes/token       =    118,497 tokens
max seqs    = max tokens / 4096                      =      28.93  →  **28 sequences**
```

**Assumption flagged:** "24 GB" could mean 24×10⁹ (decimal, as GPU marketing usually means) or
24×2³⁰ (GiB, as memory allocators actually compute). Redoing the arithmetic with the decimal
reading gives **25 sequences** instead of 28. I use 28 (GiB reading) as primary because that's
what the serving framework's own memory accounting uses, but both numbers bracket the same
conclusion below, so the ambiguity doesn't change the finding.

**Checked against the log** (long-prompt sweep, prompt 3584 + gen 512 = 4096 = `max_model_len`,
so each sequence occupies its full context window):

```
batch  kv_cache_util  preempted_seqs
   24           0.93               0
   32           0.97               7
   48           0.97              23
```

Batch 24 fits cleanly (24 < 28, 0 preemptions, util under 1.0). Batch 32 (> 28) starts
preempting sequences — 7 of them — and batch 48 preempts 23. The predicted ceiling of ~28–29
sits exactly where the log's behavior changes qualitatively, between batch 24 (fits) and batch
32 (overflows). That's a real, falsifiable prediction confirmed by data neither cherry-picked
nor adjusted after the fact — the arithmetic was fixed before this table was pulled.

## B2 — The long-context throughput anomaly

**The anomaly:** in the prompt=3584 sweep, `reported_tok_s` rises with batch size up to 24,
then **falls** as batch size keeps increasing — the opposite of "throughput scales with
batch":

```
batch     4      8     16     24     32     48
tok/s   565.4  902.6  1311.4 1607.4 1384.0 1298.5   <- peaks at 24, falls after
```

**Mechanism, using specific rows/columns:** B1 predicted a ceiling of ~28 concurrent
4096-token sequences. `kv_cache_util` confirms the system is nearly out of KV-cache room by
batch 24 (0.93) and pinned at its ceiling (0.97) from batch 32 on. Once the cache is full, the
scheduler must **preempt** running sequences to admit new ones (`preempted_seqs`: 0 → 7 → 23
across batch 24/32/48) — a preempted sequence's KV cache is evicted, so its prefill work has to
be at least partially redone later. That's wall-clock time spent on wasted/duplicate compute
and scheduling churn rather than new tokens, so `wall_clock_s` grows faster than the token
count does (61.16s → 94.71s → 151.41s, i.e. +55%/+60% wall-clock for batch increases of
+33%/+50%), and the tok/s figure — whatever it's actually counting (see B3) — drops. `e2e_ms_p95`
corroborates: 69.2s → 97.5s → 105.4s, latency ballooning much faster than batch size,
consistent with requests sitting preempted/re-queued rather than just queuing normally.

**Proposed change + predicted effect:** cap concurrent long-context (~4096-token) requests at
24 via admission control (e.g. vLLM `max_num_seqs`/scheduler concurrency limit for this context
length), queuing the rest instead of admitting them into a cache that's already at 93% and
letting the scheduler thrash. Predicted effect: sustains the measured batch-24 throughput
(1607 reported-tok/s / 201 goodput-tok/s, see B3) under higher offered load, instead of
regressing to the measured 1298.5 reported-tok/s (162 goodput-tok/s) that batch 48 actually
delivers — i.e. avoids a **~19–20% throughput regression** that the current "just let batch
grow" behavior produces. A complementary, larger lever: fp8 KV cache (1 byte/element instead
of 2) would roughly **double** the KV budget to ~57 sequences, which should be enough to run
batch 48 without hitting the preemption cliff at all — but that changes numerical behavior
and needs an accuracy check before shipping, so we'd stage it behind the (immediately safe)
admission-control fix.

## B3 — What `reported_tok_s` actually measures, and the honest goodput

**The misread column is `reported_tok_s` itself.** It is not generation throughput. Reverse-
engineered and confirmed exactly (to 1 decimal, on all 13 rows, both sweeps):

```
reported_tok_s == (prompt_len + gen_len) × num_requests / wall_clock_s
```

i.e. it counts one-time prompt-prefill tokens at the *same rate* as actually-generated decode
tokens. Prefill is a single parallel forward pass over the whole prompt; decode is sequential,
one token at a time, memory-bandwidth-bound. Mixing them into one "tok/s" figure inflates the
number for any row with a large prompt relative to its generation length — which is exactly
the long-prompt sweep (prompt 3584, gen 512 → 87.5% of "throughput" is prefill tokens that were
never actually generated for a user).

**This is also why "longer prompts give better throughput" (Section 2, claim 1) is an
artifact, not a real finding:** it's comparing `reported_tok_s` across rows with different
prompt/gen mixes, so a bigger prompt fraction mechanically inflates the metric regardless of
whether decode got any faster.

**Honest goodput of the batch-24 long-prompt row — two independent derivations:**

```
Method 1 (definition):        n × gen_len / wall_clock_s   = 24 × 512 / 61.16   = 200.92 tok/s
Method 2 (from the log column): reported_tok_s × gen/(prompt+gen) = 1607.4 × (512/4096) = 200.93 tok/s
```

Both agree to within rounding (200.92 vs. 200.93) — strong internal confirmation that the
formula above is exactly right, not an approximation.

**What the report should have said:** *"At batch 24 with 3584-token prompts, the harness
reports 1607 tok/s, but 87.5% of that is one-time prompt-prefill tokens counted at the
decode rate. Actual sustained generation throughput ('goodput') is ~201 tok/s. This number
should never be compared across rows with different prompt/gen-length ratios, and must not be
linearly extrapolated to larger batches — the system is already at 93% KV-cache utilization at
batch 24. Batch 48 does not reach ~3200 tok/s: measured, it delivers 1298.5 reported-tok/s
(≈162 goodput-tok/s) — lower than batch 24, not higher — because of KV-cache-driven
preemption (23 sequences preempted)."*

## B4 — Metric to confirm the B2 mechanism

We'd pull the serving stack's **preemption counter** — in vLLM terms, the cumulative
`num_preemptions_total` counter (or equivalently the scheduler's swap/recompute-preemption
event log), cross-referenced against the **KV-cache occupancy gauge**
(`gpu_cache_usage_perc`) sampled continuously through the run rather than as a single peak
value. The mechanism predicts a specific, checkable shape: `gpu_cache_usage_perc` should climb
smoothly through the batch-4→24 runs and then **pin at its ceiling** (matching the log's 0.97)
for the entire duration of the batch-32/48 runs, and `num_preemptions_total` should sit at
exactly 0 until the moment occupancy first pins, then start incrementing — i.e. the first
preemption event should line up in time with the cache hitting its ceiling, not before. That
time-alignment is the actual confirmation of causality; the aggregate CSV columns we have
(`kv_cache_util`, `preempted_seqs` as end-of-run summaries) are consistent with the mechanism
but don't prove the ordering, since they're already collapsed to one number per run.
