# Setup: hugegraph-cluster

Distributed HugeGraph: 1 PD + 1 Store + 1 Server, hstore backend, all on
this host via the official images, wired per apache/hugegraph
`docker/docker-compose-hstore.yml` adapted in
[runner/hstore-compose.yml](runner/hstore-compose.yml) (hubble dropped,
explicit heaps, server on host port 18081).

```
docker compose -f bench/runner/hstore-compose.yml up -d
```

Images (all `:latest`, digests):

- `hugegraph/pd` sha256:f77e25d14642acc6bc012d5b8c9d73ef56b3f336bc0a5d59580a57937872900f
- `hugegraph/store` sha256:d4b770e16d23ce5f90cd3ea818cc5233a887010da728adbb921528c42e87b660
- `hugegraph/server` sha256:bcc673884668c66350db87a18d5ffab250451d76a3edbbcf57649c1c44ec5690

Server reports core 1.7.0, api 0.72.0.0; graph `hugegraph` in graphspace
`DEFAULT`, `backend=hstore` (verified in the container's
`conf/graphs/hugegraph.properties`).

Config deltas from the upstream compose: single store (upstream file is
also single-store), heaps `-Xmx1g` (pd) / `-Xmx4g` (store) / `-Xmx4g`
(server) — three JVMs share the 15G host, every process stays under the
8G cap; `HG_PD_AUTH_SECRET_KEY=hgbench-secret`; no admin password.

The runner is the same HugeGraph adapter as the single node
([runner/hg.py](runner/hg.py)) pointed at port 18081; identical REST and
gremlin endpoints, wipe = clear API + schema recreate.

Stop with `docker compose -f bench/runner/hstore-compose.yml stop`.
