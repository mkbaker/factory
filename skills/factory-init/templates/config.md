# Factory config

Read by the factory orchestrator and every factory agent. Edit freely — this file is the
only place the factory learns about this repo.

## Repo
<!-- 2–4 sentences: what this repo is, language/stack, where the code lives. -->

## Install
<!-- One command per line, run inside each new worktree. Remove the section's bullets if none. -->
- 

## Verify
<!-- Every command must pass before a job is approved. Typecheck, lint, tests, build. -->
- 

## Verify (UI)
<!-- Extra commands, run only when a UI path changed. -->
- 

## UI paths
<!-- Paths (relative to the repo root) that count as UI. The ui reviewer is skipped when a job touches none of them. -->
- 

## Users
<!-- Who uses this and what they want, e.g. "a solo developer who wants zero interruptions". Drives the ux reviewer. -->

## Conventions
<!-- Repo-specific rules the code reviewer should enforce, beyond what CLAUDE.md says. -->
- 

## Security focus
<!-- Risks specific to this repo: tokens, privacy boundaries, data the app doesn't own, public endpoints. -->
- 

## Sensitive areas
<!-- Changes here always ESCALATE to a human instead of auto-opening a PR: migrations, auth, billing, deletion of external data. -->
- 

## UI notes
<!-- Design system, style files, existing components, timezone/format helpers the ui reviewer should check. -->
- 
