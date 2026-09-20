# Handoff

State: complete. All four systems measured on all four datasets; three
gaps, all on janusgraph/lj, each with a notes entry. Benchmark
containers, volumes and images removed; wearwise and f1 untouched.

Numbers: [summary.md](summary.md) · raw runs: [results/](results/) ·
timings: [run-log.md](run-log.md)
Gaps: [notes/janusgraph-lj-fs.md](notes/janusgraph-lj-fs.md),
[notes/janusgraph-lj-scans.md](notes/janusgraph-lj-scans.md)
Method and rule changes: [notes/method.md](notes/method.md),
[notes/deviations.md](notes/deviations.md)

Next: nothing outstanding. To re-measure janusgraph lj, the cached
nid -> vertex-id map at ~/hg-bench/state/vid-lj.pkl avoids a 33-minute
reload (`janus.py <digest> lj usevid,<tests>`).
