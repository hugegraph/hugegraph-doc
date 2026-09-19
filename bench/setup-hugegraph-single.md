# Setup: hugegraph-single

Single-node HugeGraph Server, RocksDB backend, from the official image.

```
docker pull hugegraph/hugegraph:latest
# digest sha256:18751704849e6b113791914b4e710a64afe41182208c7ff0af417c554ef323f9
docker run -d --name hg-bench-server -p 18080:8080 \
  -e JAVA_OPTS="-Xms2g -Xmx8g" hugegraph/hugegraph:latest
```

Readiness check: `curl http://localhost:18080/versions` returns
`{"versions":{"version":"v1","core":"1.7.0","gremlin":"3.5.1","api":"0.72.0.0"}}`.

Schema per run (created by the runner after every wipe):

- vertex label `node`, id strategy CUSTOMIZE_NUMBER (dataset ids used
  directly), no properties, label index off
- edge label `link` node->node, frequency SINGLE, no properties, label
  index off

Wipe between runs: `DELETE /graphspaces/DEFAULT/graphs/hugegraph/clear`
with the confirm message, then schema is recreated. No container restart
between runs.

API endpoints used by the runner
([runner/hg.py](runner/hg.py)):

- MIW/SIW: `POST .../graph/vertices[/batch]`, `POST .../graph/edges[/batch]`
- FN: `POST /gremlin` with alias `g -> __g_DEFAULT-hugegraph`,
  `g.V(ids).both().count()` per batch of 500
- FA/CW read: `GET .../graph/edges?limit=500&page=...` (paged scan)
- FS: `GET .../traversers/shortestpath?...&max_depth=6&direction=BOTH`
