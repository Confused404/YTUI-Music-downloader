## Why

The YouTube "Liked Videos" playlist (`LL`) contains both music and non-music content. When a user likes a meme video, podcast clip, or tutorial on regular YouTube, it gets mixed into the same playlist as their YouTube Music liked songs. The TMD app currently downloads everything indiscriminately, cluttering the library with non-music files. A heuristic filter is needed to identify and skip non-music content without requiring a separate YouTube Music API.

## What Changes

- Add a tiered ensemble heuristic to `sync.py` that filters the `LL` playlist:
  - **Pass 1 (free):** Accept songs where the channel name suggests music (`VEVO`, ` - Topic`, `Official`, `Music`)
  - **Pass 2 (piggyback):** For ambiguous items, batch-fetch `snippet` + `contentDetails` and keep if `categoryId == "10"` (Music) OR duration is 60–600 seconds with `" - "` in the title
- Add `filter_music_only: bool = True` parameter to `fetch_liked_songs()` and `sync_liked_songs()` so the filter can be disabled
- Update `tui_app.py` call site to pass the new parameter (future: wire to a settings toggle)

## Capabilities

### New Capabilities

- `music-filter`: Tiered heuristic filter for identifying music-only content from YouTube's mixed "Liked Videos" playlist. Combines channel name whitelist, YouTube category ID, and duration + title pattern heuristics.

### Modified Capabilities

- `sync`: Added `filter_music_only` parameter to `fetch_liked_songs()` and `sync_liked_songs()`. When enabled, non-music items are silently dropped during sync.

## Impact

- Reuses the same `videos().list` batch call that the duration fix adds (no extra API cost when both changes are applied)
- Drops non-music items silently during sync; they won't appear in the library or download queue
- If disabled (`filter_music_only=False`), behavior reverts to current "sync everything" mode
