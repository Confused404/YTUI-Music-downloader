## Why

The sync engine currently hardcodes `duration_secs=0` for every song fetched from YouTube. This means the Library TUI screen cannot display real song durations, making it impossible for users to see how long a track is before playing it. The duration data is freely available from the YouTube Data API via `videos().list(part="contentDetails")` — we just aren't fetching it.

## What Changes

- Modify `sync.py` to batch-call `youtube.videos().list` after fetching the `LL` playlist items
- Parse YouTube's ISO 8601 duration strings (`PT3M45S` → `252` seconds) into integer seconds
- Merge real durations into each song dict before database insertion
- Retroactively update existing database records where `duration_secs=0` with newly fetched durations
- Add `update_song_duration()` method to `database.py` if not already present

## Capabilities

### New Capabilities

- `duration-sync`: Batch-fetching real song durations from YouTube Data API `videos().list(contentDetails)` and merging them into the sync pipeline.

### Modified Capabilities

- `sync`: Enhanced `fetch_liked_songs()` to include real `duration_secs` from `contentDetails`. Retroactive duration backfill for existing library entries with `duration_secs=0`.

## Impact

- One additional `videos().list` API call per 50 songs (1 quota unit per batch)
- No breaking changes to TUI — the Library screen already reads `duration_secs`
- Backward compatible with existing database schema
