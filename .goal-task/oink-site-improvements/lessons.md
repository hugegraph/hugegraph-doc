# OINK Site Improvements — Reusable Lessons

## Bound review-fix convergence

Use at most three broad review-fix rounds for one milestone. A fourth or fifth
round is reserved for a reproducible release-blocking Critical and must be
narrowly scoped to that finding. Record remaining lower-severity work instead
of repeatedly invalidating an otherwise complete matrix; keep only the affected
gate open and continue independent lanes.

## Parse browser request syntax, then validate emitted targets

Regex-only URL scanning missed CSS escapes, quoted URLs with spaces,
`image-set()`, SVG IRIs, duplicate HTML attributes, and list-valued image
attributes. A publication gate should tokenize each browser request surface,
apply one scheme/authority policy, and resolve same-origin resources against
the emitted artifact so a safe-looking but missing target cannot pass.

When a theme embeds `data:` control images but the site forbids rendered data
URLs, externalize the complete theme variable set and test historical overlay
copying. A successful latest build does not prove version artifacts contain the
same shared static resources.

## Canonicalize both sides of destructive path checks

- Symptom: the versioning output-cleanup regression test deleted two isolated
  worktrees created below `/tmp`, even though the test expected repository-root
  cleanup to be rejected.
- Root cause: on macOS, `/tmp` resolves to `/private/tmp`. The candidate output
  path was canonicalized while the repository root used for the safety
  comparison was not, so equal paths appeared different.
- Evidence: the first run removed the versioning worktree; a later full-suite
  run independently removed the Community worktree after its focused tests and
  Hugo build had passed. Both branch refs survived, but uncommitted files did
  not.
- Partial fix: commit `f1bffd0827d217ad17eecf5ba00ace793ecf3ff3`
  canonicalizes the current repository boundary and rejects its root,
  ancestors, and descendants. Its focused regression passes, but a third
  deletion of a different parallel worktree proves that current-checkout
  protection alone does not establish cross-worktree safety.
- Complete guard: commit `178f300c59cebb3ea4b9c135162108a24aeab6ef`
  enumerates every registered Git worktree, rejects equal/ancestor/descendant
  relationships, detects `.git` markers for prunable or unregistered
  checkouts, and fails closed when enumeration is unavailable. Its regression
  first failed against the old implementation, then passed after the fix; a
  live registered `/tmp` sibling was also rejected with deletion mocked.
- Prevention: before any recursive cleanup, resolve both the protected
  boundary and candidate path, then test equality and both ancestor
  directions. Include a platform alias case such as `/tmp` versus
  `/private/tmp`, enumerate Git worktree boundaries when multiple checkouts
  share one repository, and do not run broad cleanup tests until the
  cross-worktree case is proven.

## Checkpoint isolated parallel work before broad validators

- Symptom: Community implementation that had already passed eight focused
  tests, offline roster validation, and a Hugo build was lost when a later
  unrelated full-suite validator removed its worktree.
- Cause: a broad validation surface exercised destructive code outside that
  lane's ownership before the lane had made a recoverable checkpoint.
- Prevention: after each focused green batch in an isolated worktree, create a
  scoped local commit before running broad cross-subsystem validation. Broad
  validators remain mandatory, but they run after destructive-path guards and
  from a location whose recovery boundary is understood.
- Additional evidence: the first reviewer-fix batch passed 16 focused tests but
  was still lost before its checkpoint when the `/tmp` worktree disappeared a
  third time. High-risk parallel work now uses a worktree under
  `/Users/zhu/.codex/worktrees/` until the cross-worktree cleanup cause is
  proven and fixed.

## Isolate Hugo caches when debugging failed resource pipelines

- Symptom: after a Sass compilation error, the next Hugo build waited with zero
  CPU instead of reporting the next error.
- Evidence: a process sample showed Hugo goroutines waiting; rerunning the same
  source with a fresh `HUGO_CACHEDIR` immediately reported the next unsupported
  Sass expression, and the final isolated-cache build completed.
- Prevention: parallel worktrees and failure diagnosis use distinct Hugo cache
  directories. Treat a post-failure cache wait separately from the source error
  and do not infer that the template itself is deadlocked.

## Preserve browser CSS functions through the repository Sass compiler

- Symptom: Node UI contracts passed, but Hugo rejected CSS Level 4
  `rgb(r g b / a)` and tried to numerically evaluate `min()` containing
  viewport units.
- Root cause: the current Sass transformer parses those functions before the
  browser can evaluate them.
- Fix: use compatible `rgba(r, g, b, a)` colors and quote/unquote browser-owned
  `min()`, `max()`, `env()`, and nested `calc()` expressions.
- Prevention: every style batch must pass the actual Hugo production build;
  JavaScript or textual contract tests are insufficient compilation evidence.

## Propagate release-scope inputs through every validation boundary

- Symptom: a latest-only staging artifact validated immediately after build,
  but aggregate revalidation would have interpreted historical selector URLs
  without the production historical origin.
- Root cause: `historical_origin` reached build and direct validation but was
  dropped by the aggregate CLI and workflow step.
- Fix: make the aggregate parser, artifact revalidation namespace, and workflow
  environment/command carry the same value; validate both the production
  five-version aggregate and a staging latest-only aggregate.
- Prevention: treat build, upload, download, aggregate, revalidation, and
  publish as one parameter-propagation chain. A contract input is complete only
  when the final consumer receives it and a workflow test proves the wiring.

## Match browser fixtures to the contract under test

- Symptom: latest UI, search, AI, and accessibility checks passed against a
  direct Hugo build, while all aggregate/version-history checks failed.
- Root cause: the browser suite was pointed at a latest-only site, which cannot
  contain aggregate metadata, archived routes, aliases, or the materialized
  five-version selector.
- Prevention: run latest behavior against a direct fixture only when isolated
  evidence is useful; run the full blocking suite against the exact
  five-version aggregate. Classify fixture-shape failures separately from
  product regressions, then rerun with the correct artifact before reporting.

## Use fallback when a Playwright fault injector must preserve remapping

- Symptom: integrated search retry made two requests but never rendered a
  result; the same behavior had passed in PR-A alone.
- Root cause: the test-specific route aborted the first hashed index request
  and used `route.continue()` for the second. That bypassed the shared handler
  which remaps production-origin URLs to the local aggregate. PR-A passed only
  because its hash happened to exist on production; the PR-B-integrated hash
  correctly returned 404 there.
- Fix: use `route.fallback()` after the injected failure so the shared artifact
  handler fulfills the retry from the local aggregate.
- Prevention: fault-injection routes should terminate only the intended
  failure attempt. Successful attempts must delegate through the same fixture
  routing chain used by the rest of the suite, so tests never depend on live
  deployment hashes.

## Validate version switching as a logical-page contract

- Symptom: the five-version order, version roots, builds, and broad browser
  checks were green, but switching from a deep documentation page still sent
  users to the target version's Docs root.
- Root cause: root-level version metadata proved that each release existed but
  did not encode whether the current logical page had an equivalent in each
  target release.
- Fix: generate a deterministic route map from all five canonical inventories,
  materialize page-specific selector options for every rendered artifact, and
  use one Hugo partial for desktop, mobile, and Palette entry points. Preserve
  query/hash only for true equivalents; otherwise use the matching locale Docs
  root plus a one-shot fallback sentinel and notice.
- Prevention: validate exact forward, missing/null, and reverse equality
  between the route map and every version's canonical inventory. Browser tests
  must cover equivalent and missing EN/CN pages through all selector surfaces;
  version ordering and root-URL assertions alone do not prove page semantics.

## Keep manifest-derived behavior in every supported entry point

- Symptom: CI artifacts had five route-aware versions, while the documented
  direct `hugo server` and strict-build commands rendered no configured
  versions. After adding a manifest-aware wrapper, native anchors became
  correct but Palette still consumed root-only action-manifest options.
- Root cause: configuration, native links, and action manifests were produced
  at different layers. Fixing only the command or visible anchors did not make
  the render-time action contract equivalent to the postprocessed CI artifact.
- Prevention: every documented build/serve entry point must derive from the
  same manifest and must prove both visible anchors and embedded action
  manifests on a deep page. A live-reload server test must exercise Palette,
  because build-after-processing evidence cannot prove development-server
  behavior.

## Test every publication-origin mode independently

- Symptom: production and latest-only staging passed, but full staging would
  fail when an archived version lacked a latest-shared page.
- Root cause: the missing shared-route rewrite hard-coded the production
  origin. That happened to be correct for production and latest-only staging
  history, but contradicted full staging where both current and historical
  versions share the staging origin.
- Prevention: test production full, staging full, and staging latest as three
  distinct origin matrices. Shared-route fallback follows the current artifact
  origin; only historical selector destinations use `historical_origin`.

## Model renamed-page equivalence separately from canonical identity

- Symptom: historical readme-to-readme switching was fixed, but latest
  `introduction` still could not reach older `introduction/readme` pages.
- Root cause: some versions contain both a section landing and a readme while
  older versions contain only the readme. Collapsing both canonical pages into
  one ID loses information; keeping them unrelated loses a valid migration.
- Prevention: keep the canonical inventory one-to-one and record explicit,
  disjoint, locale-matched equivalence groups. Resolve an exact target first;
  only a unique alternate may count as equivalent. Alias edges must terminate
  at a canonical page in the same artifact before authorizing a cross-version
  target.

## Use dedicated contracts for corpus provenance and social images

- Symptom: LLMSFULL existence checks accepted mixed-locale or non-canonical
  `Source:` rows, while generic URL validation accepted `mailto:` as a social
  image.
- Root cause: broad URL checks prove syntax classes, not corpus provenance or
  image semantics.
- Prevention: parse every Source row, bind the first and subsequent rows to
  the exact locale/origin/version, reject query/fragment delimiters and
  normalized duplicates, and forbid historical corpora. Validate `og:image`
  and `twitter:image` separately as HTTPS or safe local image targets that
  actually exist.

## Apply one browser-safe URL shape policy to every request surface

- Symptom: strict alias checks rejected external and protocol targets, but
  `https:///docs/...` still passed ordinary link, `srcset`, object/media, and
  CSS validation because Python parsed it as an HTTP URL with no authority and
  a local-looking path.
- Root cause: URL trust checks were attached to individual consumers. Python
  RFC parsing and browser WHATWG parsing disagree on malformed slash,
  backslash, whitespace, and authority forms, so a path-only check can
  authorize a browser request to another host.
- Prevention: validate URL shape before resolution and apply it to links,
  actions, meta refresh, active resources, every `srcset` candidate, object and
  media fields, inline styles, static CSS, action manifests, and artifact
  metadata. HTTP(S) always requires an authority; protocol-relative,
  backslash, whitespace/control, and ambiguous forms fail before origin or
  target checks. Artifact validation must invoke the complete rendered
  security scan, not assume a prior build-stage scan covers post-processing or
  downloaded artifacts.
