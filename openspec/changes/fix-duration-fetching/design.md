## Context

The Terminal Music Downloader (TMD) syncs liked songs from YouTube's `LL` playlist. Currently, every song gets `duration_secs=0` hardcoded in `sync.py` because the `playlistItems().list` endpoint only returns metadata (title, channel, publishedAt) — not the video duration. The duration lives in the `contentDetails` part of the `videos().list` endpoint. The TUI Library screen already has a Duration column, but it shows `0:00` for every song because the database has no real data.

## Goals / Non-Goals

**Goals:**
- Batch-fetch real song durations from YouTube Data API during sync
- Parse ISO 8601 duration strings into integer seconds
- Store durations in the SQLite database
- Retroactively backfill existing songs that have `duration_secs=0`
- Keep API quota usage minimal (batched calls, 50 IDs per request)

**Non-Goals:**
- Adding a new UI element for duration (the column already exists)
- Changing the database schema (duration_secs column already exists)
- Fetching additional video metadata beyond duration

## Decisions

**1. Batch API call after playlist fetch**
- After `playlistItems().list` collects all video IDs, make a single pass of `videos().list(part="contentDetails", id=",".join(ids))` in chunks of 50.
- Rationale: YouTube Data API allows up to 50 comma-separated IDs per `videos().list` call, costing 1 quota unit per call regardless of ID count. This is the most quota-efficient approach.
- Alternative: Call `videos().list` per video — rejected because it burns 1 unit per song.

**2. ISO 8601 parsing with regex**
- Use `re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")` to parse YouTube's duration format (e.g., `PT3M45S` → 252).
- Rationale: No external dependency needed. YouTube only returns the `PT#H#M#S` format, so a lightweight regex is sufficient.
- Alternative: `isodate` library — rejected to avoid adding a dependency for a single simple parse.

**3. Retroactive backfill in sync flow**
- During sync, if a song already exists in the database but has `duration_secs=0`, update it with the newly fetched duration.
- Rationale: Existing users will benefit immediately without needing a manual migration script.
- Alternative: Separate migration script — rejected because it's extra complexity when the sync flow can handle it naturally.

## Risks / Trade-offs

- **[Risk]** API quota burn on large playlists → **Mitigation**: Batched calls (1 unit per 50 videos). A 1000-song playlist costs 20 quota units for the batch call. Default daily quota is 10,000 units.
- **[Risk]** Private/deleted videos in the liked playlist won't return data from `videos().list` → **Mitigation**: Default to `duration_secs=0` if a video ID is missing from the response. The song still syncs, just without a known duration.
