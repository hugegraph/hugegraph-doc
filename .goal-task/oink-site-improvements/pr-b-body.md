## Before → after

| Before | After |
| --- | --- |
| Community did not expose the ASF HugeGraph project roster. | One reviewed data bundle renders 12 PMC members and 10 Committers consistently in HTML, Print, and Markdown. |
| Member identity presentation could require browser-side lookups. | The page performs zero visitor-side roster requests; the confirmed empty GitHub mapping uses deterministic initials and ASF phonebook links. |
| Core documentation entry queries relied only on body text. | Restrained metadata for 12 bilingual entry groups places all 24 fixed queries in the Top 3 of the real OINK summary search. |
| Confirmed OINK content primitives were not exercised in product documentation. | Three latest-only bilingual page groups pilot steps, command/file controls, field anchors, wide tables, and request/response blocks. |

## Main changes

- Add a deterministic ASF roster refresh/validation pipeline using the public
  committee, LDAP project, and LDAP people datasets.
- Preserve the last-good roster atomically: install and validate candidate
  images first, replace the data bundle last, then clean orphaned assets.
- Render Project members after participation guidance with a 5/3/2 responsive
  grid and same-origin 128×128 WebP assets.
- Keep GitHub mappings empty for this delivery. No identity is inferred from a
  name, email address, organization membership, or commit history.
- Add bounded search metadata only to the 12 agreed EN/CN entry groups.
- Apply native OINK content components only to the three agreed bilingual
  latest-page pilots.

## Validation

- Offline roster and rendering contracts: 35 passed
- Combined Python suite: 112 passed
- Actual OINK search ranking: 24/24 fixed queries in the Top 3
- Community HTML/Print/Markdown parity: 12 PMC + 10 Committers
- Responsive grid: 5 columns at 1440px, 3 at 900px, 2 at 390/320px
- Integrated Node/Chromium gate: 49/49
- Integrated five-version aggregate: 1,082 HTML, 3,414 files,
  10 error documents
- Advisory visual capture: 8/8

## Dependency

This change is intentionally isolated from the shared shell, versioning,
workflow, and test workspace owned by #472. It will be rebased onto the merged
PR-A baseline before final merge.

Closes #468
