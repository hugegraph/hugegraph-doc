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

## Long-run cutoff tightened to 30 minutes (2026-09-20, lj on janusgraph)

The adaptive cutoff was lowered from 45 to 30 minutes partway through
janusgraph's lj dataset, to bound a campaign that had already lost
several hours to the two janusgraph defects recorded in
[janusgraph-fs.md](janusgraph-fs.md) and below. Effect: lj MIW and FS on
janusgraph report one measured run rather than three. Every test still
has a warmup plus at least one measured run, and every raw run is
committed. hugegraph-cluster lj MIW was already a single measured run
under the old 45-minute rule.

## JanusGraph vertex ids above 2^31 (lj only)

gremlinpython serializes a plain python int as a 32-bit GraphBinary
integer. JanusGraph vertex ids pass 2^31 once a graph reaches a few
million vertices, so binding them raised

    struct.error: 'i' format requires -2147483648 <= number <= 2147483647

mid-load, aborting lj MIW. enron, amazon and youtube were unaffected --
their id space stays below the boundary -- and lj sat close enough to it
that one MIW run completed and the next did not. The runner now wraps
every vertex id binding in `gremlin_python.statics.long`, forcing the
64-bit form. Verified directly: a plain int of 3e9 fails to serialize,
`long(3e9)` round-trips.

## JanusGraph insert batches inherited the server's 30s timeout

`insert_edges_batch` submitted without an explicit `evaluationTimeout`,
so it took the server default of 30s. A 500-edge batch exceeds that once
the graph holds tens of millions of edges, which aborted the first lj
load. All janusgraph write and per-batch read operations now carry an
explicit 900s timeout.
