# Contributing

Enable the repo hooks once (lint + these checks):

```bash
git config core.hooksPath .githooks
```

`git commit` validates the message. `git push` validates the branch name, then runs `./scripts/lint.sh`. Bypass with `--no-verify` only if you must.

## Branch names

```text
<type>/<short-kebab-description>
```

| Type | Use for |
| --- | --- |
| `feat` | A user-facing capability |
| `fix` | A bug fix |
| `docs` | README, comments, screenshots |
| `style` | Formatting only |
| `refactor` | Change structure, not behaviour |
| `test` | Tests |
| `chore` | Tooling, deps, chores |
| `perf` | Performance |
| `ci` | CI / hooks |
| `build` | Docker / build |

Rules:

- Lowercase `type` and slug
- Hyphens between words, digits allowed (`fix/404-for-missing-page`)
- No spaces, underscores, or camelCase
- `main` is protected; do not develop on it
- GitHub revert branches (`revert-12-feat/...`) are allowed

```text
good   feat/multiple-contacts
       fix/404-for-missing-page
       docs/readme-screenshots
bad    feaat/make-url-clickable
       Feature/Contacts
       feat/Add_Lint
```

Rename a local branch:

```bash
git branch -m feat/your-change
```

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(optional-scope): imperative summary

Optional body after a blank line, wrapped at 72 characters.
```

Same `type` values as branches. Optional `scope` is a lowercase area (`api`, `preview`, `profile`). Append `!` after the type or scope for a breaking change (`feat(api)!: ...`).

Rules for the subject (first line):

- Imperative, present tense (“add”, not “added” or “adds”)
- Starts with a lowercase letter after the colon
- No trailing period
- 72 characters or fewer
- Describe *what* changed; *why* goes in the body

```text
good   feat: add multiple contacts to the profile
       fix(preview): delete certifications from the cv
       docs: document lint and git hooks
bad    Add linter checker for code syntax
       feat: Add Contacts.
       updated readme
```

Merge, revert, `fixup!`, and `squash!` subjects are left as Git writes them.
