"""HugeGraph adapter (REST + gremlin-over-HTTP). Used for both the
single-node and the PD/Store/Server cluster deployments; only the base
URL and graph name differ."""

import json

import requests

import common


class HG:
    def __init__(self, base="http://localhost:18080",
                 graphspace="DEFAULT", graph="hugegraph"):
        self.base = base
        self.g = f"{base}/graphspaces/{graphspace}/graphs/{graph}"
        self.gremlin_url = f"{base}/gremlin"
        self.alias = f"__g_{graphspace}-{graph}"
        self.s = requests.Session()

    def _post(self, url, payload, timeout=300):
        r = self.s.post(url, json=payload, timeout=timeout)
        if r.status_code >= 300:
            raise RuntimeError(f"POST {url} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.text else None

    def gremlin(self, script, timeout=300):
        r = self.s.post(self.gremlin_url,
                        json={"gremlin": script, "aliases": {"g": self.alias}},
                        timeout=timeout)
        if r.status_code >= 300:
            raise RuntimeError(f"gremlin -> {r.status_code}: {r.text[:300]}")
        return r.json()["result"]["data"]

    # -- lifecycle --

    def wipe(self):
        r = self.s.delete(
            f"{self.g}/clear",
            params={"confirm_message": "I'm sure to delete all data"},
            timeout=600)
        if r.status_code not in (200, 202, 204):
            raise RuntimeError(f"clear -> {r.status_code}: {r.text[:300]}")
        self.schema()

    def schema(self):
        self._post(f"{self.g}/schema/vertexlabels", {
            "name": "node", "id_strategy": "CUSTOMIZE_NUMBER",
            "properties": [], "primary_keys": [], "nullable_keys": [],
            "enable_label_index": False})
        self._post(f"{self.g}/schema/edgelabels", {
            "name": "link", "source_label": "node", "target_label": "node",
            "frequency": "SINGLE", "properties": [], "sort_keys": [],
            "nullable_keys": [], "enable_label_index": False})

    # -- inserts --

    def insert_vertices_batch(self, ids):
        self._post(f"{self.g}/graph/vertices/batch",
                   [{"label": "node", "id": i, "properties": {}} for i in ids])

    def insert_edges_batch(self, pairs):
        self._post(f"{self.g}/graph/edges/batch",
                   [{"label": "link", "outV": a, "inV": b,
                     "outVLabel": "node", "inVLabel": "node", "properties": {}}
                    for a, b in pairs])

    def insert_vertex(self, i):
        self._post(f"{self.g}/graph/vertices",
                   {"label": "node", "id": i, "properties": {}})

    def insert_edge(self, a, b):
        self._post(f"{self.g}/graph/edges",
                   {"label": "link", "outV": a, "inV": b,
                    "outVLabel": "node", "inVLabel": "node", "properties": {}})

    # -- queries --

    def fn_batch(self, ids):
        data = self.gremlin(f"g.V({json.dumps(ids)}).both().count()")
        return int(data[0])

    def fa_scan(self, cap):
        n = 0
        page = ""
        while True:
            r = self.s.get(f"{self.g}/graph/edges",
                           params={"limit": common.BATCH, "page": page},
                           timeout=300)
            r.raise_for_status()
            d = r.json()
            for e in d["edges"]:
                # touch both endpoints, as FA is defined
                _ = e["outV"], e["inV"]
                n += 1
            page = d.get("page")
            if not page or (cap and n >= cap):
                return n

    def fs(self, src, dst):
        try:
            r = self.s.get(
                f"{self.g}/traversers/shortestpath",
                params={"source": src, "target": dst,
                        "max_depth": common.FS_MAX_DEPTH, "direction": "BOTH"},
                timeout=common.FS_TIMEOUT)
        except requests.exceptions.Timeout:
            return None
        if r.status_code >= 300:
            return None
        p = r.json().get("path", [])
        return len(p) - 1 if p else None

    def edge_pairs(self, cap):
        n = 0
        page = ""
        while True:
            r = self.s.get(f"{self.g}/graph/edges",
                           params={"limit": common.BATCH, "page": page},
                           timeout=300)
            r.raise_for_status()
            d = r.json()
            for e in d["edges"]:
                yield e["outV"], e["inV"]
                n += 1
            page = d.get("page")
            if not page or (cap and n >= cap):
                return

    def close(self):
        self.s.close()


if __name__ == "__main__":
    import sys
    system = sys.argv[1] if len(sys.argv) > 1 else "hugegraph-single"
    digest = sys.argv[2]
    datasets = sys.argv[3].split(",") if len(sys.argv) > 3 else \
        ["enron", "amazon", "youtube", "lj"]
    tests = tuple(sys.argv[4].split(",")) if len(sys.argv) > 4 else \
        ("siw", "miw", "fn", "fa", "fs", "cw")
    base = sys.argv[5] if len(sys.argv) > 5 else "http://localhost:18080"
    hg = HG(base=base)
    for d in datasets:
        common.run_dataset(hg, system, digest, d, tests)
    hg.close()
