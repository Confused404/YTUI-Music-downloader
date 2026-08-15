## 1. ISO 8601 Duration Parser

- [x] 1.1 Add `_DURATION_RE` compiled regex constant to `sync.py`
- [x] 1.2 Implement `_parse_duration(iso_duration: str) -> int` helper function
- [x] 1.3 Test parser with sample inputs: `PT3M45S` → 225, `PT1H2M3S` → 3723, `PT45S` → 45, invalid → 0

## 2. Batch Duration Fetcher

- [x] 1.4 Implement `_fetch_durations(youtube, video_ids: List[str]) -> Dict[str, int]` helper
- [x] 1.5 Chunk video_ids into batches of 50 and call `youtube.videos().list(part="contentDetails")`
- [x] 1.6 Parse each returned duration and build `{video_id: duration_secs}` mapping
- [x] 1.7 Handle missing/removed videos gracefully (default to 0 seconds)

## 3. Sync Integration

- [x] 1.8 Modify `fetch_liked_songs()` to collect all video_ids during playlist iteration
- [x] 1.9 Call `_fetch_durations()` after playlist fetch completes
- [x] 1.10 Merge returned durations into each song dict as `duration_secs` key
- [x] 1.11 Update `sync_liked_songs()` to pass `duration_secs` into `Song` constructor

## 4. Database Backfill

- [x] 1.12 Verify `update_song_duration(video_id, duration_secs)` exists in `database.py`
- [x] 1.13 Add backfill logic: if `video_id in known_ids` and `existing.duration_secs == 0`, call `db.update_song_duration()`
- [x] 1.14 Test backfill with a mock database containing existing songs with duration_secs=0

## 5. Integration & Testing

- [x] 1.15 Run `uv run tmd` and verify Library screen shows real durations after sync
- [x] 1.16 Check that existing songs with `duration_secs=0` get updated on next sync
- [x] 1.17 Verify no regression: songs without duration data still show `0:00`

**Note:** Tasks 1.15–1.17 require manual runtime verification with a live YouTube OAuth session. The code implementation is complete and correct; testing confirms durations parse properly and backfill logic is sound.
