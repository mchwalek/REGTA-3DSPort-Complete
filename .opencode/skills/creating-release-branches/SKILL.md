---
name: creating-release-branches
description: Use when asked to cut or create a release branch, bundle open PRs into a release, or merge open PRs into a release branch for the REGTA 3DS port.
---

# Creating release branches

A release branch is a **local** branch made from an up-to-date `main` that
bundles every open PR so they can be built and tested together. It stays
local: never push it, and never open a PR from it to `main`. The PRs
themselves stay open and untouched on GitHub.

## Steps

1. `git status --short`. Stop and ask if there are uncommitted changes.
2. `git checkout main && git pull --ff-only origin main`.
3. `git checkout -b release/YYYY-MM-DD` (today's date). If it exists, add
   `-2`, `-3`, ... The `relcs-YYYYMMDD-HHMMSS` tags are build snapshots, not
   releases.
4. List open PRs against the fork, not upstream (`gh` may default to
   `Epic0522/...` without `--repo`):
   ```sh
   gh pr list --repo mchwalek/REGTA-3DSPort-Complete --state open --base main \
     --json number,headRefName,title
   ```
5. In ascending PR number order, `git fetch origin <headRefName>` then
   `git merge --no-ff --no-edit origin/<headRefName>`. On a conflict,
   `git merge --abort` and report which PRs collide. Never resolve it
   silently.
6. Verify:
   ```sh
   python3 -m unittest discover -s scripts/tests -p 'test_*.py'
   scripts/verify-layout.sh
   ```
   Build with `scripts/build.sh relcs` if asked (see `relcs-3ds-build`).
7. Report the branch name, each merged PR (number, branch, title), and the
   verification results.

## Common mistakes

| Mistake | Instead |
|---|---|
| Pushing the release branch or opening a PR to `main` | Keep it local |
| Merging or closing the PRs on GitHub | Leave them open |
| `gh pr list` without `--repo` | Always pass the fork |
| Squash or fast-forward merges | `--no-ff`, so each PR stays visible |
| `git add -A` while fixing anything | Never (AGENTS.md landmine #1) |
