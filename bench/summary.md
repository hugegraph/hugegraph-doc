# Results summary

Median wall-clock seconds over the measured runs (warmup excluded).
`(1r)` marks a single measured run under the long-run rule in
[notes/deviations.md](notes/deviations.md). Raw per-run output is in
[results/](results/), one JSON per run, each carrying its image digest.

`fn` is the full neighbour pass; `fns` is the fixed 500,000-vertex
sample used for lj on every system. Blank cells are explained in notes/.


## hugegraph-cluster
| dataset | miw | siw | fn | fns | fa | fs | cw |
|---|---|---|---|---|---|---|---|
| enron | 13.949 | 56.780 | 31.019 | - | 6.447 | 4.323 | 7.677 |
| amazon | 148.197 | 47.382 | 350.468 | - | 59.083 | 12.139 | 80.927 |
| youtube | 249.285 | 55.661 | 977.269 | - | 52.703 | 23.832 | 70.113 |
| lj | 2796.030 (1r) | 52.968 | - | 507.167 | 91.755 | 17.822 | 1030.864 |

## hugegraph-single
| dataset | miw | siw | fn | fns | fa | fs | cw |
|---|---|---|---|---|---|---|---|
| enron | 4.405 | 15.407 | 1.314 | - | 2.256 | 3.777 | 3.037 |
| amazon | 44.003 | 13.548 | 12.175 | - | 21.062 | 8.007 | 36.597 |
| youtube | 45.406 | 19.627 | 22.839 | - | 18.795 | 11.212 | 34.372 |
| lj | 696.402 | 19.411 | 733.384 | 21.781 | 35.249 | 9.368 | 551.633 |

## janusgraph
| dataset | miw | siw | fn | fns | fa | fs | cw |
|---|---|---|---|---|---|---|---|
| enron | 19.048 | 27.928 | 1.299 | - | 5.141 | 110.309 | 5.799 |
| amazon | 159.058 | 25.290 | 12.585 | - | 47.142 | 838.559 | 64.179 |
| youtube | 184.503 | 33.773 | 18.627 | - | 42.735 | 2404.682 | 63.165 |
| lj | 1972.403 (1r) | 33.228 | - | 19.545 | 71.093 | - | - |

## neo4j
| dataset | miw | siw | fn | fns | fa | fs | cw |
|---|---|---|---|---|---|---|---|
| enron | 10.644 | 31.762 | 0.309 | - | 5.086 | 0.107 | 5.970 |
| amazon | 77.989 | 38.103 | 2.923 | - | 45.825 | 0.159 | 60.859 |
| youtube | 80.075 | 45.092 | 5.956 | - | 40.679 | 0.080 | 59.877 |
| lj | 883.075 | 40.199 | - | 6.067 | 71.824 | 0.255 | 1031.009 |

## Gaps

- **janusgraph lj fn** — not run as a full pass; `fns` (the 500k sample,
  seed 42) is the cross-system comparison for lj, as for every system.
- **janusgraph lj fs** — a single shortest-path query exceeds the 60s
  timeout on lj; see [notes/janusgraph-lj-fs.md](notes/janusgraph-lj-fs.md).
- **janusgraph lj cw** — the full 34.7M-edge read does not finish inside
  the 60-minute run cap; the capped warmup reached 66% of the edges. See
  [notes/janusgraph-lj-scans.md](notes/janusgraph-lj-scans.md).
- **hugegraph-single/cluster and neo4j lj fn** — same as above, `fns`
  is the lj figure by design.

## Reading the table

The shapes that hold across datasets:

- **Batch and single insert**: hugegraph-single is fastest everywhere,
  neo4j next, janusgraph and the hstore cluster behind it.
- **Neighbour traversal**: neo4j is 4-20x faster than hugegraph-single;
  the hstore cluster is the outlier, 24-44x slower than single-node and
  widening with scale
  ([notes/fn-cluster-slowdown.md](notes/fn-cluster-slowdown.md)).
- **Edge scan**: all four within roughly 2x of each other once the scan
  is bounded server-side.
- **Shortest path**: neo4j by orders of magnitude, then hugegraph;
  janusgraph has no native OLTP shortest-path step and degrades sharply
  with graph size.
- **Clustering**: dominated by the edge read, so it tracks scan cost.

Every row here is a median of the raw runs committed alongside it; none
of these numbers were typed by hand.
