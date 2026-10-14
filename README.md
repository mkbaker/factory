# factory

A small, visual software factory for Claude Code. Give it a feature or a GitHub issue; it
writes a spec, builds it test-first, runs parallel reviews, gates on an approver, and opens a
pull request. Every job runs in its own git worktree, so several run at once.

**The factory never commits to, pushes, or merges into `main`.** Every job ends as a PR; you merge.

Adapted from zazencodes' original factory prompt.

## Install

```
/plugin marketplace add mkbaker/factory
/plugin install factory@mkbaker
```

Then, in the repo you want a factory in:

```
/factory-init
```

`/factory-init` inspects the repo and writes `factory/config.md` (install/verify commands, UI
paths, sensitive areas, review focus), plus `factory/backlog.md`, `factory/dashboard.html` and
the `.gitignore` entries. Review `config.md`, and land those files through a PR.

Requires `git`, an authenticated `gh`, `python3`, an `origin` remote, and `main` as the base branch.

## The loop

```
feature → spec-writer → builder ⇄ [security · ux · ui · code] → approver → pull request | needs-human
```

| Agent | Model | Job |
|---|---|---|
| `spec-writer` | opus | request → `spec.md` with testable acceptance criteria |
| `builder` | opus | TDD on `factory/<job-id>`, commits, `build.md`; resumed each round |
| `security-reviewer` | opus | secrets, injection, validation, data the app doesn't own |
| `ux-reviewer` | sonnet | behaviour vs the spec as a user feels it |
| `ui-reviewer` | sonnet | design and accessibility — skipped if no UI paths changed |
| `code-reviewer` | sonnet | correctness, tests, conventions; runs the checks |
| `approver` | opus | re-verifies; APPROVE → PR, ESCALATE → needs-human |

Any `CHANGES` resumes the same builder (max 2 rework rounds). A round only completes when
every reviewer's file exists.

## Commands

```
/factory <feature>               run a new job
/factory #<n>                    run a job from GitHub issue n (the PR closes it)
/factory next [n]                start the next n READY items (backlog first, then `factory`-labelled issues)
/factory approve <job-id>        for needs-human jobs: record a human approval and open the PR
/factory rework <job-id> <note>  send a needs-human or PR'd job back to the builder
/factory resume <job-id>         continue a job whose orchestrator session died
```

Dependencies are respected: a backlog line saying `depends on #74`, an issue body line
starting `Depends on #74`, or GitHub's native "blocked by" holds the item until that work's PR
is merged.

## Dashboard

```
cd factory && python3 -m http.server 8765
```

Open http://localhost:8765/dashboard.html — jobs move across the stages, reviewer chips fill
in per round, needs-human jobs are highlighted with a copy-the-approve-command button, and
each card opens a drawer with the job's markdown files.

## What lives where

In this plugin: `skills/factory` (orchestrator, `board.py`, `ready.py`), `skills/factory-init`
(+ templates), `agents/`. In your repo: `factory/config.md`, `backlog.md`, `dashboard.html`
(committed); `factory/board.json`, `factory/jobs/`, `.claude/worktrees/` (gitignored runtime state).

Agents are namespaced `factory:<name>` (e.g. `factory:builder`) and read your repo's
`factory/config.md` by absolute path, so improving the plugin updates every repo.
