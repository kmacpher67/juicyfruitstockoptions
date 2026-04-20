#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-origin}"
BRANCH="${2:-main}"
TARGET_REF="${REMOTE}/${BRANCH}"

# Comma-separated patterns can be overridden per-run:
#   AUTO_OURS_PATTERNS="docs/**,xdivs/**,logs/**" ./scripts/git_pull_gamepc_guarded.sh
AUTO_OURS_CSV="${AUTO_OURS_PATTERNS:-docs/**,xdivs/**,logs/**,report-results/**,*.md,*.ics}"
IFS=',' read -r -a AUTO_OURS_PATTERNS_ARR <<< "$AUTO_OURS_CSV"

path_matches_any() {
  local path="$1"
  shift
  local pattern
  for pattern in "$@"; do
    if [[ -n "$pattern" && "$path" == $pattern ]]; then
      return 0
    fi
  done
  return 1
}

require_clean_merge_state() {
  if [[ -f .git/MERGE_HEAD ]]; then
    echo "A merge is already in progress. Resolve or abort it first (git merge --abort)." >&2
    exit 2
  fi
}

print_list() {
  local title="$1"
  shift
  echo "$title"
  local item
  for item in "$@"; do
    echo "  - $item"
  done
}

require_clean_merge_state

echo "Fetching ${TARGET_REF}..."
git fetch "$REMOTE" "$BRANCH"

if ! git rev-parse --verify -q "$TARGET_REF" >/dev/null; then
  echo "Remote ref not found: ${TARGET_REF}" >&2
  exit 2
fi

LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse "$TARGET_REF")"

if [[ "$LOCAL_HEAD" == "$REMOTE_HEAD" ]]; then
  echo "Already up to date with ${TARGET_REF}."
  exit 0
fi

if git merge-base --is-ancestor "$LOCAL_HEAD" "$REMOTE_HEAD"; then
  echo "Fast-forwarding to ${TARGET_REF}..."
  git merge --ff-only "$TARGET_REF"
  echo "Fast-forward complete."
  exit 0
fi

echo "Branches diverged. Starting guarded merge from ${TARGET_REF}..."
set +e
git merge --no-commit --no-ff "$TARGET_REF"
MERGE_EXIT=$?
set -e

if [[ $MERGE_EXIT -eq 0 ]]; then
  echo "Merge applied cleanly with no conflicts."
  echo "Review and finish with: git commit"
  exit 0
fi

mapfile -t CONFLICTED < <(git diff --name-only --diff-filter=U)
if [[ ${#CONFLICTED[@]} -eq 0 ]]; then
  echo "Merge returned conflicts but none were listed. Inspect manually with git status." >&2
  exit 1
fi

AUTO_RESOLVED=()
MANUAL_REVIEW=()

for file in "${CONFLICTED[@]}"; do
  if path_matches_any "$file" "${AUTO_OURS_PATTERNS_ARR[@]}"; then
    git checkout --ours -- "$file"
    git add "$file"
    AUTO_RESOLVED+=("$file")
  else
    MANUAL_REVIEW+=("$file")
  fi
done

if [[ ${#AUTO_RESOLVED[@]} -gt 0 ]]; then
  print_list "Auto-resolved by keeping this machine's version (ours):" "${AUTO_RESOLVED[@]}"
fi

if [[ ${#MANUAL_REVIEW[@]} -gt 0 ]]; then
  echo
  print_list "Needs manual review before commit:" "${MANUAL_REVIEW[@]}"
  echo
  echo "Next steps:"
  echo "  1) Open each file, resolve conflict markers"
  echo "  2) git add <resolved-files>"
  echo "  3) git status"
  echo "  4) git commit"
  exit 1
fi

echo
echo "All conflicts auto-resolved with ours for configured paths."
echo "Review and finish with: git commit"
