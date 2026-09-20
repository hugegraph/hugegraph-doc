# Gap: JanusGraph FS on lj -- a single query does not finish in 60s

No FS result is reported for janusgraph on lj. This is a measured
limitation, not a missing run.

## Evidence

Against a freshly restarted server holding the complete lj graph
(3,997,962 vertices / 34,681,189 edges), with the vertex ids resolved in
advance so the traversal itself is all that is timed, the first three
shortest-path queries of the standard seed-42 set each ran to the 60s
per-query timeout and returned nothing:

```
vid entries: 3997962
query 0: result=None wall=60.1s
query 1: result=None wall=60.1s
query 2: result=None wall=60.1s
```

The same traversal -- `repeat(both().dedup())` to depth 6, the corrected
form from [janusgraph-fs.md](janusgraph-fs.md) -- answers correctly on
every smaller dataset, matching the other three systems exactly on paths
found (enron 85, amazon 81, youtube 99). Cost per query scales sharply
with graph size:

| dataset | edges | per query | 100 queries |
|---|---|---|---|
| enron | 367,662 | 1.10s | 110.3s |
| amazon | 3,387,388 | 8.39s | 838.6s |
| youtube | 2,987,624 | 24.0s | 2,404.7s |
| lj | 34,681,189 | >60s (timeout) | would exceed the 60-min run cap |

At over 60s per query, 100 queries cannot fit the 60-minute per-run cap
under any arrangement, so no measured run is possible within the rules
this campaign has been following. For comparison, the other three
systems complete all 100 lj queries in 9.4s (hugegraph-single), 17.8s
(hugegraph-cluster) and 0.26s (neo4j) -- the last two using a native
shortest-path step, which JanusGraph has no OLTP equivalent for.

## What was ruled out

- **Wedged server.** Early attempts recorded 100 queries in 0.2s with
  found=0. That was an artifact: after a large load or a heavy aborted
  scan this JVM sits at its heap ceiling and fails every request without
  running it. Those rows were deleted, not reported. The evidence above
  comes from a server restarted immediately beforehand.
- **Id resolution.** Resolving the 100 endpoints from a cold process
  needs an unindexed vertex scan that does not finish on lj. The runner
  now caches the nid -> vertex-id map at load time, so the numbers above
  time only the traversal.
- **The traversal itself.** The `simplePath()` formulation really was a
  harness bug and really did produce false negatives, but it was
  replaced before any of this; the query used here is the corrected one
  that agrees with all three other systems everywhere it completes.
