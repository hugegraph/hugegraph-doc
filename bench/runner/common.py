"""Shared workload logic for the graphdb benchmark rerun.

One thin adapter per system implements:
    wipe()                       -- empty graph, schema recreated
    insert_vertices_batch(ids)   -- batch of BATCH vertex ids
    insert_edges_batch(pairs)    -- batch of BATCH (src, dst) pairs
    insert_vertex(i)             -- single vertex insert
    insert_edge(u, v)            -- single edge insert
    fn_batch(ids) -> int         -- neighbor count for a batch of vertex ids
    fa_scan(cap) -> int          -- scan up to cap edges, return count seen
    fs(src, dst) -> path len or None (per-query timeout FS_TIMEOUT)
    edge_pairs(cap) -> iterator of (src, dst) for the CW graph read
    close()

The orchestrator runs, per dataset: SIW, MIW, FN, FA, FS, CW.
Each test: 1 warmup pass + 3 measured runs (median reported downstream).
Adaptive rule: if the warmup or first measured run exceeds LONG_RUN_S,
only 1 measured run is taken for that test and the deviation is noted.
"""

import json
import os
import random
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
RESULTS = os.path.join(BENCH, "results")
RUNLOG = os.path.join(BENCH, "run-log.md")
DATA = os.path.expanduser("~/hg-bench/datasets")

BATCH = 500          # batch size for MIW / FN, page size for FA scans
SIW_EDGES = 10_000   # bounded single-insert workload, identical per system
FS_TARGETS = 100     # shortest-path target count
FS_MAX_DEPTH = 6
FS_TIMEOUT = 60      # seconds per shortest-path query
LONG_RUN_S = 2700    # 45 min: adaptive cutoff, see notes/method.md
SEED = 42

DATASETS = {
    "enron":   {"file": "email-Enron.txt",        "fa_cap": None},
    "amazon":  {"file": "amazon0601.txt",         "fa_cap": None},
    "youtube": {"file": "com-youtube.ungraph.txt", "fa_cap": None},
    "lj":      {"file": "com-lj.ungraph.txt",     "fa_cap": 5_000_000},
}


class Dataset:
    def __init__(self, name):
        self.name = name
        self.path = os.path.join(DATA, DATASETS[name]["file"])
        self.fa_cap = DATASETS[name]["fa_cap"]
        self._vertices = None
        self._first = None

    def edges(self):
        """Yield (src, dst) int pairs in file order."""
        with open(self.path) as f:
            for line in f:
                if line.startswith("#"):
                    continue
                a, b = line.split()
                yield int(a), int(b)

    @property
    def vertices(self):
        """Sorted list of all vertex ids."""
        if self._vertices is None:
            s = set()
            for a, b in self.edges():
                if self._first is None:
                    self._first = a
                s.add(a)
                s.add(b)
            self._vertices = sorted(s)
        return self._vertices

    @property
    def first_vertex(self):
        self.vertices
        return self._first

    def fs_pairs(self):
        """(source, target) pairs: first vertex to 100 seeded-random targets."""
        rng = random.Random(SEED)
        targets = rng.sample(self.vertices, FS_TARGETS)
        return [(self.first_vertex, t) for t in targets]


def batched(it, n):
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf


# ---- workloads: each returns (ops_count, extra_dict) ----

def miw(adapter, ds):
    nv = ne = 0
    for chunk in batched(iter(ds.vertices), BATCH):
        adapter.insert_vertices_batch(chunk)
        nv += len(chunk)
    for chunk in batched(ds.edges(), BATCH):
        adapter.insert_edges_batch(chunk)
        ne += len(chunk)
    return nv + ne, {"vertices": nv, "edges": ne}


def siw(adapter, ds):
    seen = set()
    ne = nv = 0
    for a, b in ds.edges():
        for v in (a, b):
            if v not in seen:
                adapter.insert_vertex(v)
                seen.add(v)
                nv += 1
        adapter.insert_edge(a, b)
        ne += 1
        if ne >= SIW_EDGES:
            break
    return nv + ne, {"vertices": nv, "edges": ne}


def fn(adapter, ds):
    total = 0
    nv = 0
    for chunk in batched(iter(ds.vertices), BATCH):
        total += adapter.fn_batch(chunk)
        nv += len(chunk)
    return nv, {"vertices_traversed": nv, "neighbors_seen": total}


def fa(adapter, ds):
    n = adapter.fa_scan(ds.fa_cap)
    return n, {"edges_scanned": n, "cap": ds.fa_cap}


def fs(adapter, ds):
    found = timeout = 0
    for s, t in ds.fs_pairs():
        r = adapter.fs(s, t)
        if r is None:
            timeout += 1
        else:
            found += 1
    return FS_TARGETS, {"found": found, "timeout_or_unreached": timeout}


def cw(adapter, ds):
    import igraph
    import numpy as np
    pairs = np.fromiter(
        (x for e in adapter.edge_pairs(None) for x in e), dtype=np.int64
    ).reshape(-1, 2)
    ids = np.unique(pairs)
    idx = {int(v): i for i, v in enumerate(ids)}
    el = [(idx[int(a)], idx[int(b)]) for a, b in pairs]
    g = igraph.Graph(n=len(ids), edges=el, directed=False)
    comm = g.community_multilevel()
    return len(el), {
        "edges_read": len(el),
        "communities": len(comm),
        "modularity": round(comm.modularity, 4),
    }


TESTS = {"siw": siw, "miw": miw, "fn": fn, "fa": fa, "fs": fs, "cw": cw}
# tests that require an empty graph and leave it loaded (miw) or dirty (siw)
LOADERS = {"siw", "miw"}


def record(system, digest, dataset, test, run, wall, ops, extra):
    row = {
        "system": system,
        "image": digest,
        "dataset": dataset,
        "test": test,
        "run": run,
        "wall_seconds": round(wall, 3),
        "ops": ops,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "params": {"batch": BATCH, "siw_edges": SIW_EDGES,
                   "fs_targets": FS_TARGETS, "fs_max_depth": FS_MAX_DEPTH,
                   "fs_timeout_s": FS_TIMEOUT, "seed": SEED},
        "detail": extra,
    }
    name = f"{system}-{dataset}-{test}-{run}.json"
    with open(os.path.join(RESULTS, name), "w") as f:
        json.dump(row, f, indent=1)
    with open(RUNLOG, "a") as f:
        f.write(f"| {time.strftime('%Y-%m-%d %H:%M')} | {system} | {dataset} "
                f"| {test} | {run} | {row['wall_seconds']} |\n")
    print(f"[{time.strftime('%H:%M:%S')}] {system} {dataset} {test} "
          f"run={run} wall={wall:.3f}s ops={ops}", flush=True)


def run_dataset(adapter, system, digest, dsname,
                tests=("siw", "miw", "fn", "fa", "fs", "cw")):
    ds = Dataset(dsname)
    ds.vertices  # parse once up front, outside any timing
    for test in tests:
        fun = TESTS[test]
        long_hit = False
        for r in ("w", "1", "2", "3"):
            if long_hit and r in ("2", "3"):
                print(f"  adaptive: {test}/{dsname} run exceeded {LONG_RUN_S}s,"
                      f" stopping after run 1", flush=True)
                break
            if test in LOADERS:
                adapter.wipe()
            t0 = time.monotonic()
            ops, extra = fun(adapter, ds)
            wall = time.monotonic() - t0
            record(system, digest, dsname, test, r, wall, ops, extra)
            if wall > LONG_RUN_S:
                long_hit = True
        # after siw the graph holds partial data; miw wipes first anyway
    # leave graph loaded (last miw run data is used by fn/fa/fs/cw)
