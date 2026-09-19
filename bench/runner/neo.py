"""Neo4j adapter (official python driver, bolt). Wipe = container restart
with a fresh data dir, since DETACH DELETE over tens of millions of
elements is far slower and less deterministic."""

import subprocess
import time

import neo4j

import common

CONTAINER = "hg-bench-neo4j"
DATA_DIR = "/home/library/hg-bench/state/neo4j"
AUTH = ("neo4j", "benchpass1")
URI = "bolt://localhost:17687"


class Neo:
    def __init__(self, image):
        self.image = image
        self.driver = None
        self._ensure_up()

    def _connect(self):
        if self.driver:
            self.driver.close()
        self.driver = neo4j.GraphDatabase.driver(URI, auth=AUTH)
        for _ in range(120):
            try:
                self.driver.verify_connectivity()
                return
            except Exception:
                time.sleep(2)
        raise RuntimeError("neo4j did not come up")

    def _ensure_up(self):
        r = subprocess.run(["docker", "ps", "-q", "-f", f"name={CONTAINER}"],
                           capture_output=True, text=True)
        if not r.stdout.strip():
            self._start_fresh()
        else:
            self._connect()

    def _start_fresh(self):
        subprocess.run(["docker", "rm", "-f", CONTAINER],
                       capture_output=True)
        subprocess.run(["rm", "-rf", DATA_DIR])
        subprocess.run(["mkdir", "-p", DATA_DIR], check=True)
        subprocess.run([
            "docker", "run", "-d", "--name", CONTAINER,
            "-p", "17687:7687", "-p", "17474:7474",
            "-v", f"{DATA_DIR}:/data",
            "-e", f"NEO4J_AUTH={AUTH[0]}/{AUTH[1]}",
            "-e", "NEO4J_server_memory_heap_initial__size=2g",
            "-e", "NEO4J_server_memory_heap_max__size=8g",
            "-e", "NEO4J_server_memory_pagecache_size=2g",
            self.image], check=True, capture_output=True)
        self._connect()
        self.schema()

    def wipe(self):
        self._start_fresh()

    def schema(self):
        with self.driver.session() as s:
            s.run("CREATE CONSTRAINT node_nid IF NOT EXISTS "
                  "FOR (n:node) REQUIRE n.nid IS UNIQUE").consume()

    def _run(self, q, **params):
        with self.driver.session() as s:
            return s.run(q, **params).consume()

    def insert_vertices_batch(self, ids):
        self._run("UNWIND $ids AS i CREATE (:node {nid: i})", ids=list(ids))

    def insert_edges_batch(self, pairs):
        self._run("UNWIND $ps AS p "
                  "MATCH (a:node {nid: p[0]}), (b:node {nid: p[1]}) "
                  "CREATE (a)-[:link]->(b)", ps=[list(p) for p in pairs])

    def insert_vertex(self, i):
        self._run("CREATE (:node {nid: $i})", i=i)

    def insert_edge(self, a, b):
        self._run("MATCH (a:node {nid: $a}), (b:node {nid: $b}) "
                  "CREATE (a)-[:link]->(b)", a=a, b=b)

    def fn_batch(self, ids):
        with self.driver.session() as s:
            rec = s.run("UNWIND $ids AS i MATCH (v:node {nid: i})--(m) "
                        "RETURN count(m) AS c", ids=list(ids)).single()
            return int(rec["c"])

    def fa_scan(self, cap):
        n = 0
        with self.driver.session() as s:
            res = s.run("MATCH (a:node)-[:link]->(b:node) "
                        "RETURN a.nid AS s, b.nid AS t")
            for rec in res:
                _ = rec["s"], rec["t"]
                n += 1
                if cap and n >= cap:
                    break
        return n

    def fs(self, src, dst):
        q = neo4j.Query(
            "MATCH (a:node {nid: $s}), (b:node {nid: $t}) "
            f"MATCH p = shortestPath((a)-[*..{common.FS_MAX_DEPTH}]-(b)) "
            "RETURN length(p) AS l", timeout=common.FS_TIMEOUT)
        try:
            with self.driver.session() as s:
                rec = s.run(q, s=src, t=dst).single()
                return int(rec["l"]) if rec else None
        except Exception:
            return None

    def edge_pairs(self, cap):
        n = 0
        with self.driver.session() as s:
            res = s.run("MATCH (a:node)-[:link]->(b:node) "
                        "RETURN a.nid AS s, b.nid AS t")
            for rec in res:
                yield rec["s"], rec["t"]
                n += 1
                if cap and n >= cap:
                    return

    def close(self):
        if self.driver:
            self.driver.close()


if __name__ == "__main__":
    import sys
    digest = sys.argv[1]
    datasets = sys.argv[2].split(",") if len(sys.argv) > 2 else \
        ["enron", "amazon", "youtube", "lj"]
    tests = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else \
        ("siw", "miw", "fn", "fa", "fs", "cw")
    image = sys.argv[4] if len(sys.argv) > 4 else "neo4j:5.26.30-community"
    n = Neo(image)
    for d in datasets:
        common.run_dataset(n, "neo4j", digest, d, tests)
    n.close()
