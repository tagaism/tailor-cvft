#!/usr/bin/env bash
# Validate a commit message (Conventional Commits). Usage: check-commit-msg.sh <file>
set -euo pipefail

TYPES="feat|fix|docs|style|refactor|test|chore|perf|ci|build"
# feat: add lint hooks   fix(api)!: reject empty profile
SUBJECT_RE="^(${TYPES})(\([a-z0-9][a-z0-9._-]*\))?!?: [a-z].*$"

file="${1:-}"
if [[ -z "$file" || ! -f "$file" ]]; then
  echo "commit-msg: expected a message file." >&2
  exit 1
fi

# Drop comment lines Git leaves in the editor template (bash 3.2-safe).
subject=""
second=""
saw_subject=0
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" == \#* ]] && continue
  if [[ $saw_subject -eq 0 ]]; then
    subject="$line"
    saw_subject=1
    continue
  fi
  second="$line"
  break
done < "$file"
subject="${subject%"${subject##*[![:space:]]}"}"

if [[ -z "$subject" ]]; then
  echo "commit-msg: empty subject." >&2
  exit 1
fi

# Merges, reverts, and rebase autosquash are not authored as conventional commits.
if [[ "$subject" =~ ^Merge\  || "$subject" =~ ^Revert\  || "$subject" =~ ^(fixup|squash)! ]]; then
  exit 0
fi

if (( ${#subject} > 72 )); then
  echo "commit-msg: subject is ${#subject} characters (max 72)." >&2
  echo "  $subject" >&2
  exit 1
fi

if [[ "$subject" =~ \.$ ]]; then
  echo "commit-msg: do not end the subject with a period." >&2
  echo "  $subject" >&2
  exit 1
fi

if [[ ! "$subject" =~ $SUBJECT_RE ]]; then
  cat >&2 <<EOF
commit-msg: invalid subject

  $subject

Use Conventional Commits:

  <type>(optional-scope): imperative summary

  type: feat | fix | docs | style | refactor | test | chore | perf | ci | build
  summary: lowercase, imperative, no trailing period, subject ≤ 72 chars

  good:  feat: add multiple contacts to the profile
         fix(preview): delete certifications from the cv
         docs: document lint and git hooks
  bad:   Add linter checker for code syntax
         feat: Add Contacts.
         updated readme

Put detail in a body after a blank line, wrapped at 72 characters.
EOF
  exit 1
fi

if [[ -n "${second:-}" ]]; then
  echo "commit-msg: separate the body with a blank line after the subject." >&2
  exit 1
fi

exit 0
