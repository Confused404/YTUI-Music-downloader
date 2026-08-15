## 1. Music Channel Whitelist

- [x] 1.1 Define `_MUSIC_CHANNEL_KEYWORDS` constant tuple in `sync.py`
- [x] 1.2 Implement `_is_music_channel(channel_title: str) -> bool` helper
- [x] 1.3 Test with sample channels: "AdeleVEVO" → True, "Taylor Swift - Topic" → True, "PewDiePie" → False

## 2. Video Details Batch Fetcher

- [x] 1.4 Implement `_fetch_video_details(youtube, video_ids)` returning `{vid: {duration_secs, category_id}}`
- [x] 1.5 Use `part="snippet,contentDetails"` to get both categoryId and duration in one call
- [x] 1.6 Chunk into batches of 50 IDs per request
- [x] 1.7 Parse durations and extract `categoryId` from each response item

## 3. Tiered Filter Integration

- [x] 1.8 Modify `fetch_liked_songs()` to accept `filter_music_only: bool = True` parameter
- [x] 1.9 Implement Pass 1: accept songs where `_is_music_channel()` returns True
- [x] 1.10 Implement Pass 2: for ambiguous items, call `_fetch_video_details()`
- [x] 1.11 Accept if `category_id == "10"` OR (`60 <= duration <= 600` AND `" - " in title`)
- [x] 1.12 Silently drop items that fail all heuristics (don't add to result list)
- [x] 1.13 If `filter_music_only=False`, bypass all filtering and return everything

## 4. Sync Function Updates

- [x] 1.14 Modify `sync_liked_songs()` to accept `filter_music_only: bool = True` parameter
- [x] 1.15 Pass the parameter through to `fetch_liked_songs()`
- [x] 1.16 Update `tui_app.py` call site in `_startup_sync()` to pass `filter_music_only=True`
- [x] 1.17 Add TODO comment for future settings toggle wiring

## 5. Integration & Testing

- [ ] 1.18 Run `uv run tmd` and verify non-music liked videos are not synced
- [ ] 1.19 Verify music videos still sync correctly (including VEVO, Topic, indie)
- [ ] 1.20 Test with `filter_music_only=False` to confirm all videos sync
- [ ] 1.21 Verify durations are still fetched correctly (integration with duration fix)

**Note:** Tasks 1.18–1.21 require manual runtime testing with a live YouTube OAuth session. The code implementation is complete and verified with syntax checks.
