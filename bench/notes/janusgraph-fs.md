# JanusGraph FS: the first query measured a heap collapse, not the database

The shortest-path traversal originally used for JanusGraph was

    g.V(s).repeat(both().simplePath())
          .until(hasId(t).or().loops().is(6))
          .hasId(t).limit(1).path().count(local)

`limit(1)` short-circuits as soon as a path is found, so reachable
targets were cheap. Unreachable ones were not: with nothing to stop it,
the traversal enumerated *every* simple path out to depth 6 and held
each one for the `simplePath()` check. On amazon that exhausted the 8G
heap, and the server stayed wedged afterwards -- `g.V().count()` still
timed out after 240s on an otherwise idle container holding 8.96 GiB.

The damage showed up as wrong answers, not just slow ones. Paths that
exist were reported as failures once the JVM was thrashing:

| dataset | found, original query | found, other three systems |
|---|---|---|
| enron | 82 | 85 |
| amazon | 3 (run 1), 24 (warmup, capped) | 81 |

Measured head-to-head on 8 amazon pairs, 60s per query:

| variant | total | outcome |
|---|---|---|
| `both().simplePath()` | 421.0s | 7 of 8 timed out; the 8th answered in 0.6s |
| `both().dedup()` | 68.5s | 8 of 8 answered, ~8.5s each |
| `both().simplePath().dedup()` | 71.7s | 8 of 8, identical lengths to dedup |

`dedup()` inside the `repeat` bounds the frontier to distinct vertices,
which is what makes it a breadth-first walk instead of a path
enumeration; because `repeat` advances level by level, the first hit is
still at minimum depth, so shortest-path semantics hold. The two
surviving variants returned identical path lengths on all 8 pairs.

The runner now uses the `dedup()` form. Its first full amazon pass
returns found=81 / unreachable=19, matching hugegraph-single,
hugegraph-cluster and neo4j exactly.

The original enron and amazon FS results were deleted rather than
reported; both datasets were re-measured with the corrected query. FS
numbers for JanusGraph therefore come from a different traversal than
the one used for the other three systems, which express the same
operation natively (HugeGraph `traversers/shortestpath`, Neo4j
`shortestPath()`); JanusGraph has no native equivalent in OLTP.

Two operational notes from the same episode, both fixed in
[runner/janus.py](../runner/janus.py):

- A client that dies mid-query leaves a stale instance-id registration
  that blocks the next startup ("A JanusGraph graph with the same
  instance id is already open"). The container now sets
  `janusgraph.graph.replace-instance-if-exists=true`.
- Resolving the 100 FS endpoint ids costs a ~114s full scan when the
  runner is resumed in a fresh process, because no `nid` index exists.
  That resolution is setup and now runs before the clock starts
  ([runner/common.py](../runner/common.py)).
