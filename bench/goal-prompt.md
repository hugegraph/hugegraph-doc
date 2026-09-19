/goal Rerun the HugeGraph benchmark on current software. Record raw results on this branch. No PR, no docs page.

Branch: bench/perf-1.8 on hugegraph/hugegraph-doc. Everything lives under bench/.

Systems, one at a time on one host:

- HugeGraph :latest, single-node RocksDB
- HugeGraph :latest, distributed 1 PD + 1 Store + 1 Server (hstore)
- Neo4j, current LTS
- JanusGraph, current release (pick one backend, record which)

Tests, same shapes as docs/performance/hugegraph-benchmark-0.5.6:

- MIW massive insert, SIW single insert
- QW: find neighbors, find adjacent nodes, shortest path to 100 random targets
- CW: Louvain clustering
- Datasets: SNAP Enron, Amazon, Youtube, LiveJournal (com-lj)

Harness: try socialsensor/graphdb-benchmark first. It predates every current client, so expect to reimplement the same operations with current drivers instead. If reimplementing: one thin runner per system, identical operation counts and datasets, warmup pass then 3 measured runs, report the median.

Host: library (12 threads i5-11400H, 15G RAM, about 13G available, 107G free disk, Docker 29.5.3, Java 17). The wearwise stack and the f1 kind cluster are stopped for this work. Rules:

- One system under test at a time. Heap cap 8G. Stop its containers before starting the next.
- The stopped wearwise-* and f1-* containers, their volumes and their images stay exactly as they are: never start, remove or prune them, never `docker compose down` the wearwise-live project, never `kind delete` f1, never `docker volume prune` or `docker system prune`.
- Work under ~/hg-bench on library. Remove only the benchmark's own images, containers and volumes at the end. Leave wearwise and f1 stopped; the owner restarts them.

Record in bench/ on this branch:

- env.md: hardware, OS, kernel, JVM, docker, each system version, every config delta from default, exact invocation lines
- run-log.md: date, system, dataset, wall time per test, anomalies
- results/: raw output per run, csv or json, named <system>-<dataset>-<test>-<n>
- handoff.md: current state and next step, updated at every stop

Git: commits via git commit-tree as Himanshu Verma, no AI references anywhere, push only this branch, never force-push. No PR until told.

Blocked means: a dataset refuses to load into a system after 3 attempts, or disk runs out. Record it in handoff.md and move on.

Done when all four systems have results for all datasets and tests, or every gap is recorded in handoff.md.
