# Handoff

State: hugegraph-single, hugegraph-cluster and neo4j complete and pushed.
janusgraph in progress: enron done, amazon reloaded and re-measuring.
Its FS query was rewritten after the original one collapsed the heap and
returned false negatives -- [notes/janusgraph-fs.md](notes/janusgraph-fs.md);
enron and amazon FS are being re-measured with the corrected traversal.
Next: finish janusgraph (enron rerun, youtube, lj), then cleanup and push.
Rules added mid-campaign: [notes/deviations.md](notes/deviations.md).
