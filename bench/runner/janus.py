"""JanusGraph adapter (gremlinpython over websocket, groovy scripts with
bindings). Backend: BerkeleyJE (in-process, the single-node analogue of
the RocksDB choice for HugeGraph). Wipe = container restart with a fresh
data dir.

Vertex-id cache: during vertex insertion the server returns JanusGraph
vertex ids, which the client caches (nid -> vid) and uses for edge
inserts, FN and FS. This mirrors socialsensor's cache and avoids
index lookups skewing insert times; no nid index is created."""

import subprocess
import time

from gremlin_python.driver.client import Client

import common

CONTAINER = "hg-bench-janus"
DATA_DIR = "/home/library/hg-bench/state/janus"
URL = "ws://localhost:18182/gremlin"


class Janus:
    def __init__(self, image):
        self.image = image
        self.client = None
        self.vid = {}
        self._ensure_up()

    def _connect(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        deadline = time.time() + 300
        last = None
        while time.time() < deadline:
            try:
                self.client = Client(URL, "g")
                self.client.submit("g.V().limit(1).count()").all().result()
                return
            except Exception as e:
                last = e
                time.sleep(3)
        raise RuntimeError(f"janusgraph did not come up: {last}")

    def _ensure_up(self):
        r = subprocess.run(["docker", "ps", "-q", "-f", f"name={CONTAINER}"],
                           capture_output=True, text=True)
        if not r.stdout.strip():
            self._start_fresh()
        else:
            self._connect()

    def _start_fresh(self):
        subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
        # data dir files are owned by the container user: clear as root
        # inside a throwaway container, never on the host
        subprocess.run(["docker", "run", "--rm", "-u", "0",
                        "--entrypoint", "sh",
                        "-v", f"{DATA_DIR}:/wipe", self.image,
                        "-c", "rm -rf /wipe/* /wipe/.[!.]* 2>/dev/null; true"],
                       check=True, capture_output=True)
        subprocess.run(["mkdir", "-p", DATA_DIR], check=True)
        subprocess.run(["chmod", "777", DATA_DIR], check=True)
        subprocess.run([
            "docker", "run", "-d", "--name", CONTAINER,
            "-p", "18182:8182",
            "-v", f"{DATA_DIR}:/var/lib/janusgraph",
            "-e", "JANUS_PROPS_TEMPLATE=berkeleyje",
            # a crashed client would otherwise leave a stale instance-id
            # registration that blocks the next startup
            "-e", "janusgraph.graph.replace-instance-if-exists=true",
            "-e", "JAVA_OPTIONS=-Xms2g -Xmx8g",
            self.image], check=True, capture_output=True)
        self._connect()
        self.vid = {}
        self.schema()

    def wipe(self):
        self._start_fresh()

    def schema(self):
        self.client.submit(
            "mgmt = graph.openManagement();"
            "if (mgmt.getPropertyKey('nid') == null) {"
            "  mgmt.makePropertyKey('nid').dataType(Long.class).make();"
            "  mgmt.makeVertexLabel('node').make();"
            "  mgmt.makeEdgeLabel('link').make();"
            "  mgmt.commit()"
            "} else { mgmt.rollback() }").all().result()

    def _submit(self, script, bindings=None, timeout_ms=None):
        opts = {"evaluationTimeout": timeout_ms} if timeout_ms else None
        if bindings:
            return self.client.submit(script, bindings,
                                      request_options=opts).all().result()
        return self.client.submit(script,
                                  request_options=opts).all().result()

    # -- inserts --

    def insert_vertices_batch(self, ids):
        vids = self._submit(
            "ids.collect { g.addV('node').property('nid', it).id().next() }",
            {"ids": list(ids)})
        for n, v in zip(ids, vids):
            self.vid[n] = v

    def insert_edges_batch(self, pairs):
        vp = [[self.vid[a], self.vid[b]] for a, b in pairs]
        self._submit(
            "vp.each { g.V(it[0]).addE('link').to(__.V(it[1])).iterate() };"
            "vp.size()", {"vp": vp})

    def insert_vertex(self, i):
        vids = self._submit("[g.addV('node').property('nid', n).id().next()]",
                            {"n": i})
        self.vid[i] = vids[0]

    def insert_edge(self, a, b):
        self._submit("g.V(s).addE('link').to(__.V(t)).iterate(); 1",
                     {"s": self.vid[a], "t": self.vid[b]})

    # -- queries --

    def fn_batch(self, ids):
        vids = [self.vid[i] for i in ids]
        r = self._submit("g.V(vids).both().count()", {"vids": vids})
        return int(r[0])

    # g.E() would return Edge objects whose RelationIdentifier id is a
    # custom graphbinary type the python driver cannot decode; project
    # the endpoint ids to plain longs instead.
    _EDGE_SCAN = "g.E().project('o','i').by(outV().id()).by(inV().id())"

    def _resolve_vids(self, nids):
        """One full-scan lookup for nids missing from the cache (used only
        when resuming query tests in a fresh process against an already
        loaded graph; there is no nid index, so this is a single scan)."""
        missing = [n for n in nids if n not in self.vid]
        if not missing:
            return
        rows = self._submit(
            "g.V().has('nid', within(ns))"
            ".project('n','v').by(values('nid')).by(id())",
            {"ns": missing}, timeout_ms=common.TIME_CAP_S * 1000)
        for m in rows:
            self.vid[m["n"]] = m["v"]

    def prepare_fs(self, pairs):
        nids = set()
        for s, t in pairs:
            nids.add(s)
            nids.add(t)
        self._resolve_vids(sorted(nids))

    def fa_scan(self, cap):
        n = 0
        rs = self.client.submit(
            self._EDGE_SCAN,
            request_options={"evaluationTimeout": common.TIME_CAP_S * 1000})
        for batch in rs:
            for e in batch:
                _ = e["o"], e["i"]
                n += 1
            if cap and n >= cap:
                rs.close()
                break
        return n

    def fs(self, src, dst):
        s, t = self.vid[src], self.vid[dst]
        try:
            # dedup() inside the repeat keeps this a breadth-first walk
            # over distinct vertices. The simplePath() form it replaces
            # enumerated every simple path to depth 6 whenever a target
            # was unreachable, which exhausted the heap and turned real
            # paths into false negatives -- see notes/janusgraph-fs.md.
            r = self._submit(
                "g.V(s).repeat(both().dedup()).until(hasId(t).or()"
                f".loops().is({common.FS_MAX_DEPTH})).hasId(t)"
                ".limit(1).path().count(local)",
                {"s": s, "t": t}, timeout_ms=common.FS_TIMEOUT * 1000)
            return int(r[0]) - 1 if r else None
        except Exception:
            return None

    def edge_pairs(self, cap):
        n = 0
        rs = self.client.submit(
            self._EDGE_SCAN,
            request_options={"evaluationTimeout": common.TIME_CAP_S * 1000})
        for batch in rs:
            for e in batch:
                yield e["o"], e["i"]
                n += 1
                if cap and n >= cap:
                    rs.close()
                    return

    def close(self):
        if self.client:
            self.client.close()


if __name__ == "__main__":
    import sys
    digest = sys.argv[1]
    datasets = sys.argv[2].split(",") if len(sys.argv) > 2 else \
        ["enron", "amazon", "youtube", "lj"]
    tests = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else \
        ("siw", "miw", "fn", "fa", "fs", "cw")
    image = sys.argv[4] if len(sys.argv) > 4 else "janusgraph/janusgraph:latest"
    j = Janus(image)
    for d in datasets:
        common.run_dataset(j, "janusgraph", digest, d, tests)
    j.close()
