# Isolated search index evaluation

Base site source: `38a97a7bbc2b7066292b1e2c093bb25b0689c496`.
This branch adds only experiment files. Production and PR configuration remain unchanged.
The workflow builds summary/content variants from identical source, changes only the temporary workspace search-index parameter, then restores it.

Both variants run the existing bilingual search-ranking contract with retries disabled.
A Chromium runner measures raw/gzip index bytes, record counts, Node JSON parse cost,
all existing query ranks, body-only technical queries present in real content, and five first-search samples per language.
Each first-search sample creates a fresh browser context on the same runner and uses local matching artifacts.
The timing includes opening the palette, typing and waiting for a result. No network/CPU throttling is applied.
These samples compare this experiment on this runner; they are not production latency or an independent benchmark.

Results are logged as compact JSON between SEARCH_EVALUATION markers and uploaded with complete ranking reports.
No site setting is enabled by this experiment.
