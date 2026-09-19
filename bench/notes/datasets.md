# Datasets: not local, downloaded

Deviation from the goal prompt: no SNAP dataset files existed anywhere on
the host (searched /home, /media, /mnt, whole root). Downloaded
2026-09-19 from snap.stanford.edu into `~/hg-bench/datasets/`:

| File | URL path | sha256 (of .gz) |
|---|---|---|
| email-Enron.txt.gz | data/email-Enron.txt.gz | 55cfead79b1f0161786179a48796c2a119bd7026a246238b257b6be9d8b69b68 |
| amazon0601.txt.gz | data/amazon0601.txt.gz | aa6dea3bac74bf8e396f23a42a44eb1a913f9837cb388a688a70b2cae8944a7b |
| com-youtube.ungraph.txt.gz | data/bigdata/communities/com-youtube.ungraph.txt.gz | dff1b97ba7d2fa9c59884b67dcd2275e717ff9501f86ed82ce6582ed4971f3e0 |
| com-lj.ungraph.txt.gz | data/bigdata/communities/com-lj.ungraph.txt.gz | e0e8996341b963ecbe0a572c71446c03fd6e93a6c521578eaae7566c68ff608e |

The com-youtube and com-lj files live under `bigdata/communities/` on the
SNAP server, not `data/` directly.

Amazon is `amazon0601` (as in the 0.5.6 reference doc), not `com-amazon`.
Header counts match the reference doc exactly: enron 36,692 v / 367,662 e;
amazon 403,394 v / 3,387,388 e; youtube 1,134,890 v / 2,987,624 e;
lj 3,997,962 v / 34,681,189 e. (The old doc's table rounds some of these.)

The 0.5.6 doc ran CW on synthetic LFR graphs (1k-20k vertices); this
rerun's scope is the four SNAP datasets for every test, so CW runs on
these instead. See [method.md](method.md).
