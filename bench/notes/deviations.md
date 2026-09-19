# Deviations from the original plan

## 60-minute per-run cap (added 2026-09-20, before any lj run on the cluster)

Rule change during the campaign: no single test run may exceed 60
minutes; any run projected to exceed it gets capped. Mechanics in the
harness ([runner/common.py](../runner/common.py)):

- Streaming tests (miw, siw, fn/fns, fa, fs, cw's read phase) stop
  cleanly at 3,600s; the run's JSON carries `time_capped_at_s` and the
  ops actually completed, so throughput stays comparable.
- If the *final* miw run of a dataset is capped, the load is completed
  untimed afterwards (recorded as run `t`, `setup_topup: true`) so the
  query tests still see the complete graph. A top-up is setup, not a
  test run.
- The earlier 45-minute adaptive rule (skip runs 2-3 after a long run)
  stays.

## FN on lj: fixed 500,000-vertex sample (`fns` test)

Full FN on lj is ~58 min/run on hugegraph-cluster (per-vertex cost is
~0.87ms there, near-constant across datasets — see
[fn-cluster-slowdown.md](fn-cluster-slowdown.md)) and unknown-but-worse
on JanusGraph. Per the cap rule, lj FN is measured from here on as
`fns`: `random.Random(42).sample(sorted_vertices, 500_000)` — the same
sample for every system. hugegraph-single's full-scan lj fn results
(already recorded) stay in results/; its `fns` rerun on the same loaded
lj graph makes the cross-system comparison. Every other dataset keeps
the full FN pass.

## SIW bound, FA cap on lj

In [method.md](method.md) from the start: SIW bounded to the first
10,000 edges; FA capped at 5,000,000 edges for lj. Identical for every
system.
