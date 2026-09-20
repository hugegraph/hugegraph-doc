# Setup: janusgraph

JanusGraph 1.1.0 (current release), BerkeleyJE backend -- the in-process
single-node store, chosen as the closest analogue to the RocksDB backend
used for hugegraph-single. Backend recorded here as the contract asks.

- Image: `janusgraph/janusgraph:latest`, digest
  `sha256:75f57aff4b152ca86b4cdaeefb5335154d7fad412cffef75fa44c7504adc96d4`
  (JanusGraph 1.1.0, TinkerPop/Gremlin 3.7.3, BerkeleyJE 18.3.12)
- Invocation (from [runner/janus.py](runner/janus.py), which manages the
  container):

```
docker run -d --name hg-bench-janus -p 18182:8182 \
  -v /home/library/hg-bench/state/janus:/var/lib/janusgraph \
  -e JANUS_PROPS_TEMPLATE=berkeleyje \
  -e janusgraph.graph.replace-instance-if-exists=true \
  -e JAVA_OPTIONS="-Xms2g -Xmx8g" \
  janusgraph/janusgraph:latest
```

Config deltas from image default: BerkeleyJE template, heap 2g/8g (the
8G cap), and `replace-instance-if-exists` so a client that dies mid-query
cannot leave a stale instance-id registration blocking the next startup.

Schema per fresh instance, via the management API: property key `nid`
(Long), vertex label `node`, edge label `link`. No index on `nid` -- the
runner caches the JanusGraph vertex ids returned at insert time and uses
them for edge inserts, FN and FS, mirroring socialsensor's vertex cache
and keeping index maintenance out of the insert measurements.

Wipe between loader runs = remove the container and clear its data dir
(as root in a throwaway container, since the files are owned by the
container user), then start fresh. Restart cost is not part of any
measured run.

Client: gremlinpython 3.7.3 over websocket. Version-matched to the
server deliberately -- gremlinpython 3.8.x speaks the TinkerPop 3.8 HTTP
protocol and cannot talk to this 3.7.3 server (it fails deserializing
GraphBinary).

Operations:

- MIW/SIW: `g.addV('node').property('nid', ...)` per batch of 500, then
  `g.V(src).addE('link').to(__.V(dst))` per batch of 500
- FN: `g.V(vids).both().count()` per batch of 500
- FA/CW read: `g.E().project('o','i').by(outV().id()).by(inV().id())` --
  projected to plain ids because a raw `g.E()` returns edge objects whose
  RelationIdentifier id is a custom GraphBinary type the python driver
  cannot decode
- FS: breadth-first `repeat(both().dedup())` to depth 6, 60s per query.
  JanusGraph has no native shortest-path step in OLTP; the first
  formulation used `simplePath()` and had to be replaced. See
  [notes/janusgraph-fs.md](notes/janusgraph-fs.md).

All write and per-batch read operations carry an explicit 900s
evaluationTimeout. Without it they inherit the server's 30s default,
which a 500-edge batch exceeds once the graph holds tens of millions of
edges -- that aborted the first lj load mid-MIW.
