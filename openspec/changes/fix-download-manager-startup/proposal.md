## Why

The download manager only starts when `sync_liked_songs()` returns newly synced songs. If a user restarts the app while songs are still pending or failed from a previous session, the download manager is never initialized and those songs remain stuck in `pending` status forever. This is a silent failure — the user sees songs in their library but they never download.

## What Changes

- Modify `_startup_sync()` in `tui_app.py` to check for existing pending/failed songs after sync
- Start the download manager if there are **either** new songs **or** existing pending songs
- Queue all existing pending songs (with retry_count < 3) into the download manager on startup
- Add a helper method to check and queue pending songs from the database

## Capabilities

### Modified Capabilities

- `download`: Startup flow now checks for and queues existing pending/failed songs, not just new ones
- `sync`: `_startup_sync()` now ensures download manager starts for any pending work

## Impact

- No database schema changes
- No external dependencies
- Minimal code change (3-5 lines in `_startup_sync()`)
- Fixes silent stuck downloads for all existing users
