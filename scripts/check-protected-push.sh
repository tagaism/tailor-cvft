#!/usr/bin/env bash
# Refuse updates to main/master. Usage: check-protected-push.sh <branch>
set -euo pipefail

name="${1:-}"
if [[ -z "$name" ]]; then
  echo "protected-push: expected a branch name." >&2
  exit 1
fi
name="${name#refs/heads/}"

if [[ "$name" != "main" && "$name" != "master" ]]; then
  exit 0
fi

cat >&2 <<EOF
push: refusing to update '$name'

Do not push commits directly to main. Open a feature branch and a pull request:

  git checkout -b feat/your-change
  git push -u origin feat/your-change

Merge via the GitHub PR. Local hooks can be skipped with --no-verify;
GitHub branch protection is the real backstop.
EOF
exit 1
