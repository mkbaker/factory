---
name: factory
description: Run the software factory — take a feature through spec → build → 4 parallel reviews → approval → pull request, each job in its own git worktree so several run at once, tracked on factory/board.json. Use for "/factory <feature>", "/factory #<issue>", "/factory next [n]", "/factory approve <job-id>", "/factory rework <job-id> <note>", "/factory resume <job-id>".
---

# Factory

You are the **orchestrator**. You run the loop below, spawn every agent, and are the
only one who updates the board (always through `board.py`). Agents get their context
from files, never from this conversation, and each writes only its own file.

```
feature → spec-writer → builder ⇄ [security · ux · ui · code] → approver → pull request | needs-human
```

**Nothing is ever committed to or merged into `main` by the factory.** Every job ends
as a pull request against `main`; the user merges on GitHub.

## Setup

- `SKILL_DIR` is this skill's base directory (shown when the skill loads); `board.py` and
  `ready.py` live there.
- `CONFIG` is `ROOT/factory/config.md`, written by `/factory-init`. If it is missing, tell
  the user to run `/factory-init` and stop. Read it for the **install commands** (run when
  creating a worktree) and the **UI paths** (for the path-gated `ui` reviewer). Agents read
  the rest of it (verify commands, sensitive areas, repo context) themselves — always give
  them its absolute path.
- Requires `git`, `gh` (authenticated), `python3`, an `origin` remote, and `main` as the base branch.

## Files

Paths are relative to the **main checkout** (`ROOT` — the parent directory of
`git rev-parse --path-format=absolute --git-common-dir`), even if this session runs in a
worktree. Give agents absolute paths.

```
factory/board.json                     # via board.py only; dashboard.html polls it
factory/backlog.md                     # "- [ ] feature" lines for /factory next
.claude/worktrees/<job-id>/            # the job's git worktree, on branch factory/<job-id>
factory/jobs/<job-id>/issue.md         # you — the GitHub issue, when the job came from one
factory/jobs/<job-id>/spec.md          # spec-writer
factory/jobs/<job-id>/build.md         # builder
factory/jobs/<job-id>/round-<n>/review-<reviewer>.md   # one per reviewer
factory/jobs/<job-id>/decision.md      # approver
factory/jobs/<job-id>/pr.md            # you — the PR description
```

`factory/board.json`, `factory/jobs/`, and `.claude/worktrees/` are gitignored runtime
state.

## Worktrees

Every job lives in its own worktree, so jobs never share a working tree and the main
checkout is never switched: it can sit on any branch, with the user's own edits, while
jobs run. The builder commits in the job's worktree; reviewers and the approver read it.

- **Create** (new job): from `ROOT`,
  ```
  git fetch origin
  git worktree add --no-track -b factory/<id> .claude/worktrees/<id> origin/main
  <each install command from config.md, run inside .claude/worktrees/<id>>
  ```
  Spawn the spec-writer as soon as `worktree add` returns, and run the install(s) while
  it works — the builder needs them, the spec-writer doesn't.
- **Ensure** (approve, rework, resume): if `.claude/worktrees/<id>` is missing, recreate
  it from the existing branch with `git worktree add .claude/worktrees/<id> factory/<id>`
  plus the install(s), and `board.py set <id> '{"worktree": ".claude/worktrees/<id>"}'`.
  If git says the branch is already checked out elsewhere (e.g. the main checkout, from
  before worktrees), stop and ask the user to switch that checkout off it.
- **Remove** (job merged): `git worktree remove .claude/worktrees/<id>` then
  `git branch -D factory/<id>`. If git refuses because the worktree has changes, leave
  it and tell the user.

Jobs branch from `origin/main`, and every diff is against `origin/main`, so the local
`main` branch is never needed.

## Running several jobs

Each job is an independent state machine in its own worktree. While one job's agents
run in the background you can start another (`/factory <feature>` again, or
`/factory next 3`), and other Claude sessions can run jobs too — `board.py` locks every
write. When an agent finishes, its name tells you the job (every agent name ends in the
job id): read that job's board entry and files, advance only that job, and never make
one job wait on another. A job is driven by exactly one orchestrator; to pick up a job
whose session is gone, use `/factory resume`.

Parallel jobs that touch the same files can conflict once one of them merges. Fix that
with `/factory rework <id> merge origin/main and resolve the conflicts`.

## Settings

- Reviewers: `security`, `ux`, `ui`, `code` (agents `security-reviewer`, `ux-reviewer`, `ui-reviewer`, `code-reviewer`).
- Path-gated reviewers: `ui` only runs when the branch changes one of the UI paths in config.md. Otherwise it is skipped (see the round loop).
- `MAX_REWORK = 2` — the builder is resumed at most twice for reviewer CHANGES (so at most 3 review rounds).

## Board

Change the board only with `python3 $SKILL_DIR/board.py` (from any checkout):

```
board.py new <slug> "<request>" [--issue <url>]   # creates the job + its folder, prints the id
board.py set <id> '{"stage": "build"}'            # merge top-level fields
board.py review <id> <reviewer> <verdict>         # one chip
board.py round <id> <reviewer>...                 # push reviews to history, round += 1,
                                                  # all listed reviewers pending, make round-<n>/; prints n
board.py get [<id>]                               # read
```

Never edit `board.json` by hand. `factory/board.json` is `{ "jobs": [ ... ] }`, one entry
per job:

```json
{
  "id": "003-rate-limiting",
  "title": "Rate-limit the public API",
  "request": "rate limit the public api",
  "branch": "factory/003-rate-limiting",
  "worktree": ".claude/worktrees/003-rate-limiting",
  "stage": "review",
  "round": 2,
  "reviews": { "security": "CHANGES", "ux": "PASS", "ui": "pending", "code": "PASS" },
  "history": [ { "round": 1, "reviews": { "security": "CHANGES", "ux": "PASS", "ui": "PASS", "code": "PASS" } } ],
  "decision": null,
  "issue": null,
  "pr": null,
  "updated": "2026-10-08T14:03:00-05:00"
}
```

- `stage` is one of `spec`, `build`, `review`, `approve`, `pr`, `merged`, `needs-human`.
- `request` is the feature text exactly as given, or `#<n> <issue title>` for an issue job.
- `reviews` is the current round; `board.py round` pushes `{round, reviews}` onto `history` when the next starts.
- A review value is `pending`, `PASS`, `CHANGES`, or `SKIPPED` (a path-gated reviewer with nothing to review).
- `decision` is `null`, `APPROVE`, `APPROVE (human)`, or `ESCALATE`.
- `issue` and `pr` are `null` or the GitHub issue / pull request URL.
- `board.py` sets `updated` on every write and creates the file if missing.

## Before any command

The main checkout's branch and uncommitted changes don't matter — the factory never
checks out, commits, or edits code there.

1. For each job in stage `pr`, run `gh pr view <pr> --json state -q .state`; if `MERGED`, set `stage: "merged"` and remove its worktree if it has one (*Worktrees*).
2. Tell the user the dashboard is at `cd factory && python3 -m http.server 8765` → http://localhost:8765/dashboard.html.

## /factory <feature>

1. **Create the job.** `board.py new <slug> "<feature text>"` with a short kebab slug of the feature (e.g. `snooze-habit`); it prints the id (e.g. `004-snooze-habit`) and makes `factory/jobs/<id>/`. Create the job's worktree (*Worktrees*).
2. **Spec.** Spawn `factory:spec-writer` **named `spec-<id>`** with: the job id, the job folder, the worktree, the config path, and the feature text verbatim (for an issue job: "GitHub issue #<n> — read `issue.md` in the job folder"). Wait for `spec.md`. Set the board `title` from its first heading.
3. **Build.** Set `stage: "build"`. Spawn `factory:builder` **named `builder-<id>`** with: the job id, the job folder, the worktree, the config path, and the branch `factory/<id>`. Wait for it to finish and for `build.md` to exist. If the builder reports it is blocked, set `stage: "needs-human"` and stop.
4. **Review round.** Run the round loop below.

### Round loop

1. `board.py round <id> security ux ui code` (prints `<n>` and makes `round-<n>/`), then `board.py set <id> '{"stage": "review"}'`.
2. **Skip reviewers with nothing to review.** Run `git -C .claude/worktrees/<id> diff --name-only origin/main...HEAD -- <UI paths from config.md>`. If it prints nothing, don't spawn `factory:ui-reviewer`: write `round-<n>/review-ui.md` yourself as `VERDICT: PASS` followed by `Skipped by orchestrator — no changes under the UI paths.`, and set its chip to `SKIPPED`. Re-check every round, since rework can start touching the UI paths.
3. Spawn **all remaining reviewers in a single message** (they run in parallel), each **named `<reviewer>-<id>`** with: job id, job folder, worktree, config path, branch, and round folder. Each writes `round-<n>/review-<reviewer>.md`.
4. As each reviewer finishes, read the first line of its file (`VERDICT: PASS` or `VERDICT: CHANGES`) and update that chip on the board.
5. **WAIT FOR ALL** of this job's reviewers (other jobs carry on meanwhile). The round is done only when all four `review-*.md` files exist in the round folder. Never resume the builder mid-round.
6. Then:
   - **All PASS** → go to *Approve*.
   - **Any CHANGES and rework count < MAX_REWORK** → set `stage: "build"`, then resume the same builder with `SendMessage` to `builder-<id>`: "Round <n> reviews are in `<job folder>/round-<n>/`. Address every CHANGES review, commit, and append a `## Round <n> response` section to build.md." Wait for it to finish, then start the next round.
   - **Any CHANGES and rework count = MAX_REWORK** → go to *Approve* anyway; the approver will see unresolved CHANGES and escalate.

If `builder-<id>` can't be reached (e.g. a new session), spawn a fresh `factory:builder` named `builder-<id>` with the same message — everything it needs is in the job folder.

### Approve

1. Set `stage: "approve"`. Spawn `factory:approver` **named `approver-<id>`** with job id, job folder, worktree, config path, branch. Wait for `decision.md`.
2. Read its first line and set `decision`.
   - **APPROVE** → *Open PR*.
   - **ESCALATE** → set `stage: "needs-human"` (keep the worktree). Tell the user why (quote decision.md's reasons) and that they can `/factory approve <id>` (the dashboard's **Approve** button on a needs-human card copies this command) or `/factory rework <id> <note>`.

### Open PR

1. Write `factory/jobs/<id>/pr.md`:
   - If the job has an `issue`: a first line `Closes #<n>`.
   - `## Summary` — the spec's Goal, then the Changes list from build.md.
   - `## Acceptance criteria` — each AC with the test that proves it (from build.md).
   - `## Factory review` — one line per round with each reviewer's verdict, then the approver's decision and its one-paragraph summary. If `decision` is `APPROVE (human)`, say the approver escalated, quote why, and note a human approved it.
   - End with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
2. `git -C .claude/worktrees/<id> push -u origin factory/<id>`.
3. If the job has no `pr` yet: `gh pr create --base main --head factory/<id> --title "<conventional-commit title>" --body-file factory/jobs/<id>/pr.md` and store the URL in `pr`. If it already has one (a reworked job), the push already updated it; refresh the description with `gh api -X PATCH repos/{owner}/{repo}/pulls/<number> -F body=@factory/jobs/<id>/pr.md` (not `gh pr edit`, which can fail on repos with a Projects-classic error).
4. Set `stage: "pr"` and give the user the PR link. Keep the worktree until the PR merges. Never merge it.

If the push or `gh` fails, set `stage: "needs-human"` and tell the user the error.

## /factory #<n>

Run a job from GitHub issue `<n>`.

1. `python3 $SKILL_DIR/ready.py <n>`. Unless it says `READY`, stop and tell the user why (closed, taken by a job, or blocked — quote what it's waiting on). Then `gh issue view <n> --json number,title,body,comments,state,url`.
2. Create the job as in step 1 above with `board.py new <slug> "#<n> <title>" --issue <url>`, slugging the issue title (e.g. `add-export-endpoint`). `board.py` refuses if another job already has this issue — e.g. another session just started it.
3. Write `factory/jobs/<id>/issue.md`: `# #<n> <title>`, the URL, the body verbatim, then each comment under `## Comment — <author>, <date>`.
4. Continue from step 2 of `/factory <feature>`. *Open PR* puts `Closes #<n>` in the PR description so merging the PR closes the issue.

### Dependencies

Work must never start before the work it builds on is merged — the job branches from
`origin/main`, so anything unmerged simply isn't there. `ready.py` decides this; never
work it out by hand, and never start an item it doesn't print as `READY`.

- An issue depends on every issue on a body line starting with `Depends on` (e.g. `Depends on #72`, `**Depends on:** #72, #73`), plus GitHub's native "blocked by" links.
- A plain backlog line depends on any `#<m>` after "depends on" in it (e.g. `- [ ] Tidy log copy — depends on #74`).
- A dependency #<m> has landed only when #<m> is closed as completed **and**, if a factory job built it, that job's PR is merged. An issue closed by hand while its PR is still open, or closed as not planned, keeps its dependents blocked.

A merged factory PR closes its issue, so the next item in a chain becomes `READY` once you
merge the earlier PR — never while the earlier job is still running or awaiting review.

## /factory next [n]

Start the next `n` items (default 1) as separate jobs running at once.

1. Run `python3 $SKILL_DIR/ready.py`. It prints the whole queue in order — unchecked `factory/backlog.md` lines first (a `#<n>` line is that issue), then open issues labelled `factory`, oldest first — one tab-separated line each: status, `#<n>` or `backlog`, text, note.
2. Take the first `n` lines whose status is `READY`, in order. Skip everything else — `BLOCKED` (a dependency isn't merged; see *Dependencies*), `TAKEN` (already a job), `CLOSED`. Two `READY` items never depend on each other, since an item is `BLOCKED` while anything it depends on is unmerged.
3. If nothing is `READY`, say so and stop — quoting the `BLOCKED` notes, e.g. "#74 is waiting on #73; merge its PR, then run `/factory next`". If fewer than `n` are `READY`, start the ones there are and say what the rest are waiting on.

Start each job — as `/factory #<n>` for an issue (`ready.py` already checked it), otherwise as `/factory <feature>` with the line's text. If `board.py new` refuses because the request or issue is taken (another session just started it), skip that item and take the next `READY` one. For a backlog item, change its line in `ROOT/factory/backlog.md` to `- [x] <line> → <job-id>`. Don't commit it: the factory never commits the backlog, so parallel PRs don't conflict on it. The user commits backlog edits through their own PR when they like.

## /factory approve <job-id>

Only for a job in `needs-human`. Ensure its worktree (*Worktrees*), set `decision: "APPROVE (human)"`, then run *Open PR*.

## /factory rework <job-id> <note>

For a job in `needs-human` or `pr`.

1. Ensure its worktree (*Worktrees*). `board.py round <id> human`, then `board.py review <id> human CHANGES` and `board.py set <id> '{"decision": null, "stage": "build"}'`. Write the note to `round-<n>/review-human.md` starting with `VERDICT: CHANGES` followed by the note verbatim.
2. Resume (or re-spawn) `builder-<id>` pointing at `round-<n>/`, exactly as in the round loop.
3. Then run a fresh round loop. Human rework does not count toward `MAX_REWORK`; reset the rework count to 0. If it is approved again, *Open PR* updates the existing PR.

## /factory resume <job-id>

For a job whose orchestrator is gone (its session ended mid-flight) — stage `spec`,
`build`, `review`, or `approve`. Run it only when no other session is still driving the
job; two orchestrators on one job would spawn duplicate agents. If you can't tell, ask.

Ensure its worktree (*Worktrees*), then continue from its stage, reusing every file that
already exists:

- `spec` — no `spec.md`: step 2 of `/factory <feature>`. Otherwise step 3.
- `build`, `round` 0 — spawn a fresh `builder-<id>` for its first run (it picks up any commits an interrupted run left).
- `build`, `round` ≥ 1 — if build.md has `## Round <round> response`, start the next round; otherwise send the round message from the round loop to a fresh `builder-<id>`.
- `review` — spawn only the reviewers whose `review-*.md` is missing from `round-<round>/`, then continue the round loop.
- `approve` — no `decision.md`: spawn the approver. Otherwise act on its first line.

## Rules

- Spawn agents by `subagent_type` (`factory:spec-writer`, `factory:builder`, `factory:security-reviewer`, `factory:ux-reviewer`, `factory:ui-reviewer`, `factory:code-reviewer`, `factory:approver`), each named with the job id as above. Their prompts contain only ids and absolute paths (always including the config path) — never paste file contents or conversation context.
- Agents run in the background; you'll be notified when each finishes. Don't poll and don't guess results — read the files.
- You never edit code, never commit, and never commit to, merge into, or push `main`. Only the builder commits, on `factory/<id>` in the job's worktree. The only review files you write are `review-human.md` (rework) and a skipped reviewer's `review-<reviewer>.md`.
- Keep the board truthful: update it at every transition, before you tell the user.
