# Benchmark environment

## Host (`library`)

| Item | Value |
|---|---|
| CPU | 11th Gen Intel Core i5-11400H @ 2.70GHz, 6 cores / 12 threads |
| Memory | 15 GiB (about 13 GiB available at start), 4 GiB swap |
| Disk | NVMe, 106 GB free on / at start |
| OS kernel | Linux 7.0.0-31-generic |
| Docker | 29.5.3 (Compose v5.1.4) |
| Host JVM | Temurin OpenJDK 25.0.2 LTS (servers run their image-bundled JVMs) |
| Client | Python 3.12.3 venv: requests 2.34.2, neo4j 6.3.1, gremlinpython 3.8.2, python-igraph 1.0.0 |

All systems run in Docker on this host; the client runs on the same host
against localhost-mapped ports. One system at a time, JVM heap capped at 8G.

## Datasets

SNAP originals (not present locally; downloaded 2026-09-19 from
snap.stanford.edu, sha256 in [notes/datasets.md](notes/datasets.md)):

| Dataset | File | Vertices | Edges |
|---|---|---|---|
| enron | email-Enron.txt | 36,692 | 367,662 |
| amazon | amazon0601.txt | 403,394 | 3,387,388 |
| youtube | com-youtube.ungraph.txt | 1,134,890 | 2,987,624 |
| lj | com-lj.ungraph.txt | 3,997,962 | 34,681,189 |

## hugegraph-single

- Image: `hugegraph/hugegraph:latest`, digest
  `sha256:18751704849e6b113791914b4e710a64afe41182208c7ff0af417c554ef323f9`
  (server core 1.7.0, API 0.72.0.0, bundled JDK 11.0.32, gremlin 3.5.1)
- Backend: RocksDB (image default), graphspace `DEFAULT`, graph `hugegraph`
- Config delta from image default: `JAVA_OPTS=-Xms2g -Xmx8g` (effective
  `-Xmx8g`, verified in-process; the start script's auto-sized 6731m is
  overridden by the later flag)
- Invocation:
  `docker run -d --name hg-bench-server -p 18080:8080 -e JAVA_OPTS="-Xms2g -Xmx8g" hugegraph/hugegraph:latest`
- Note: in this 1.7.0 image the REST root is `/` (not `/apis`), paths are
  graphspace-scoped: `/graphspaces/DEFAULT/graphs/hugegraph/...`

## hugegraph-cluster

- 1 PD + 1 Store + 1 Server, backend hstore, official `:latest` images
  (digests in [setup-hugegraph-cluster.md](setup-hugegraph-cluster.md)),
  server core 1.7.0
- Heaps: pd 1g, store 4g, server 4g (three JVMs on one 15G host; per-
  process cap 8G respected)
- Invocation: `docker compose -f bench/runner/hstore-compose.yml up -d`,
  server API on `http://localhost:18081`

## neo4j

- Image: `neo4j:5.26.30-community` (current LTS), digest
  `sha256:3388e05ee53c8313d01acdf33e63ad175af95a92226dc8551160564439ce2c8c`
- Config delta from default: heap 2g/8g, pagecache 2g, auth set
- Invocation and operations: [setup-neo4j.md](setup-neo4j.md)

## janusgraph

- Image: `janusgraph/janusgraph:latest`, digest
  `sha256:75f57aff4b152ca86b4cdaeefb5335154d7fad412cffef75fa44c7504adc96d4`
  (JanusGraph 1.1.0, Gremlin 3.7.3), backend BerkeleyJE 18.3.12
- Config delta from default: BerkeleyJE template, heap 2g/8g,
  `replace-instance-if-exists=true`
- Client: gremlinpython 3.7.3 (version-matched to the server; the 3.8.x
  driver cannot talk to a 3.7.3 server)
- Invocation and operations: [setup-janusgraph.md](setup-janusgraph.md)
