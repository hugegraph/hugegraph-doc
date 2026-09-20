# Handoff

State: hugegraph-single, hugegraph-cluster and neo4j complete and pushed.
janusgraph: enron, amazon and youtube complete; lj running (last dataset).
Its FS query was rewritten mid-campaign after the original collapsed the
heap and returned false negatives -- [notes/janusgraph-fs.md](notes/janusgraph-fs.md).
Corrected FS now matches the other three systems exactly on every dataset
measured (enron 85, amazon 81, youtube 99 paths found).
Next: finish janusgraph lj, then cleanup, summary and final push.
Rules added mid-campaign: [notes/deviations.md](notes/deviations.md).
