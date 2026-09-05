## Before → after

| Before | After |
| --- | --- |
| Three release entries were split across configuration and build behavior. | `versions.json` drives one immutable `latest / 1.7 / 1.5 / 1.3 / 1.0` release contract, including selectors, aliases, SEO, and aggregate metadata. |
| Summary search had no durable load-failure recovery path. | Native summary search remains primary and exposes distinct empty/error states with a stable keyboard-accessible retry. |
| No optional AI integration contract existed. | Kapa is disabled by default, locale-bound, and loaded only after an explicit click; timeout, late response, and retry remain isolated from native search. |
| CI mixed build and publication concerns. | Fixed event plans build immutable artifacts, revalidate the aggregate, run Chromium gates, and publish only to reviewed ASF targets with minimal permissions. |

## Main changes

- Add the shared OINK shell behavior for navigation, version/locale-scoped
  sidebar state, mobile isolation, focus restoration, theme, image zoom,
  Backlinks, and Blog copy-link behavior.
- Keep local summary search authoritative while adding an optional Search Tail
  + Floating Launcher Kapa adapter with privacy-safe click gating.
- Generate bilingual latest-only `llms-full.txt` files without adding them to
  historical releases or making Kapa a build dependency.
- Build five immutable releases and preserve production historical links from
  latest-only staging. A deterministic 195-page route map keeps users on the
  equivalent logical page when it exists and gives a locale-correct,
  one-time-explained Docs-root fallback when it does not.
- Replace the previous workflow with fixed production/staging plans,
  short-lived artifacts, aggregate/security validation, Node 24, Playwright,
  Chromium, and fixed ASF publication targets.
- Apply one fail-closed rendered-request policy to HTML, SVG, CSS, list-valued
  image attributes, runtime URLs, and authored content boundaries. Bootstrap
  control SVGs and shared historical assets remain local and version-complete.

## Ask AI direction

The selected design combines a contextual Search Tail with a restrained
Floating Launcher. It excludes a persistent side panel and the old red/pink
assistant treatment.

<img width="860" alt="Ask AI interaction direction comparison" src="https://github.com/user-attachments/assets/013cceaa-fd72-47cf-88ff-69224e0ce32b" />

Full decision record: https://github.com/apache/hugegraph-doc/issues/467#issuecomment-5541691334

## Validation

- `bash dist/validate-links.sh`
- `python3 -m unittest discover -s scripts -p 'test_*.py' -v` — 124 passed
- `node --test tests/ui-ai/*.test.cjs` — 23 passed
- `node --test tests/e2e/workflow-contract.test.cjs` — 6 passed
- Five-version production aggregate — 1,082 HTML, 3,528 published files,
  10 error documents; all 195 logical route entries pass exact
  forward/missing/reverse validation, including two explicit EN/CN renamed-page
  equivalence groups
- Latest-only ASF OINK staging aggregate — 276 HTML, 845 published files,
  2 error documents; every historical selector remains on the production
  origin
- Full ASF OINK staging aggregate — 1,082 HTML, 3,528 published files,
  10 error documents; current and historical routes remain on staging
- AI-enabled fixture — 276 HTML, 840 files
- EN/CN LLMSFULL — 87 canonical, unique, same-origin sources per locale;
  historical LLMSFULL outputs remain absent
- Historical social metadata — 1,530 matching OG/Twitter entries with all four
  version-scoped fallback images present; 59 static redirects are explicitly
  distinguished from content pages
- Blocking Chromium suite — 32 passed, 3 expected PR-B-only skips
- Advisory visual matrix — 8/8
- Authored-content boundary scan — ordinary, Print, and landing Print outputs
  retain balanced markers; media nesting and duplicate attributes fail closed
- Final integrated re-review — exactly 3 independent reviewers, 3/3 CLEAR

## Delivery boundaries

- Kapa remains disabled until the reviewed EN/CN source groups, staging corpus,
  CSP hosts, and live privacy/failure smoke checks pass.
- Community roster and content pilots remain isolated in PR-B.
- Full-content local search remains deferred and is tracked in #471.
