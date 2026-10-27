# OINK 1.4.0 browser evidence

Captured by [GitHub Actions run 40550402749](https://github.com/hugegraph/hugegraph-doc/actions/runs/40550402749)
with Playwright 1.62.1, Chromium, Node 24.21.0 and a 1440 × 900 viewport.

- Baseline: `efa1d042316e3f18caef4a642a685f38d2ec596f`, OINK 1.3.1 with its matching Dart Sass 1.105.2 toolchain.
- Target runtime: `e447cbb5d2cfd8967e247b00ea693d5d6c372976`, OINK 1.4.0 with Hugo Extended 0.168.0 and built-in LibSass.
- Both artifacts were built separately. Production-origin requests were routed to the corresponding local artifact, following `tests/e2e/artifact-test.js`.
- Stylesheet loading and integrity were retained. The table reader was opened through its native hover/click control.
- The code PR is [#54](https://github.com/hugegraph/hugegraph-doc/pull/54).
