# Setup: neo4j

Neo4j Community 5.26.30 (current LTS line), official image.

- Image: `neo4j:5.26.30-community`, digest
  `sha256:3388e05ee53c8313d01acdf33e63ad175af95a92226dc8551160564439ce2c8c`
- Invocation (from [runner/neo.py](runner/neo.py), which manages the
  container):

```
docker run -d --name hg-bench-neo4j -p 17687:7687 -p 17474:7474 \
  -v /home/library/hg-bench/state/neo4j:/data \
  -e NEO4J_AUTH=neo4j/benchpass1 \
  -e NEO4J_server_memory_heap_initial__size=2g \
  -e NEO4J_server_memory_heap_max__size=8g \
  -e NEO4J_server_memory_pagecache_size=2g \
  neo4j:5.26.30-community
```

Config deltas from image default: heap 2g/8g (the 8G cap), pagecache 2g,
auth fixed for the driver. Everything else default.

Schema per fresh instance: `CREATE CONSTRAINT node_nid IF NOT EXISTS FOR
(n:node) REQUIRE n.nid IS UNIQUE` (gives the index used for lookups).

Wipe between loader runs = remove the container and its data dir, start
fresh (a root helper container clears the bind mount, since neo4j writes
as uid 7474; DETACH DELETE over tens of millions of elements is slower
and less deterministic). Restart cost is not part of any measured run.

Operations (official python driver 6.3.1, bolt):

- MIW/SIW: `UNWIND` batches of 500 / single `CREATE`; edges resolve
  endpoints via the nid index
- FN: `UNWIND $ids MATCH (v:node {nid: i})--(m) RETURN count(m)` per
  batch of 500
- FA/CW read: one streamed `MATCH (a:node)-[:link]->(b:node) RETURN
  a.nid, b.nid`
- FS: `shortestPath((a)-[*..6]-(b))` with a 60s query timeout
