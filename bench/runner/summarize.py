"""Print median wall times per system/dataset/test from results/*.json.
Medians are over measured runs (w excluded). Used to fill notes/summary.md."""

import glob
import json
import os
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "results")

DS_ORDER = ["enron", "amazon", "youtube", "lj"]
TEST_ORDER = ["miw", "siw", "fn", "fa", "fs", "cw"]


def main():
    runs = defaultdict(list)
    meta = {}
    for p in sorted(glob.glob(os.path.join(RESULTS, "*.json"))):
        d = json.load(open(p))
        if d["run"] == "w":
            continue
        key = (d["system"], d["dataset"], d["test"])
        runs[key].append(d["wall_seconds"])
        meta[key] = (d["image"], len(runs[key]))
    systems = sorted({k[0] for k in runs})
    for sy in systems:
        print(f"\n## {sy}")
        print("| dataset | " + " | ".join(TEST_ORDER) + " |")
        print("|---" * (len(TEST_ORDER) + 1) + "|")
        for ds in DS_ORDER:
            row = [ds]
            for t in TEST_ORDER:
                v = runs.get((sy, ds, t))
                if v:
                    m = statistics.median(v)
                    row.append(f"{m:.3f}" + (f" ({len(v)}r)" if len(v) != 3 else ""))
                else:
                    row.append("-")
            print("| " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
