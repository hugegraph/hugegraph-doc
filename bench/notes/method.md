# Method: reimplemented harness

socialsensor/graphdb-benchmarks was tried first and is unusable as-is:
Java-7-era build (blueprints 2.6.0, Titan 0.5.4, OrientDB 2.2, Neo4j 2.x
adapters); no HugeGraph or JanusGraph adapters at all. As the goal prompt
anticipated, the same operations are reimplemented with current drivers:
one thin runner per system under [runner/](../runner/), all sharing
[runner/common.py](../runner/common.py) so operation counts, batch sizes,
ordering and random seeds are identical across systems.

Workload shapes (matching hugegraph-benchmark-0.5.6 definitions):

- **MIW**: whole dataset, vertices then edges, batches of 500,
  single-threaded client, empty graph per run.
- **SIW**: one-at-a-time inserts into an empty graph, bounded to the first
  10,000 edges of the dataset plus their vertices on first encounter.
  (Full-dataset SIW at one-request-per-element is days per system on this
  host; the bound is identical for every system.)
- **FN**: neighbors of *all* vertices, `both()` per batch of 500 vertex
  ids, neighbor traversal forced server-side via count.
- **FA**: full edge scan touching both endpoints of every edge, page size
  500; capped at 5,000,000 edges for lj only.
- **FS**: shortest path from the dataset's first vertex to 100 random
  targets (seed 42, same targets for every system), max depth 6,
  direction BOTH, 60s per-query timeout.
- **CW**: Louvain. No portable server-side Louvain exists across these
  four systems (Neo4j needs the GDS plugin, JanusGraph has none), so CW =
  full edge read from the store through the system's own API + igraph
  `community_multilevel` (Louvain) client-side, wall time covering both.
  The clustering half is constant across systems; the read half is the
  system under test. This mirrors socialsensor's CW, which also ran
  Louvain in the client against the database.

Every test: 1 warmup pass + 3 measured runs; the median of the 3 is the
reported number. Raw per-run output in [../results/](../results/), one
JSON per run, named `<system>-<dataset>-<test>-<n>` with n in
{w,1,2,3}. Adaptive long-run rule: if any run of a test exceeds 2,700s
(45 min), remaining runs of that test are skipped (at least one measured
run is always taken); occurrences are recorded in notes/deviations.md.

MIW leaves the last run's data in place; FN/FA/FS/CW then run against it.
SIW runs before MIW on a wiped graph each time.
