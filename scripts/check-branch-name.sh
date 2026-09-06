#!/usr/bin/env bash
# Validate a Git branch name. Usage: check-branch-name.sh [branch]
set -euo pipefail

TYPES="feat|fix|docs|style|refactor|test|chore|perf|ci|build"
# feat/add-lint-hooks   fix/404-page   revert-11-feat/add-projects-to-profile
BRANCH_RE="^(${TYPES})/[a-z0-9]+([.-][a-z0-9]+)*$"
REVERT_RE="^revert-[0-9]+-.+"
PROTECTED_RE="^(main|master)$"

name="${1:-}"
if [[ -z "$name" ]]; then
  name="$(git branch --show-current 2>/dev/null || true)"
fi
if [[ -z "$name" ]]; then
  echo "branch: not on a named branch (detached HEAD is ok)." >&2
  exit 0
fi

if [[ "$name" =~ $PROTECTED_RE ]]; then
  exit 0
fi
if [[ "$name" =~ $BRANCH_RE || "$name" =~ $REVERT_RE ]]; then
  exit 0
fi

cat >&2 <<EOF
branch: invalid name '$name'

Use: <type>/<short-kebab-description>

  type: feat | fix | docs | style | refactor | test | chore | perf | ci | build
  slug: lowercase letters, digits, hyphens (dots allowed)

  good:  feat/multiple-contacts
         fix/404-for-missing-page
         docs/readme-screenshots
         refactor/remove-legacy-frontend
  bad:   feaat/make-url-clickable
         Feature/Contacts
         feat/Add_Lint

GitHub revert branches (revert-12-feat/...) are allowed.
Rename:  git branch -m feat/your-change
EOF
exit 1
