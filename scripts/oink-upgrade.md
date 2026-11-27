# OINK upgrade SOP

OINK is the sole theme module. `go.mod` / `go.sum` pin the release and both checksums; `toolchain.json` pins Hugo and Go for local and CI builds.
Latest and every archived release use the current shell and the same theme locks. Keep HugeGraph branding and behavior in configuration, data, hooks
and public OINK APIs. Do not edit the module cache, vendor a fork, copy native runtimes, or run `go mod tidy`: this site has no Go imports, so `tidy`
can remove the theme requirement.

## Start an upgrade

Read the target's [release notes](https://github.com/pgsty/oink/releases) and [upgrade guidance](https://oink.pgsty.com/zh/docs/admin/upgrade/).
Use a clean independent branch, Python 3.13+, the tools pinned in `toolchain.json`, WebP's `cwebp` / `dwebp`, and Node as required by
`tests/e2e/package.json`. Node is only for browser tests; native CSS needs neither Sass nor a site-build npm dependency.

```sh
# Replace vX.Y.Z with an explicit published release.
scripts/update-oink.sh vX.Y.Z
```

The printed work directory holds all evidence and recovery information. To choose a durable location outside every Git checkout, including enclosing
or linked checkouts, use `--work-dir /path/to/upgrade-evidence`. Network access is needed for Go modules, archived content, npm and Playwright browsers; ports 4173–4175
must be free. `HUGO_BIN`, `GO_BIN` and `PYTHON_BIN` may select task-local executables.

If the previous release requires an older Hugo, set `BEFORE_HUGO_BIN=/path/to/previous/hugo`. This affects only the original checkout's baseline
build, which uses its own build wrapper. The target still uses the pinned current toolchain. The report records both versions; a toolchain change is
part of the measured migration and must not be described as a theme-only benchmark.

When the target requires newer tools, preflight stops before changing locks. Update `toolchain.json`, run
`python3 scripts/site_toolchain.py --sync`, install those versions, and retry. `--check` verifies the derived Go and legacy Netlify settings. Never
lower the upstream minimum to make preflight pass. Production Hugo warnings are blocking; do not hide them through `ignoreLogs` or disable strict checks.

## Automatic steps and review

1. Validate the target release, published module metadata, exact local toolchain and native CSS build, without changing the current locks.
2. Preserve the first lock/inventory backup and original commit; build it in an isolated detached worktree with an empty Hugo cache.
3. Capture representative real desktop/mobile pages, bilingual search timing samples, generated JS/CSS/index bytes and build duration.
4. Upgrade the exact dependency, prune only stale OINK checksums, verify Hugo's published module graph, and compare upstream interfaces.
5. Run the selected validation level and produce Before/After evidence and a concise report; real build/test failures stop immediately.
6. Review reported upstream impacts against that evidence before accepting the baseline. Compare old/target upstream files and the HugeGraph integration;
   adapt only affected behavior, then resume with the same directory.

```sh
# During compatibility work: latest build, source/link checks, search ranking,
# representative captures and search measurements. Does not accept the baseline.
scripts/update-oink.sh vX.Y.Z --resume --accept-reviewed --mode quick --work-dir /path/to/upgrade-evidence

# Final local acceptance: complete version, AI, browser and visual gates.
scripts/update-oink.sh vX.Y.Z --resume --accept-reviewed --mode full --work-dir /path/to/upgrade-evidence
```

`--accept-reviewed` acknowledges an actual compatibility review; it does not bypass tests. Agents may perform the review as authorized by the task.
The default run collects evidence before asking for review acknowledgement. Upstream hash changes alone do not force local edits.
Quick success never updates `scripts/oink-overrides.json`. Only successful full validation advances that inventory. A same-version run validates further
fixes; an incremental patch upgrade starts a fresh directory so the previous accepted release becomes its baseline.

The Shell entry point remains intentionally thin. Python owns orchestration and reports, using the standard library and the existing validators,
version cache and parallel build runner. Local and CI checks use the same commands; privileged CI job boundaries remain separate.

## Evidence and failure recovery

| Evidence | Meaning |
| --- | --- |
| `report.md`, `review.json` | Current status, review impacts, command results, durations, comparison and exact recovery/resume commands |
| `logs/` | Per-command combined stdout/stderr, including failed commands and actual historical cache outcomes |
| `before/`, `after/` | Real page captures; `before/` also retains the first lock/inventory backup |
| `before-metrics.json`, `after-metrics.json` | Latest-only artifact bytes, estimated gzip bytes, build duration and actual tool versions |
| `before-browser/`, `after-browser/` | Raw cold/warm bilingual search samples and summaries from the same browser harness |
| `before-source/`, `baseline-site/` | Original detached checkout and its built site; the original commit never follows later edits |
| `build-plan.json`, `artifacts/`, `site/` | Cache eligibility, individually validated versions and their validated aggregate |

Generated asset totals include all emitted JS/CSS files, not initial-page transfer. Estimated gzip sizes do not claim CDN compression behavior. Build
numbers are single observations from isolated empty Hugo caches; repeat them if making a performance claim. Browser timing samples carry their query,
language, browser and run conditions. Keep upstream headline numbers separate from HugeGraph measurements.

Failures retain the evidence and local adaptations. Fix the reported problem and reuse the original `--work-dir` with `--resume`. If baseline capture
failed before dependency mutation, resume accepts only the original unchanged locks. Never relabel a partially upgraded page as the Before capture.
If Go updated the target pin but was interrupted before writing its checksums, the matching original transaction reruns the exact target `go get`
and then applies the same strict checksum and module-graph verification. A fresh resume directory or same-version backup cannot authorize that repair;
use the original transaction or restore its locks. Writable artifact paths must not be symbolic links, including when resuming.
The updater does not automatically revert code, commit, push or publish.

A task-local installed Chromium can be selected with `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`. Full acceptance still requires the Firefox/WebKit checks;
unavailable browsers are a failed prerequisite, not a skip that counts as a pass. CI installs the pinned Playwright browsers.

## Compatibility review map

| Integration | Local entry | Required evidence |
| --- | --- | --- |
| Native CSS and branding | `assets/css/project*`, CSS bundle hooks, `data/`, `i18n/` | Four reader presets, light/dark, responsive and Print; no retired Sass hooks or CSP data-URL regression |
| Navigation and keyboard behavior | `navbar.html`, `footer.html`, shell hooks | Native overflow/version menus, mobile utilities and keyboard focus; no removed Bootstrap JS dependency |
| Full-text and field search | Site search config, `.fields`, field anchors | All existing ranking cases, split/body indexes, lazy loading and exact parameter destinations |
| Page actions and Duo View | `actions/manifest.html`, compare public interfaces | Page-scoped real translation availability, lazy panes, mobile tabs and history |
| Historical shell and languages | `language-preference.js`, `hugegraph-shell.js`, version partials | Existing URLs, language/version navigation, no duplicate controllers |
| Kapa and consent | `kapa-adapter.js`, body/footer hooks | No AI request before consent or when disabled; no duplicate widget inside comparison panes |
| SEO and content outputs | Alternates, content/Print/Markdown hooks | Canonical/hreflang, real translations, RSS/Print/Markdown isolation and readable component fallbacks |
| Archive assembly and caches | `versioning.py`, `version_cache.py`, `versions.json` | Every configured release, valid digests and toolchain/theme invalidation; restored artifacts revalidated |

The inventory stores upstream hashes, not copied sources. It watches matching local overrides, CSS selectors and the search/fields/navigation/appearance/
comparison interfaces. Additions, removals and changes require review. Unchanged hashes alone do not prove interaction compatibility. Prefer deleting
redundant overrides when the target's native implementation meets the site's requirements.

Use `.fields` only for real parameter definitions where stable anchors and layout improve navigation. Preserve explicit public IDs. Keep ordinary tables
compact and avoid bulk conversion of archived parameter tables. Check current and archived content against shared CSS changes.

## Duo View contracts

Keep `params.ui.compare: true` and Slate as the default reader preset. Native OINK discovers real same-origin HTML translations in Docs, Book and Blog,
providing the page button, Command Palette action, `B` shortcut, Sync Scroll, lazy loading, mobile tabs, history and retry behavior. Do not add a second
comparison controller or route map. HugeGraph has bilingual Docs and Blog content; test Book when real translated Book pages exist.

| Content | English | Chinese |
| --- | --- | --- |
| Latest Docs | `/docs/…` | `/cn/docs/…` |
| Each archived release in `versions.json` | `/versions/<id>/docs/…` | `/versions/<id>/cn/docs/…` |
| Blog shared by every release shell | `/blog/…` | `/cn/blog/…` |

Check entry from both languages. Native desktop panes and mobile tabs must remain readable. Missing/draft/non-HTML translations must not expose an entry;
Print, Markdown and RSS must not carry the reader. Sync Scroll may align approximately when headings differ; improve important shared IDs where evidence
shows poor alignment instead of rewriting the content tree.

An iframe is an ordinary same-origin page. Keep article runtimes such as tables, diagrams, images and code active, while suppressing the top-level shell,
language preference and Kapa initialization inside `window.OinkComparePane`. Before opening, neither the second document nor its reader runtime should load.

## Full acceptance and cache behavior

Full mode runs source/link tests, a fresh strict latest build, every configured version, aggregate/output validation, both AI modes, the complete Chromium
regression suite, Firefox/WebKit compatibility checks, visual checks and measured search samples. A temporary oversized Markdown fixture also exercises
native index splitting, Save-Data and failed-body retry;
these fixture checks do not claim a production performance benefit. This includes the original search-ranking requirements,
field destinations, four themes, mobile layouts, native components, keyboard behavior, Kapa/consent and ASF CSP. Review representative Before/After images
and a short interaction GIF; keep the full captures as diagnostic evidence rather than putting every screenshot into a PR.

Latest always rebuilds. Historical caches require matching source, shared shell, theme lock, Hugo/Go/WebP versions, origins, year fingerprints and file
digests. Every restored artifact is validated again; invalid receipts/artifacts rebuild. Resume reuses only this existing validated cache path. Quick mode
cannot certify missing historical or browser checks. Have an independent agent review the final combined diff for correctness, security, performance,
compatibility, native reuse and unnecessary complexity.

Release checks clear preview replacements/themes, set `GOWORK=off` and `HUGO_MODULE_WORKSPACE=off`, reject `_vendor`, and verify the Hugo graph. A correct
`go.mod` alone does not prove the rendered site used that module.

## ASF Staging and publication

Open non-Draft ORG and ASF PRs from the same branch. PR approval or a local full pass is not an ASF Staging pass. The trusted workflow on ASF `master`
selects an immutable candidate commit and reads its validated toolchain manifest as data; do not run candidate-controlled setup scripts with publication
credentials. Use the workflow's staging operation after the necessary trusted workflow changes are available on ASF `master`.

```text
operation: staging-next
scope: full
candidate_branch: <candidate branch available in the ASF repository>
confirmation: publish asf-staging-oink
```

Staging must wait for E2E success. Record the candidate SHA and workflow run; inspect the real staged origin's bilingual/version routes, same-origin iframe
policy, canonical/hreflang, search, native components, Kapa consent, Print/RSS/Markdown and responsive captures. Changes to the trusted workflow may need a
separate reviewed preparation step before it can build the new candidate. Do not work around that boundary by executing the candidate's publisher.

Production is a separately authorized operation after Staging evidence is accepted. This upgrade command does not dispatch production, write `asf-site`
or merge PRs. `netlify.toml` remains a derived legacy-preview configuration, not another release authority.

## Rollback and cleanup

Revert the complete focused upgrade commit/series, including locks, toolchain, compatibility changes and reviewed inventory. Do not reset unrelated work or
only downgrade the theme lock under newer incompatible overrides. Validate the reverted release with its matching tools, rebuild all configured versions,
and compare Staging with retained Before evidence. Production rollback uses the same explicit release authorization; never patch generated output by hand.

For uncommitted recovery, inspect `review.json`'s exact recovery command: it restores only the first lock/inventory backup and retains adaptations. Toolchain
and source edits need their own focused restore/revert. A fresh `--resume` backup may already pin the target, which the report explicitly records.

Keep evidence through acceptance. When it is no longer needed, remove the detached baseline with `git worktree remove /path/to/upgrade-evidence/before-source`
before deleting the external work directory. Retain release/rollback commit IDs and workflow links in the PR or upgrade report.
