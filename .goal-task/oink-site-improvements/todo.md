# OINK Site Improvements — Work Items

Item-level status, dependencies, waits, and deferrals live here. Update this
file after each productive loop; keep only counts and dependency summaries in
`state.md`.

## Gate 1 — PR-A: OINK core platform

- [x] Fix destructive output-path validation so canonical repository roots,
  ancestors, and checkout descendants are rejected; focused regression passed
  in checkpoint `f1bffd0827d217ad17eecf5ba00ace793ecf3ff3` and integration commit
  `4753dedb7`.
- [x] Refresh `origin/master`, create the direct Apache PR-A branch/worktree,
  and inventory current OINK extension seams, ownership boundaries, and tests.
- [x] Implement shared OINK theme tokens, five-group Documentation navigation,
  single version selector, delayed pointer behavior, keyboard behavior, and
  explicit sidebar collapse/restore.
- [x] Implement stable per-version/per-locale sidebar persistence, active-path
  priority, stale-ID cleanup, localStorage fallback, mobile drawer isolation,
  focus restoration, scroll unlock, and hamburger contrast.
- [x] Preserve summary search; add distinct no-results/load-failure states and
  retry.
- [ ] Implement the click-loaded Kapa adapter and shared state machine with the
  exact configuration, privacy, failure, timeout, late-response, focus, theme,
  CSP, and disabled-mode contracts. Source/mock contracts are green; staging
  source groups and exact observed CSP hosts remain.
- [x] EN/CN latest LLMSFULL outputs are implemented on PR-A and validated as
  separate locale-specific files; real Kapa ingestion remains an external gate.
- [x] Add 1.3 and 1.0, finish making `versions.json` the sole source including
  the static Hugo menu, implement immutable
  ref resolution, route-map/aliases, logical-page switching, SEO/archive rules,
  and genuine language fallbacks. Core build/validate is green.
- [x] Implement Backlinks, image zoom, Blog copy-link, reviewed social fallback
  image, and the scoped non-content OINK capabilities assigned to PR-A.
- [x] Replace the Cartesian CI matrix with the confirmed event model,
  permissions, artifact lifetimes, timeouts, aggregate/E2E/deploy gates, and
  fixed publish targets.
- [x] Add the Node 24, lockfile, Playwright, and Chromium test workspace under
  `tests/e2e/` without making Hugo production builds run npm.
- [x] Run targeted checks, full PR-A validation, browser acceptance, three
  independent reviews, fixes, and re-review; then commit, push, and open PR-A.
  Exact clean pushed head `25f3e8c` includes the rendered-request security and
  authored-content boundary checkpoints. Its final matrix passes links, Python
  124/124, UI/AI 23/23,
  workflow 6/6, production/staging-full five versions, staging-latest,
  route-byte equality, Chromium 32 with three expected PR-B-only skips, and
  visual 8/8. [PR #472](https://github.com/apache/hugegraph-doc/pull/472) is
  ready for review at the exact head.
- [ ] Resume by checking CI run 33934549197 and required human review; merge
  PR-A only when both are green, without override.

## Gate 2 — PR-B: Community and content experience

- [x] Refresh `origin/master`, create the direct Apache PR-B branch/worktree,
  and confirm it does not modify PR-A-owned shared config, shell styles,
  lockfiles, or workflow files.
- [x] Implement ASF roster refresh and offline validation with authoritative
  owners/members/Chair/name rules, deterministic ordering, schema, staleness,
  last-good atomic replacement, and orphan cleanup.
- [x] Populate any GitHub mappings only after login and numeric user ID receive
  explicit human review; the current empty mapping intentionally avoids
  inference and renders all 22 members through the required fallback. The user
  explicitly confirmed this mapping must remain empty for this delivery.
- [x] Implement the bilingual Project members section, site-local partial,
  same-origin 128×128 WebP assets, no-JS initials fallback, accessible profile
  links, 5/3/2 responsive grid, and HTML/Print/Markdown parity.
- [x] Add restrained search metadata for the 12 fixed EN/CN latest entry
  groups; the integrated real Lunr/Playwright gate ranks all 24 fixed queries
  in the Top 3.
- [x] Apply OINK native content components only to the three confirmed latest
  bilingual page groups.
- [x] Complete integrated browser matrices and exactly three independent
  reviews with required fix/re-review. Final PR-B head `bb27083` is pushed to
  `origin/feat/oink-community-content`; the exact integrated matrix and final
  3/3 review are green.
- [ ] After resume, create PR-B with `Closes #468`, then wait for CI/review and
  merge without override.

## Gate 3 — First-phase integration

- [x] Combine PR-A and PR-B in a local integration worktree without changing
  their independent PR ownership.
- [x] Resolve current seams and rerun source, build, aggregate, browser,
  accessibility, privacy, route, CSP, and security checks.
- [x] Run one complete five-version integration build after both changes are
  present.
- [x] Obtain three independent integrated-diff reviews and re-review all fixes.
  Exact clean integration head `8109231` is the exact tree union of pushed
  PR-A and PR-B. Its final matrix passes links, Python 161/161, UI/AI 23/23,
  workflow 6/6, production/staging-full five versions, staging-latest,
  route-byte equality, Chromium 35/35 with zero skips, visual 8/8, and all
  marker/media/roster focused gates. The final third review round is 3/3 CLEAR.

## Gate 4 — Browser and publication acceptance

- [ ] Exercise every required latest/history, EN/CN, desktop/mobile,
  light/dark, pointer/touch/keyboard, success/failure/retry flow in Chrome or
  the available browser equivalent. The current automated matrix is 27/27 and
  advisory visual capture is 8/8; delayed pointer/touch, real Kapa, and
  post-deploy paths remain.
- [ ] Record each route/URL, action sequence, observed result, and before/after
  screenshot; keep UI/UX, accessibility, build, artifact, CI, and PR evidence
  distinct.
- [ ] Validate exact production-origin PR artifacts without publishing.
- [ ] Dispatch and validate `staging-next/latest` and `staging-next/full` using
  trusted Apache branches and fixed confirmation mappings.
- [ ] Verify initial Kapa corpus, source groups, CSP, render, locale isolation,
  privacy, timeout, and retry on staging before AI is enabled.
- [ ] Publish through the reviewed fixed-target workflow and verify production
  and staging native-search failure isolation, routes, aliases, language
  behavior, Community privacy, and click-gated external requests.
- [ ] Record post-deploy real Kapa smoke separately as advisory evidence.

## Gate 5 — PR-C: ASF-aware download experience

- [x] Inventory the current EN/CN download facts and OINK download resolver.
  Both languages duplicate 31 ASF artifacts and 93 release links; OINK v1.0.0
  is GitHub-release-specific and has no ASC field, so PR-C needs a narrow ASF
  data contract and site adapter.
- [ ] After first-phase stability, create the direct Apache PR-C branch from
  refreshed `master`.
- [ ] Inventory duplicated EN/CN download facts and define the single
  data-source contract without rewriting unrelated documentation.
- [ ] Implement the OINK download/checksum experience for ASF mirrors, official
  source artifacts, ASC, and SHA512.
- [ ] Ensure GitHub-generated source archives are never labeled as ASF official
  releases.
- [ ] Validate EN/CN parity, rendered links/artifacts, responsive browser
  behavior, accessibility, three independent reviews, fixes, and re-review;
  then commit, push, and open PR-C.

## Gate 6 — GitHub issue and design evidence

- [x] Add the prepared three-direction comparison
  (`evidence/ask-ai-visual-directions.png`), the selected Search Tail + Floating
  Launcher decision, and the prohibition on the old red/pink UI to
  [Issue #467 V8](https://github.com/apache/hugegraph-doc/issues/467#issuecomment-5541691334).
- [ ] After staging validation, append final desktop/mobile, light/dark
  screenshots and evidence to Issue #467 without overwriting history.
- [ ] Ensure PR-B closes Issue #468.
- [x] Open deferred full-text-search
  [Issue #471](https://github.com/apache/hugegraph-doc/issues/471) with the
  summary-search baseline, clearly labeled 233–243 KiB gzip planning estimate,
  per-language/per-version performance boundary, and no implementation.

## Gate 7 — OINK upstream and final closure

- [x] Submit the generic search-tail extension API proposal to
  `github.com/pgsty/oink`.
- [x] Submit the generic palette extension and sidebar-interaction fixes
  upstream as OINK
  [#40](https://github.com/pgsty/oink/issues/40) and
  [#41](https://github.com/pgsty/oink/issues/41).
- [x] Record upstream URLs/status without making upstream acceptance block
  HugeGraph delivery.
- [ ] Freeze the final integrated diff and evidence, rerun all applicable
  completion gates, complete the final three-reviewer cycle and fix/re-review,
  and confirm no unresolved high-severity finding.

## Current waits and unresolved capabilities

- Kapa EN source-group ID: create and record it after the reviewed staging
  `/docs/llms-full.txt` corpus is reachable.
- Kapa CN source-group ID: create and record it after the reviewed staging
  `/cn/docs/llms-full.txt` corpus is reachable.
- Kapa admin session/account: authenticated and inspected. The current source
  groups and website integration are known; creation and activation remain
  gated on the matching staging corpus and dedicated staging-domain entry.
