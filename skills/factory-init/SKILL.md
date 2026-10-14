---
name: factory-init
description: Set up the software factory in the current repo — writes factory/config.md (filled in from the repo), the dashboard, the backlog, and the .gitignore entries that /factory needs. Use for "/factory-init" or when /factory says config.md is missing.
---

# Factory init

Prepare the current repo for `/factory`. The skill, scripts and agents come from the
plugin; this writes only the repo-specific files. **Do not commit anything** — the user
lands these through their own pull request.

Run from the repo's main checkout. Stop with a clear message if any of these fail:
`git rev-parse --show-toplevel`, an `origin` remote (`git remote get-url origin`),
`gh auth status`, `python3 --version`. If the default branch isn't `main`, say so — the
factory assumes `main`.

## Steps

1. **Inspect the repo** to learn how it is built and tested: `README`, `CLAUDE.md`,
   `package.json` / `pyproject.toml` / `Gemfile` / `Makefile` / `go.mod` / CI workflows.
   Find the install command, the typecheck / lint / test / build commands, any UI
   directories, and the risky areas (migrations, auth, secrets, deletes of data the app
   doesn't own).
2. **`factory/config.md`** — if it exists, show the user what you'd change and ask before
   overwriting. Otherwise copy `templates/config.md` (in this skill's directory) and fill in
   every section from step 1. Use real commands you've confirmed exist; leave a section's
   bullet empty (and say so) rather than guess.
3. **`factory/backlog.md`** — copy `templates/backlog.md` unless one exists.
4. **`factory/dashboard.html`** — copy `templates/dashboard.html` unless one exists.
5. **`.gitignore`** — append any of these that are missing, under a `# factory runtime state` comment:
   ```
   .claude/worktrees/
   factory/board.json
   factory/jobs/
   __pycache__/
   ```
6. Optionally ask whether to add a short *Feature workflow* paragraph to `CLAUDE.md`
   pointing at `/factory` — only if the user says yes.
7. **Tell the user**: which commands and sensitive areas you chose (so they can correct
   them in `factory/config.md`); that jobs branch from `origin/main`, so `factory/backlog.md`,
   `factory/dashboard.html`, `factory/config.md` and `.gitignore` are best merged to `main`
   via a PR before relying on them in a worktree; the dashboard runs with
   `cd factory && python3 -m http.server 8765` → http://localhost:8765/dashboard.html;
   and `/factory <feature>` starts the first job.
