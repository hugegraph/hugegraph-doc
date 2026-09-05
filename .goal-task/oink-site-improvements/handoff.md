# OINK Site Improvements — Cross-host Handoff

This file is the portable entrypoint for continuing the OINK site-improvement
goal on another host. Read files in this order:

1. `design.md` — authoritative product, interface, release, and acceptance
   requirements.
2. `state.md` — execution contract, exact checkpoints, decisions, and gates.
3. `todo.md` — current work queue, dependencies, waits, and deferrals.
4. `lessons.md` — failure-derived constraints that must not regress.
5. `pr-a-body.md` and `pr-b-body.md` — prepared GitHub descriptions.
6. `evidence/` — retained design and browser screenshots.

## Remote checkpoint

- Repository: `https://github.com/apache/hugegraph-doc.git`
- Baseline `master`: `d88167dd797efafea50cec59909d57849703fde5`
- PR-A branch: `feat/oink-core-platform`
- PR-A exact head: `25f3e8c3f7982cbf1d08c4bda572e9da9add79eb`
- PR-A: <https://github.com/apache/hugegraph-doc/pull/472>
- PR-A CI run: <https://github.com/apache/hugegraph-doc/actions/runs/33934549197>
  — all jobs passed; required human review is still pending.
- PR-B branch: `feat/oink-community-content`
- PR-B exact head: `bb270838626165ad2c98c11150dde39f4eb113c9`
- PR-B has no PR yet. Create it with `Closes #468` only after rechecking the
  current PR-A/base state.
- Local integration checkpoint:
  `81092317458740eeaf9da8b289cb0ea7f226aaf2`. Its tree was verified
  byte-identical to the union of the two pushed branch heads and contains no
  unique unpushed implementation.

All remote revisions and GitHub states are time-sensitive. Refresh them before
any mutation:

```bash
git fetch origin --prune
git ls-remote origin \
  refs/heads/master \
  refs/heads/feat/oink-core-platform \
  refs/heads/feat/oink-community-content
gh pr view 472 --repo apache/hugegraph-doc \
  --json state,isDraft,headRefOid,mergeStateStatus,reviewDecision,statusCheckRollup,url
gh pr list --repo apache/hugegraph-doc \
  --head feat/oink-community-content --state all
```

## New-host bootstrap

The destination host needs:

- an `apache/hugegraph-doc` clone with `origin` pointing to the Apache
  repository;
- GitHub authentication capable of reading CI and, before writes, confirmed
  Apache branch/PR permission;
- repository submodules and the Node/Hugo/Python/Chromium dependencies used by
  the current source;
- Kapa login only when the reviewed staging LLMSFULL corpus is reachable.

Suggested worktrees:

```bash
git worktree add ../hgdoc-oink-pra origin/feat/oink-core-platform
git worktree add ../hgdoc-oink-prb origin/feat/oink-community-content
```

Recreate the integration worktree from refreshed remote heads instead of
copying the source-host worktree. Preserve PR-A and PR-B ownership boundaries
defined in `state.md`.

## First continuation action

1. Recheck PR #472 exact-head CI and required review.
2. Merge PR-A only when branch protection permits it, with no override.
3. Refresh `origin/master`.
4. Create PR-B from the already-pushed branch with `Closes #468`.
5. Continue independent staging/Kapa preparation while review is pending.
6. Begin PR-C only after the first-phase stability gate in `design.md` is met.

The final integrated broad review already reached the user-approved three-round
cap and finished 3/3 clear. Do not start another broad review cycle. Only a new,
reproducible release-blocking Critical may receive a narrowly scoped fourth or
fifth round.

## Source-host-only evidence

Absolute paths under `/Users/zhu/...` and `/private/tmp/...` in `state.md` are
historical source-host evidence locations. They are not portable and must not be
treated as existing on the destination host. The committed screenshots under
`evidence/`, exact pushed commits, GitHub CI, and a fresh destination-host
validation are the portable evidence.

No credential values are stored in this directory. The Kapa integration ID is a
public browser identifier; authenticated browser sessions and cookies are not
portable and must be re-established on the destination host if needed.
