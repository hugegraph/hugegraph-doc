# Finding: FN on the hstore cluster is 24-44x slower than single-node

Every other test shows a modest, roughly flat cluster-vs-single overhead
(MIW 3.2-5.5x, SIW 2.7-3.7x, FA ~2.8x, FS 1.1-2.1x, CW read ~2x). FN is
the outlier, and its slowdown grows with dataset size.

Medians (seconds, 3 measured runs unless noted):

| dataset | FN single | FN cluster | ratio |
|---|---|---|---|
| enron (36.7k v) | 1.314 | 31.019 | 23.6x |
| amazon (403k v) | 12.175 | 350.468 | 28.8x |
| youtube (1.13M v) | 22.839 | 977.269 | 42.8x |
| lj full scan (4.0M v) | 733.384 | not run (projected ~58 min/run) | - |
| lj `fns` 500k sample | 21.781 | 507.167 | 23.3x |

Why the ratio grows: the cluster's FN cost is essentially *constant per
vertex* regardless of dataset — 845us (enron), 869us (amazon), 861us
(youtube), 1014us (lj sample) per vertex — i.e. the server->store gRPC
round-trips per `g.V(batch).both()` dominate and never amortize. The
single-node RocksDB path instead gets *cheaper* per vertex as the graph
grows and caches warm (35.8us enron, 30.2us amazon, 20.1us youtube full
scans; the lj 500k random sample runs at 43.6us/vertex vs 183us/vertex
for the full cold scan).

So the trend line 23.6x -> 28.8x -> 42.8x is not noise: it is a flat
~0.9ms/vertex cluster floor divided by a single-node per-vertex cost
that shrinks with scale. Neighbor-expansion-heavy workloads on this
1PD/1Store/1Server hstore topology pay the full RPC toll per vertex
batch; batch size 500 did not amortize it.

Raw runs: results/hugegraph-{single,cluster}-*-fn*-*.json. Sample
definition (500k vertices, seed 42) in
[deviations.md](deviations.md).
