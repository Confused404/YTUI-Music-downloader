## Context

The current startup flow in `tui_app.py` `_startup_sync()` follows this pattern:

```
sync_liked_songs() → returns new_songs → if new_songs: start download manager
```

This means the download manager only starts when there are **brand new** songs from the sync. Existing songs with `download_status='pending'` or `'failed'` (retry_count < 3) are completely ignored on subsequent app starts.

## Goals / Non-Goals

**Goals:**
- Ensure pending/failed songs from previous sessions get queued on every app startup
- Keep the change minimal and focused
- Maintain existing behavior when no pending songs exist

**Non-Goals:**
- Adding UI indicators for pending songs (separate feature)
- Changing the download retry logic
- Adding manual retry buttons

## Decisions

**1. Where to check for pending songs**
- After `sync_liked_songs()` completes, query `db.get_pending_songs()`
- Combine `new_songs` + `pending_songs` for download manager decision
- Rationale: Single point of startup logic, reuses existing `get_pending_songs()` method

**2. Whether to notify user**
- If pending songs are found and queued, show a notification: "Queued N pending downloads"
- Rationale: Informs the user that background work is happening without being intrusive

## Risks / Trade-offs

- **[Risk]** Large pending queues on startup could be slow → **Mitigation**: Download manager already handles concurrent workers (max 2 by default), queueing is instant
- **[Risk]** Songs marked `permanently_failed` could accidentally be re-queued → **Mitigation**: `get_pending_songs()` already filters `retry_count < 3`
