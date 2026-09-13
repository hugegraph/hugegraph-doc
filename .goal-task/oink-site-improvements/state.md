# OINK Site Improvements — Execution State

## Status

- Phase: cross-host handoff preparation after all local delivery code was
  pushed. `handoff.md` is the portable destination-host entrypoint.
- PR-A is ready for review and its exact-head CI is fully green; required human
  review remains pending. PR-B is pushed but its PR has not been created.
- Progress: 0/7 completion gates.
- Work-completion estimate: 65%; this is not a gate count and does not waive
  any of the seven conjunctive completion gates.
- Resume entrypoint: refresh PR #472 exact head and required human review. CI
  run `33934549197` is fully green as of the 2026-09-05 handoff refresh. If
  branch protection permits, merge PR-A without override; then refresh
  `master` and create PR-B from the already-pushed
  `feat/oink-community-content` branch with `Closes #468`.

Review-loop limit confirmed by the user:

- Default to at most three review-fix rounds per milestone.
- Extend only a reproducible release-blocking Critical finding to a fourth or
  fifth narrow re-review; never restart a broad review cycle.
- At the cap, record remaining non-high-severity findings in `todo.md` or the
  final issue and continue independent work. An unresolved high-severity
  finding keeps only its affected release gate open; it does not stop unrelated
  lanes.

## Confirmed outcome and scope

Implement the complete plan in
`.goal-task/oink-site-improvements/design.md`:

- PR-A: OINK core platform, five-version routing, Ask AI, CI/CD, and browser
  acceptance.
- PR-B: ASF Project members, search metadata, and bilingual content-component
  pilots.
- PR-C: the second-phase ASF-aware download experience after the first phase is
  stable.
- Complete the specified Issue #467/#468 and full-text-search issue work, plus
  the non-blocking OINK upstream proposals.

The deferred list in the design is out of scope. Do not import the Docusaurus
implementation, translate missing historical content, mechanically rewrite
other pages, or make Kapa a dependency of native search or site publication.

Unattended authority confirmed by the user:

- Once required CI, branch protection, and any required human review all pass,
  mark PR-A, PR-B, and PR-C ready and merge them without another prompt.
- Never use an administrator override or bypass a required review/check.
- Keep PR-B GitHub mappings empty and use the deterministic initials fallback;
  do not infer or populate the 22 member identities.
- Continue the reviewed Kapa source-group/domain configuration without another
  prompt. Only an expired session, CAPTCHA, or equivalent interactive account
  challenge requires the user to return.

## Current exact-head checkpoint

2026-09-14 PR-C checkpoint (destination host, org repository):

- The maintainer lifted the first-phase stability gate for PR-C on
  2026-09-13: if phase 1 changes, this branch merges them later; avoid
  blocking waits. PR-C therefore proceeds without waiting for #472.
- PR-C branch `feat/oink-download-asf` on `hugegraph/hugegraph-doc`, cut
  from `handoff/oink-site-improvements` head `82e9689`, head
  `892ba2b8359639c1ac8dd140296f9b54693ed407` (plus this state commit).
  `data/downloads/asf.json` is the single ASF download data source for EN
  and CN: dist path, component base prefixes, and per-release
  version/date/latest/incubating/binary/source sets. The
  `asf-downloads` shortcode and `layouts/_partials/asf-downloads.html`
  derive ASF mirror (`closer.lua ... ?action=download`), `.asc`, and
  `.sha512` links, reuse the OINK `td-asset-list` table shell, localize
  every label, link per-language release notes, and state in both
  languages that GitHub auto-generated source archives are not ASF
  releases. Malformed data, unknown or incomplete components, and a
  missing shortcode mode fail the build. Incubating is a per-release
  fact, so a post-graduation release is a data plus golden edit only.
- Evidence at `892ba2b`: the 31 derived artifacts match the live
  `downloads.apache.org/hugegraph/<version>/` listings in both directions
  (2026-09-13); rendered link sets (31 mirror, 31 ASC, 31 SHA512 per page)
  are identical to the previous hand-written tables for EN and CN; the
  real `versioning.py build` of release-1.7.0 still renders its original
  tables. Python 128/128 (python3.12), Node 24/24, links pass, strict
  latest build with zero warnings, `validate-site-output.py
  --security-only` pass, Playwright axe WCAG 2.2 AA 6/6 including both
  download pages (Playwright 1.62.1, latest-only artifact), and browser
  checks on desktop light/dark EN and mobile dark CN.
- Review: exactly three independent reviewers (correctness/tests,
  design/boundaries, security/maintainability) on `32366fa` raised two
  Important findings (silent `%!s(<nil>)` filenames on a component without
  prefix; `-incubating` baked into component prefixes) and six Minor
  findings; all fixed in `892ba2b`. Re-review CLEAR with every fix
  verified empirically.
- Not done on this host: the full five-version aggregate and complete
  Chromium matrix (versioning, platform, AI, ranking specs); exact-head CI
  runs them when the apache PR-C branch exists. Open for Jin: create the
  apache PR-C from this branch (or pull it into an apache branch).

2026-09-13 review-fix checkpoint (destination host, org repository):

- Working branch moved to `hugegraph/hugegraph-doc`
  `handoff/oink-site-improvements`. Commit
  `71a6584f273ad295f76f2f2130481439bfff46e7` on top of `bba8d83` fixes all
  four bitflicker64 review findings on PR #472: the workflow contract test is
  reduced to a hardened write-permission invariant, the hugo.sh reject
  machinery is deleted with its three tests (one flag-beats-env alignment
  test added), the Ask AI / version-fallback strings go through `T` with
  `i18n/cn.yaml` renamed to `i18n/zh-CN.yaml` (the site CN catalogue was
  silently unresolved because Hugo matches translations by locale), and the
  version-target route lookup is cached per page with an early break.
- Validation at that head: Python 122/122 (python3.12), Node 24/24
  (tests/ui-ai plus workflow contract), `bash dist/validate-links.sh` pass,
  strict wrapper production builds for latest and 1.7 with zero
  MISSING_TRANSLATION warnings (Hugo 0.166.0 extended locally; CI pins
  0.165.0). Two independent read-only review rounds: round 1 raised one
  Important (write-scope guard) and three Minor findings, all fixed; round 2
  re-review CLEAR.
- The apache PR #472 branch still points at `25f3e8c`; the maintainer pulls
  these commits into `feat/oink-core-platform` before the merge review.
  Chromium E2E and the full five-version aggregate were not rerun on this
  host; exact-head CI reruns when the apache branch advances.

Latest authoritative checkpoint at pause:

- PR-A is clean and pushed at
  `25f3e8c3f7982cbf1d08c4bda572e9da9add79eb`. PR #472 is no longer a draft;
  it is `REVIEW_REQUIRED`. Exact-head CI run
  `https://github.com/apache/hugegraph-doc/actions/runs/33934549197` completed
  successfully across prepare, all five version builds, aggregate, E2E,
  visual, and deploy; publish was correctly skipped for the PR event. Do not
  merge until required human review and branch protection are green.
- PR-B is clean and pushed at
  `bb270838626165ad2c98c11150dde39f4eb113c9` on
  `origin/feat/oink-community-content`; no PR exists yet.
- Integration is clean at
  `81092317458740eeaf9da8b289cb0ea7f226aaf2`. Its tree is byte-identical to
  the synthetic union of the pushed PR-A and PR-B heads, so the local
  integration branch contains no unique unpushed code.
- Remote `master` was rechecked immediately before both pushes and remained
  `d88167dd797efafea50cec59909d57849703fde5`.
- The checkpoint applies one browser-safe contract to HTML, SVG, CSS,
  `srcset`/`imagesrcset`, runtime `data-td-*` URLs, form/navigation attributes,
  duplicate attributes, CSS escapes/functions, and local resource existence.
  All rendered resource `data:` URLs are forbidden. Bootstrap's 20 embedded
  control SVGs are now local files, and historical overlays copy those files
  plus the two shared homepage hero images.
- PR-A exact-head matrix is fully green: links; Python 124/124; UI/AI 23/23;
  workflow 6/6; production and staging-full five-version 1082-HTML aggregates;
  195-route byte equality; staging-latest 276 HTML; Chromium 32 passed with
  three expected PR-B-only skips; visual 8/8. Evidence:
  `/private/tmp/hgdoc-pra-25f-final.0CodtH/`.
- Integration exact-head matrix is fully green: links; Python 161/161; UI/AI
  23/23; workflow 6/6; production and staging-full five-version 1082-HTML
  aggregates; route byte equality; staging-latest 276 HTML; Chromium 35/35
  with zero skips; visual 8/8; marker pairs 1009/1009 with zero unpaired;
  Community landing HTML/Print EN/CN 4/4. Evidence:
  `/private/tmp/hgdoc-integration-810-final.LiNnlr/`.
- The final integrated review stopped at the user-confirmed three-round cap.
  The third round used exactly three independent reviewers and finished 3/3
  CLEAR with no unresolved material finding.
- Local preview servers at ports 4186 (PR-A) and 4187 (integration) were
  stopped as part of the pause; both ports are no longer listening.
- PR-C baseline inventory is complete but implementation remains correctly
  gated behind first-phase stability. EN/CN currently duplicate the same 31
  ASF artifacts and 93 mirror/ASC/SHA512 links per language. The planned
  implementation uses one restricted ASF data source and a site adapter rather
  than OINK's GitHub-release-only download resolver.

Historical checkpoint detail below is retained as failure/recovery evidence;
any head or active status there is superseded by the latest checkpoint above.

- PR-A local HEAD is
  `73f31a44dd9c39e70fc2b8ce412ac56040d6b5b7`, twelve commits ahead of the draft
  PR's remote head
  `3adba9eeb7c0cbaa83d1568243954aab480f965a`. Remote `master` and the PR base
  were re-fetched on 2026-09-05 and remain
  `d88167dd797efafea50cec59909d57849703fde5`.
- The first exact-head PR-A matrix at `dc51b02e` passed links, Python 101/101,
  UI/AI Node 23/23, workflow 6/6, and the first three production builds, then
  correctly stopped when artifact validation exposed that the new social
  validator rejected Hugo alias/redirect pages without social tags. Its
  temporary evidence was removed after the failure was recorded here.
- Repair `127fbd733` identifies redirects before social validation, permits
  only redirects with both social tags absent, and retains strict 1+1 matching
  metadata on content pages and partial-tag failure. The final exact-head
  PR-A matrix is fully green: links, Python 102/102, UI/AI Node 23/23,
  workflow 6/6, production and staging-full five-version builds (1082 HTML),
  staging-latest (276 HTML), 195-route byte equality, exact AI fixture,
  Chromium 32 passed with three expected PR-B-only skips, and visual 8/8. Its
  temporary evidence was removed after later validator commits superseded it.
- The integration worktree is clean at
  `1d6e1303ff38bd1fc7e3b148e6da3628eb26a10c`, containing PR-A, PR-B, all
  logical-equivalence/LLMS/social hardening, and the redirect-validator repair.
  The superseded `aae94cdc6` matrix passed links, Python 136/136, UI/AI Node
  23/23, workflow 6/6, and all five production builds before reproducing the
  same redirect false positive and stopping. That superseded temporary evidence
  was removed after its failure was recorded. The final exact-head integration
  matrix is now fully green: links, Python 137/137, UI/AI Node 23/23,
  workflow 6/6, production and staging-full five-version builds (1082 HTML),
  staging-latest (276 HTML), exact route equality, AI fixture, Chromium 35/35
  with zero skips, ranking 24/24, Community parity across all three artifact
  modes, and visual 8/8. Evidence:
  `/private/tmp/hgdoc-integration-97643.dYy6VS/` (removed after the new head
  superseded it). Exactly three independent reviewers reviewed frozen clean
  head `97643b328`: reviewer #1 was CLEAR;
  reviewer #3 found that ordinary meta-refresh aliases can reuse a generic URL
  validator that permits external/protocol URLs, while route generation can
  discard an external authority and treat its path as local. The repair must
  require same-origin, same-version-scope, existing artifact targets for
  ordinary aliases while retaining only the exact `client-go` exception.
  Reviewer #2 found that the security validator's fixed error-document list
  covered only root/1.7/1.5 and omitted 1.3/1.0, even though the current ten
  generated 404 pages are correct. The fix derives the complete set from the
  version manifest and proves security-only publication checks reject SEO
  regressions for every version. Those two fixes initially over-constrained
  the intentional archived home redirects, which a new matrix and two
  reviewers caught before push. Commit `8c99d6d` / integration `cca2d0b1e`
  now permits only the exact archived English and Chinese home redirects while
  retaining strict ordinary-alias validation. Focused tests and all four real
  historical artifact validations pass. The next re-review found one remaining
  WHATWG/parser ambiguity: `https:///...` has no authority under Python
  `urlsplit` but browsers can interpret its first path segment as a host.
  Commit `2b4e221` / integration `a7e349d` rejects authority-less HTTP(S)
  aliases plus all whitespace/control characters and adds failing-first
  fixtures. The following adversarial review proved aliases themselves closed
  but found the same authority-less HTTP(S) ambiguity in ordinary rendered
  links and the aggregate security-only validator. Commit `600b828` /
  integration `8ad410135` centralizes the fail-closed URL-shape rule across
  ordinary version validation and security-only/full aggregate scans, rejecting
  authority-less HTTP(S), whitespace/control, backslashes, and protocol-relative
  forms. The next adversarial review proved ordinary links closed but found
  `srcset`, object/media resources, and CSS tokens were not all routed through
  that policy. Commit `73f31a4` / integration `1d6e1303f` applies one shape
  validator to every HTML/CSS request token and makes artifact validation call
  the complete rendered security scan. Failing-first multi-resource fixtures,
  Python 109/109, production/staging-full 1082-HTML scans, and staging-latest
  276-HTML validation pass. New exact-head matrices and all exactly three
  adversarial reviews remain required.
- Draft [PR #472](https://github.com/apache/hugegraph-doc/pull/472) was
  fast-forwarded without force to exact reviewed head `3adba9eeb`; remote
  `master` remained `d88167dd7`. CI run
  [33905024759](https://github.com/apache/hugegraph-doc/actions/runs/33905024759)
  was cancelled while queued after the integrated review proved that head
  incomplete; its cancelled jobs are not acceptance evidence. The PR remains
  draft and `REVIEW_REQUIRED`; its body is prepared with the latest local
  counts but must not be updated remotely until the new exact-head matrices and
  three reviews clear.

## Active truth and authority

Use this order when sources conflict:

1. latest user confirmation;
2. `.goal-task/oink-site-improvements/design.md`;
3. current source and tests at the refreshed Apache `master`;
4. Apache HugeGraph issues and PRs;
5. this state file and `todo.md`.

Active paths:

- `.goal-task/oink-site-improvements/design.md` — authoritative product,
  interface, release, and acceptance design.
- `.goal-task/oink-site-improvements/state.md` — execution contract, gate
  evidence, recovery entrypoint, and next action.
- `.goal-task/oink-site-improvements/todo.md` — item-level status, dependencies,
  waits, and deferrals.
- `.goal-task/oink-site-improvements/lessons.md` — evidence-backed reusable
  lessons promoted after concrete failures; not a progress log.
- `versions.json`, `hugo.yaml`, `.github/workflows/hugo.yml`,
  `scripts/versioning.py`, `scripts/test_versioning.py`, and
  `scripts/test_validate_site_output.py` — current implementation and validator
  baseline.

`AGENTS.md` still describes the pre-OINK Docsy/Hugo 0.102.3 site. Follow its
general bilingual and evidence requirements, but resolve obsolete technical
facts from the current source and CI. Updating it is not part of the confirmed
product scope.

## Baseline

- Initialized: 2026-09-04, Asia/Shanghai.
- Worktree:
  `/Users/zhu/.codex/worktrees/10a2/hugegraph-doc`.
- Remote target: `https://github.com/apache/hugegraph-doc.git`.
- Baseline revision: `d88167dd797efafea50cec59909d57849703fde5`.
- `HEAD` and `origin/master` were equal and the worktree was clean at
  the latest refresh. The primary worktree now uses
  `feat/oink-core-platform` at that revision.
- GitHub account `imbajin` was authenticated with push access to
  `apache/hugegraph-doc`.
- The refreshed baseline used OINK `v1.0.0`, Hugo `0.165.0`, and three
  versions. PR-A now derives `latest / 1.7 / 1.5 / 1.3 / 1.0` from
  `versions.json` and includes a Node 24/Playwright workspace.
- Issues #467 and #468 are open. No existing PR is assigned to PR-A, PR-B, or
  PR-C.
- Full-content local search is now tracked separately in Apache
  [Issue #471](https://github.com/apache/hugegraph-doc/issues/471); it records
  the current summary baseline and labels the 233–243 KiB gzip figure as an
  estimate rather than current-HEAD evidence.
- The Issue #467 Ask AI comparison board was generated with built-in
  `image_gen` and saved as
  `.goal-task/oink-site-improvements/evidence/ask-ai-visual-directions.png`
  (1717×916, SHA-256
  `68a97ffa93941608fa6d112e77331e464df59a824b8073ebf1c5543a472c98c2`).
  The recorded decision combines Search Tail and Floating Launcher, excludes a
  persistent side panel and the old red/pink UI. It is published as
  [Issue #467 V8 evidence](https://github.com/apache/hugegraph-doc/issues/467#issuecomment-5541691334);
  final staging screenshots remain a later append-only checkpoint.
- Kapa website/integration ID
  `0b277570-4740-451e-96fa-1e4ac1ac5e88` is confirmed in the authenticated
  Apache HugeGraph admin project. The synchronized browser session is active.
  Existing sources and the single `HugeGraph` product group were inspected
  read-only; reviewed latest EN/CN source-group IDs do not yet exist. The
  widget currently allows production and general staging, but not the
  dedicated `https://hugegraph-oink.staged.apache.org` origin. Do not create
  groups, sources, or the domain entry until the matching staging LLMSFULL
  corpus exists.
- Baseline validation on the original initialization revision passed
  `bash dist/validate-links.sh` and
  `python3 -m unittest discover -s scripts -p 'test_*.py' -v`
  (66 tests).
- Apache master then advanced through #470 from `b1ed7eb84` to
  `d88167dd7`, synchronizing 1.7 content and changing 111 paths, including
  `scripts/versioning.py`, its tests, both Docs roots, and planned content-pilot
  pages. The primary and every implementation lane must use the new revision.
- A second direct `git fetch`, `git ls-remote origin refs/heads/master`, and
  main-checkout comparison on 2026-09-04 confirmed
  `origin/master = local master = d88167dd797efafea50cec59909d57849703fde5`.
  PR-A, PR-B, UI, and versioning worktrees all reported this revision as an
  ancestor before further integration.
- On `d88167dd7`, link validation and all 67 Python tests passed.
  Baseline `hugo --minify` also passed with Hugo
  `v0.165.0+extended`; it produced 520 EN/CN pages and 814 files in an isolated
  temporary destination.
- The first versioning-lane baseline run exposed an existing path-safety defect:
  `prepare_output_directory()` can treat a `/private/tmp` checkout root as a
  disposable output after path canonicalization. The isolated worktree was
  removed, its branch reference remained intact, and that lane must add a
  regression guard for repository roots, ancestors, and checkout descendants
  before continuing.
- The same defect later deleted the Community lane after its uncommitted roster
  work had passed eight focused tests, offline validation, and a Hugo build.
  The branch/worktree was rebuilt at `d88167dd7`; that lane is reconstructing
  from retained tool evidence and must checkpoint small validated commits before
  broader tests. Until the safety fix lands, no `/tmp` implementation worktree
  may run the affected full versioning suite.
- Safety checkpoint `f1bffd0827d217ad17eecf5ba00ace793ecf3ff3`
  was integrated into PR-A as `4753dedb7`; the focused deletion regression and
  the complete 67-test Python suite both pass from the primary worktree.
- Despite that focused/current-checkout pass, the Community `/tmp` worktree was
  deleted a third time while reviewer fixes were uncommitted. The versioning
  lane and PR-B design review were interrupted; the Community branch was moved
  to `/Users/zhu/.codex/worktrees/hgdoc-oink-community-review`. Cross-worktree
  cleanup safety is an active high-priority investigation, and broad cleanup
  tests remain paused outside the primary worktree.
- Read-only process and source audit found no command that intentionally
  targeted the Community path and no surviving cleanup process. It confirmed a
  remaining safety gap: `prepare_output_directory()` protects only its current
  `ROOT`, not sibling or prunable Git worktrees. The active hypothesis is to
  fail closed for every registered worktree plus any candidate below a `.git`
  file/directory ancestor; a failing sibling-worktree regression must precede
  the fix.
- Cross-worktree fix `5edda2d59` is now integrated. The old implementation
  failed the new sibling-checkout regression before the fix; afterward four
  focused safety tests, the complete 70-test Python suite, and a live
  registered `/tmp` sibling check with `shutil.rmtree` mocked all rejected
  deletion before it could occur.
- UI/AI checkpoints were integrated as `61e20f455` and `8d5bf876e`.
  Integration found additional Sass compilation failures not covered by the
  Node contracts. Commit `70fa04695` fixes the shared root cause; with an
  isolated Hugo cache, the production build passes (520 pages, 817 files) and
  all eight UI/AI Node tests pass.
- UI/AI hardening `4d6593dc6` is now integrated. The combined PR-A tree passes
  12/12 UI/AI Node contracts and all 67 Python tests. Default and AI-enabled
  Hugo builds, enabled-artifact security validation, invalid-config failure,
  sidebar/search browser interactions, click-before-zero-external-resource
  checks, and the 1200×630 social image were independently exercised by the
  lane; real Kapa opening and staging-derived CSP hosts remain external gates.
- Five-version core commit `9c14050d5` is integrated. The lane built and
  validated latest, 1.7, 1.5, 1.3, and 1.0 from immutable refs with route,
  canonical, manifest, alias, hreflang, and historical sitemap checks. The
  workflow/E2E checkpoint and single-source handling for the static Hugo menu
  remain under active integration.
- PR-A is now at `474874c` and includes the secure fixed-target workflow,
  per-build immutable SHA fetch, 24-query browser ranking gate, shell/AI/
  Community/axe Chromium gates, eight advisory visual states, archive robots
  fixes, and manifest-derived Hugo menus. The static version arrays were
  removed from `hugo.yaml`.
- PR-A reviewer fixes are now checkpointed through `401134d`. Commit
  `d3cf6cc` preserves production historical selectors in latest-only staging
  and rejects existing parent symlinks before cleanup; `ffc41ad` stabilizes
  search retry DOM, forces fresh Kapa retry requests, blocks late renders,
  derives Kapa colors from the site token, and limits Backlinks to five before
  expansion; `72989ad` propagates the historical origin through aggregate
  revalidation and CI. The first reviewer re-review then found cross-operation
  publication concurrency, a symlinked `RUNNER_TEMP` root, dark Kapa accent
  drift, and a stale retry tooltip. Commits `79d12ba`, `1e7258f`, and
  `67ff2e8` close those findings with targeted regressions. Current exact-HEAD
  checks pass Python 77/77, UI/AI Node 15/15, and workflow contracts 5/5. A
  direct latest-only browser fixture also
  passes all 14 applicable latest/UI/AI/accessibility checks; the full
  versioning browser lane passes against the current five-version aggregate:
  26 passed with 3 expected PR-B-only skips. The same aggregate contains 1082
  HTML files, 3413 published files, and 10 error documents; latest-only staging
  aggregation contains 276 HTML and 822 published files with all historical
  selectors remaining on the production origin.
  The final three-reviewer cycle on `401134d` is clear for correctness,
  design/accessibility, and security/privacy; no material finding remains.
- PR-A was pushed directly to Apache and opened as draft
  [PR #472](https://github.com/apache/hugegraph-doc/pull/472). Its remote head
  is exactly `fe551ba06a9afed24c864759acb8c257fb29c238` and base is `master`.
  The first CI run built all five versions, then exposed a leading-dash
  argparse seam in aggregate. Commit `fe551ba` binds the run-scoped suffix to
  its option; workflow contracts are now 6/6 and the replacement exact-head CI
  run is queued. No duplicate PR or branch existed before creation.
- PR-B implementation is checkpointed in six commits ending at
  `d50bc28e85835e9325ff6b0e9ac789156a9e22bd`. Nine focused roster tests,
  offline roster/render validation, minified Hugo build, 22-member parity
  across six EN/CN HTML/Print/Markdown outputs, both LLMSFULL outputs, 276-HTML
  security validation, link validation, and diff checks pass. Browser ranking,
  the three-reviewer gate, and any human-reviewed GitHub mappings remain open.
- PR-B independent reviewer 1/3 reported four high-confidence Important
  findings: unmapped ASF profile URLs were not enforced, equal public names
  made ordering hash-dependent, orphan-cleanup failure could replace the
  last-good roster, and product-output tests did not yet prove component/index/
  LLMSFULL behavior. The PR-B lane is fixing all four with targeted regression
  evidence before reviewers 2/3 and re-review.
- Reviewer 1 re-review confirmed those first fixes, then found remaining gates
  around real search ranking, CI wiring, strict Chair/avatar types and paths,
  rollback-failure semantics, and fixed Hugo setup. Reviewer 2 found incorrect
  Markdown ordering/title semantics, shared landing-dispatcher and LLMSFULL
  ownership drift, and a stale ICC flag. Reviewer 3 added existing-avatar
  verification, bounded/allowlisted network reads, actual WebP decoding,
  identifier/Markdown escaping, and genuinely offline validation concerns.
  PR-A now owns LLMSFULL plus ranking/CI setup; PR-B is addressing the remaining
  data, section-specific rendering, and security findings before all three
  reviewers re-review.
- PR-B is now at `b6e651c` after closing reviewer findings for pre-mutation path
  validation, redirect allowlists, local and remote JSON schemas, real WebP
  decoding, role-local real-link parsing/order, Markdown boundaries, and
  cross-origin loading of its fingerprinted stylesheet. The fixed 24-query set
  ranks 24/24 in the actual OINK search engine after the two targeted symmetric
  boosts.
- PR-B final HEAD is `4d02fcb`. Exactly three independent reviewers re-reviewed
  every fix and reported clear with no material finding. The integrated
  ownership test also accepts PR-A's exact bilingual LLMSFULL contract while
  continuing to reject LLMSFULL in standalone PR-B.
- Local integration branch `work/oink-integration` combines PR-A and PR-B. A
  complete five-version production-origin run built and validated 3414 files,
  1082 HTML files, and 10 error documents. Blocking workflow contracts passed
  4/4 and Chromium passed 27/27; advisory visual capture passed 8/8. Screenshots
  are retained under
  `.goal-task/oink-site-improvements/evidence/browser/`.
- The refreshed integration head is `d91f5b55`. The first current-HEAD browser
  run exposed that the search-retry fault injector used `route.continue()` and
  bypassed the local aggregate remapper. Commit `58e7dba` switches the success
  attempt to `route.fallback()`; the isolated regression passes and the
  complete integrated Node/Chromium gate is now 49/49. The production
  five-version aggregate remains green at 1082 HTML, 3414 files, and 10 error
  documents; Python is 112/112 and advisory visuals are 8/8.
- OINK upstream proposals are filed as
  [#40 search-tail/palette extension](https://github.com/pgsty/oink/issues/40)
  and
  [#41 sidebar disclosure/isolation contracts](https://github.com/pgsty/oink/issues/41).
  The account has read-only code permission, so issues are the available
  upstream delivery mechanism and upstream acceptance remains non-blocking.

Refresh the remote revision, open PR/Issue state, staging/production deployment,
Kapa configuration, and write capability whenever those facts can affect an
action or claim.

## Work structure and ownership

- PR-A branch: create directly in `apache/hugegraph-doc` from the then-current
  `master`. Use exclusive lanes for UI/AI, versioning/CI, and E2E. A single
  integration owner owns shared configuration, lockfiles, workflows, generated
  manifests, and the combined diff.
- PR-B branch: create directly in `apache/hugegraph-doc` from the then-current
  `master`. It may run in parallel but must not edit PR-A-owned shared shell,
  configuration, or workflow files.
- PR-C branch: create directly in `apache/hugegraph-doc` only after PR-A and
  PR-B are integrated and the first-phase five-version build is stable.
- OINK upstream target: `github.com/pgsty/oink`. Upstream acceptance is not a
  HugeGraph delivery gate; record the proposal/PR URL and retain the local
  compatibility layer until a usable release exists.
- The authenticated GitHub account currently has read-only repository
  permission on `pgsty/oink`; issue/proposal submission remains available, but
  a direct upstream branch is not. OINK issue #24 already covered a distinct
  cached-sidebar/JavaScript fallback bug and is closed, so new upstream reports
  must avoid duplicating it.

Every worker must record changed paths, exact commands, evidence, assumptions,
and unresolved risks. Workers must not overwrite another lane. The integration
owner resolves seams and reruns affected checks after combination.

Current local branches/worktrees:

- Integration: `feat/oink-core-platform` in the primary worktree.
- UI/AI lane: `work/oink-ui-ai` in `/tmp/hgdoc-oink-ui.Zix0W6`.
- Versioning/CI lane: `work/oink-versioning-ci`; its isolated worktree is being
  reconstructed after the baseline path-safety failure described above.
- Community/content lane: `feat/oink-community-content` in
  `/Users/zhu/.codex/worktrees/hgdoc-oink-community-review`.
- Integration validation: `work/oink-integration` in
  `/Users/zhu/.codex/worktrees/hgdoc-oink-integration`.

## Invariants

- Native summary search remains complete and usable when AI is disabled, slow,
  blocked, or broken.
- No Kapa active resource or request occurs before an explicit Ask AI action.
  Only the trimmed query and locale-specific source group may leave the site.
- The five-version order and refs come from `versions.json`; all consumers are
  derived from it.
- Historical content retains historical facts, missing Chinese pages are not
  replaced with English, and only true bilingual equivalents receive
  `hreflang`.
- Community roles derive from ASF public data; GitHub identity is never guessed.
  Browser visitors make no GitHub or Whimsy roster requests.
- Publication code never executes untrusted candidate code in the write-enabled
  job. `deploy` remains the required read-only gate.
- Staging and production native behavior remains usable if post-deploy Kapa
  smoke fails.

## Completion gates

1. PR-A satisfies every behavior, versioning, AI, CI/CD, security, and artifact
   contract in the design.
2. PR-B satisfies the deterministic roster, three-output parity, responsive
   Community, search metadata, and bilingual component-pilot contracts.
3. PR-A and PR-B are merged or otherwise integrated on the reviewed target, and
   one complete five-version integration build passes before publication.
4. Chrome or the available browser equivalent records functional and UI/UX
   evidence for the required latest/history, EN/CN, desktop/mobile, light/dark,
   keyboard, error, retry, and failure-isolation flows. Accessibility and
   advisory visual results are reported separately.
5. Staging and production acceptance passes for native search, routes, legacy
   aliases, language switching, Community privacy, and click-gated external
   requests; initial Kapa corpus/source-group/CSP activation is verified before
   enabling AI. Post-deploy Kapa smoke remains advisory as designed.
6. PR-C delivers the ASF-aware data-driven download page with mirror, official
   source artifact, ASC, and SHA512 semantics, without presenting GitHub source
   archives as ASF releases.
7. Issue #467, Issue #468 closure linkage, the new full-text-search issue, and
   OINK upstream submissions are recorded; final integrated changes pass the
   required independent review and re-review with no unresolved high-severity
   finding.

The existing confirmed repository checks include:

```bash
bash dist/validate-links.sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

Record the exact added Node/Playwright commands only after their scripts and
lockfile exist. Do not replace browser interaction or publication acceptance
with a green build.

## Execution loop

Batch low-risk changes by shared module and validation surface. After each
frozen batch, run affected tests and targeted checks. Run complete builds,
browser matrices, aggregate checks, and integrated review at phase boundaries
and after the final diff freezes. Never weaken assertions, skip mandatory
checks, ignore exit codes, or report unobserved success.

After each productive loop report:

```text
Progress [██████░░░░] 60% (3/5 gates)
This loop: <completed work and evidence>; Remaining: <main open work>.
Next: <one primary action>.
```

Use the actual fixed denominator and never report 100% before all seven gates
pass. Before compaction, quota wait, handoff, or session end, update this file
with gate progress, latest commit, validation/review evidence, active waits,
uncommitted changes, and one next action.

## Retry, waits, and recovery

Try one failing item at most three times by default. Then record the exact
failure, evidence, attempted recovery, dependency, and unblock condition in
`todo.md`; mark it waiting, deferred, or needs input; move it and its dependents
behind independent work; continue the highest-value non-conflicting item; and
recheck at a phase boundary or when the condition changes.

CI queues, downloads, Kapa/admin waits, staging propagation, quota limits,
first failures, and optional missing dependencies do not stop independent work.
Useful parallel work includes the next module inventory, non-conflicting
implementation, evidence maintenance, failure analysis, and acceptance
preparation.

Set the overall goal `blocked` only when the same condition has recurred for at
least three goal turns and every meaningful remaining item, after recovery,
authorized alternatives, splitting, reprioritization, and completion of
independent work, still jointly depends on that same logical conflict, safety
boundary, or verified mandatory external dependency.

## Authorization, safety, and remote effects

All user-authorizable actions required inside this confirmed scope are already
approved, including local/environment changes, dependency installation,
browser uploads, entry of available credentials, worktrees, direct Apache
branches, commits, pushes, PR and Issue actions, tests, workflow dispatches,
review responses, and fixed staging/production publication. Do not ask again or
wait, defer, or mark work blocked because of an authorization prompt.

This approval does not fabricate credentials, sessions, tools, source-group IDs,
or capabilities; override higher-priority safety boundaries; or authorize work
outside scope. Never expose or persist credential values in logs, screenshots,
state, commits, PRs, or issues. Record only redacted actions and outcomes.

Before each destructive or remote mutation, record or verify its exact target
and impact. Direct source branches and PRs target `apache/hugegraph-doc`;
publication targets only `asf-staging-oink` or `asf-site` through the reviewed
workflow. Continue independent work when Kapa or another genuine capability is
unavailable while keeping its completion gate active.

## Review and commits

At every major behavior-change milestone, use exactly three independent
read-only reviewers on the integrated diff: correctness/tests,
design/boundaries, and security/maintainability. After fixes, re-review affected
changes. Run at most three fix/re-review rounds by default; unresolved failures
remain deferred and prevent completion.

Create focused local milestone commits only after applicable validation and
review pass. Push the direct Apache branches only after rechecking their exact
head and target. A checkpoint commit may preserve a required baseline with
explicit unmet gates, but it does not imply review success or completion.
