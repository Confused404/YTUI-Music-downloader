# Agent Instructions

## Project: Terminal Music Downloader (TMD)

### Permission Policy

**BEFORE performing destructive actions, ALWAYS ask the user for explicit permission.**

- Show what will be done
- Explain the impact
- Wait for user confirmation before proceeding

### Allowed Without Asking

- Reading files (`read`, `glob`, `grep`)
- Editing source files (`src/**/*.py`, `*.json`, `*.yaml`, `*.toml`)
- Running non-destructive commands (`git status`, `git log`, `ls`, etc.)
- Writing to `openspec/` planning artifacts
- Asking questions or providing summaries

### Must Ask First

- Running `git commit`, `git push`
- Installing dependencies
- Deleting files
- Running destructive bash commands

### User Override

If the user explicitly grants blanket permission (e.g., "just do it", "stop asking"), you may proceed without further confirmation until they revoke it.
