# JanusGraph on lj: full edge scans do not finish, bounded ones do

lj (3,997,962 vertices / 34,681,189 edges) is the only dataset where
JanusGraph could not complete a test. The boundary is sharp and worth
recording, because it is about scan size rather than the operation.

## Bounded scan: fine

FA reads up to the 5,000,000-edge cap. With the cap expressed
server-side as `limit(5000000)` the scan is unremarkable, and in line
with the other three systems:

| system | lj FA median |
|---|---|
| hugegraph-single | 35.2s |
| janusgraph | 71.0s |
| neo4j | 71.8s |
| hugegraph-cluster | 91.8s |

That is roughly 70,000 edges/s.

## Unbounded scan: does not finish

CW has to read every edge, so no `limit()` applies. The warmup pass read
**22,840,961 of 34,681,189 edges in 3,934s** and stopped at the 60-minute
run cap -- about 5,800 edges/s, an order of magnitude below the bounded
scan's rate, and the throughput degrades as the scan proceeds and the 8G
heap fills. The three other systems read the whole edge set:

| system | lj CW median | edges read |
|---|---|---|
| hugegraph-single | 551.6s | 34,681,189 |
| hugegraph-cluster | 1030.9s | 34,681,189 |
| neo4j | 1031.0s | 34,681,189 |
| janusgraph | capped at 3,934s | 22,840,961 (66%) |

The partial pass is committed as `janusgraph-lj-cw-w.json`, flagged
`time_capped_at_s` and `scan_incomplete`. It carries a real modularity
(0.7575 over 24,197 communities) but for two thirds of the graph, so it
is not comparable to the other three rows and is not reported as a
measured result.

A first attempt at the measured run recorded 0 edges in 0.34s: the
server was still unresponsive from the warmup, and this JanusGraph
instance does not recover from a heavy aborted scan on its own -- it has
to be restarted. That row was deleted rather than reported, and the
runner now restarts the container between phases on this dataset.

## Why the earlier FA failure was ours, not JanusGraph's

The first lj FA attempt ran an unbounded `g.E()` and stopped consuming
client-side at the cap. The server had no way to know about the cap, so
it worked toward producing all 34.7M edges, exhausted the heap and hit
the 3,600s evaluation timeout. Pushing the cap into the traversal as
`limit()` -- which is what the other three runners effectively do -- took
the same test to 71s. Recorded here so the distinction is not lost: the
unbounded-scan limit above is JanusGraph's, the earlier timeout was the
harness's.
