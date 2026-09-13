#!/bin/sh
# Keep .goal-task/oink-site-improvements identical on every active OINK
# handoff branch in the org repository.
#
#   sh .goal-task/oink-site-improvements/sync-branches.sh check
#       Fetch every branch and report whose goal-task state differs from
#       HEAD, and which branch holds the newest goal-task commit. Run this
#       before resuming work; if another branch is newer, run `pull`.
#   sh .goal-task/oink-site-improvements/sync-branches.sh pull <branch>
#       Replace HEAD's goal-task directory with the one on <branch> and
#       commit it locally (goal-task files only).
#   sh .goal-task/oink-site-improvements/sync-branches.sh push
#       Copy HEAD's committed goal-task directory onto every other branch
#       as a goal-task-only commit and push it. Refuses when a target holds
#       a newer goal-task commit than HEAD, so no agent overwrites another
#       agent's state. Pushes are fast-forward only; rerun on rejection.
#
# Only the goal-task directory ever moves between branches; product code
# stays on its own branch. Add a new branch to BRANCHES when it is created.
# HANDOFF_REMOTE may be a remote name or URL.
set -eu

BRANCHES="handoff/oink-site-improvements feat/oink-download-asf"
DIR=.goal-task/oink-site-improvements
REMOTE=${HANDOFF_REMOTE:-https://github.com/hugegraph/hugegraph-doc.git}

cd "$(git rev-parse --show-toplevel)"

fetch() {
  for b in $BRANCHES; do
    git fetch -q "$REMOTE" "+refs/heads/${b}:refs/handoff-sync/${b}"
  done
}

last_goal_commit_time() {
  git log -1 --format=%ct "$1" -- "$DIR"
}

# Drop the goal-task entries from the index named by GIT_INDEX_FILE (or the
# default index) without consulting the working tree.
drop_goal_entries() {
  git ls-files -z -- "$DIR" | xargs -0 git update-index --force-remove --
}

current_branch=$(git rev-parse --abbrev-ref HEAD)
mode=${1:-check}

case "$mode" in
  check)
    fetch
    head_tree=$(git rev-parse "HEAD:${DIR}")
    head_time=$(last_goal_commit_time HEAD)
    newest=HEAD
    newest_time=$head_time
    for b in $BRANCHES; do
      ref="refs/handoff-sync/${b}"
      tree=$(git rev-parse "${ref}:${DIR}")
      time=$(last_goal_commit_time "$ref")
      if [ "$tree" = "$head_tree" ]; then state=identical; else state=DIFFERS; fi
      printf '%-36s %s %s last goal-task commit %s\n' "$b" \
        "$(git rev-parse --short "$ref")" "$state" "$(git log -1 --format=%cI "$ref" -- "$DIR")"
      if [ "$time" -gt "$newest_time" ]; then newest=$b; newest_time=$time; fi
    done
    if [ "$newest" = HEAD ]; then
      echo "HEAD (${current_branch}) holds the newest goal-task state."
    else
      echo "Newer goal-task state is on ${newest}; run: sh ${DIR}/sync-branches.sh pull ${newest}"
    fi
    ;;
  pull)
    source_branch=${2:?usage: sync-branches.sh pull <branch>}
    fetch
    drop_goal_entries
    git read-tree --prefix="${DIR}/" "refs/handoff-sync/${source_branch}:${DIR}"
    git checkout -- "$DIR"
    if git diff --cached --quiet -- "$DIR"; then
      echo "Goal-task state already matches ${source_branch}."
    else
      tree=$(git write-tree)
      commit=$(printf 'docs(goal): sync goal-task state from %s\n' "$source_branch" \
        | git commit-tree "$tree" -p HEAD)
      git update-ref "refs/heads/${current_branch}" "$commit"
      echo "Committed ${commit} with goal-task state from ${source_branch}."
    fi
    ;;
  push)
    fetch
    if ! git diff --quiet HEAD -- "$DIR" || ! git diff --cached --quiet -- "$DIR"; then
      echo "Commit goal-task changes before pushing them to other branches." >&2
      exit 1
    fi
    head_tree=$(git rev-parse "HEAD:${DIR}")
    head_time=$(last_goal_commit_time HEAD)
    for b in $BRANCHES; do
      [ "$b" = "$current_branch" ] && continue
      ref="refs/handoff-sync/${b}"
      if [ "$(git rev-parse "${ref}:${DIR}")" = "$head_tree" ]; then
        echo "${b}: already identical"
        continue
      fi
      if [ "$(last_goal_commit_time "$ref")" -gt "$head_time" ]; then
        echo "${b}: holds newer goal-task state; run pull ${b} first" >&2
        exit 1
      fi
      index=$(mktemp)
      tree=$(
        GIT_INDEX_FILE=$index
        export GIT_INDEX_FILE
        git read-tree "$ref"
        drop_goal_entries
        git read-tree --prefix="${DIR}/" "HEAD:${DIR}"
        git write-tree
      )
      rm -f "$index"
      commit=$(printf 'docs(goal): sync goal-task state from %s\n' "$current_branch" \
        | git commit-tree "$tree" -p "$ref")
      git push "$REMOTE" "${commit}:refs/heads/${b}"
      echo "${b}: pushed ${commit}"
    done
    ;;
  *)
    echo "usage: sync-branches.sh check | pull <branch> | push" >&2
    exit 2
    ;;
esac
