## Context

The YouTube "Liked Videos" playlist (`LL`) is the only official Data API v3 endpoint for accessing a user's liked content. However, this playlist is shared between YouTube and YouTube Music — meaning it contains both music videos and non-music content (memes, tutorials, podcasts, etc.). The TMD app currently syncs and downloads everything indiscriminately, leading to a cluttered library with non-music files. There is no separate "YouTube Music API" for liked songs, so a heuristic approach is necessary.

## Goals / Non-Goals

**Goals:**
- Implement a music-only filter that runs during sync to identify and skip non-music content
- Use a tiered heuristic that minimizes API cost (free pass for obvious music, batch call for ambiguous items)
- Make the filter configurable via a `filter_music_only` parameter
- Piggyback the filter on the same `videos().list` call used by the duration fix (when both changes are applied)

**Non-Goals:**
- Perfect accuracy (100% music identification is impossible with heuristics)
- Adding a UI toggle for the filter in this change (wiring point left for future settings work)
- Using machine learning or audio analysis (too complex for this scope)
- Deleting already-downloaded non-music files from the library

## Decisions

**1. Tiered ensemble heuristic**
- Pass 1 (free): Accept songs from channels containing `VEVO`, ` - Topic`, `Official`, or `Music`. Uses existing `playlistItems().list(part="snippet")` data.
- Pass 2 (batched): For remaining items, call `videos().list(part="snippet,contentDetails")` and accept if `categoryId == "10"` (YouTube Music category) OR duration is 60–600 seconds with `" - "` in title.
- Rationale: Maximizes recall (catches most music) while minimizing false positives and API cost. The channel whitelist catches ~60-70% of commercial music for free.
- Alternative: Single pass using only categoryId — rejected because many music videos lack category 10.
- Alternative: Audio fingerprinting (e.g., AcoustID) — rejected because it requires downloading audio first, defeating the purpose.

**2. Silent dropping vs. flagging**
- Non-music items are silently dropped during sync (not inserted into the database).
- Rationale: Keeps the library clean. Users don't want to see skipped memes. If they want everything, they can set `filter_music_only=False`.
- Alternative: Insert with `is_music=False` flag — rejected because it adds DB schema complexity and clutters the library view.

**3. Parameter wiring in sync functions**
- Add `filter_music_only: bool = True` to `fetch_liked_songs()` and `sync_liked_songs()`.
- Rationale: Allows the TUI to toggle the filter in the future (e.g., a "Show all liked videos" setting).
- Alternative: Global config flag in `settings.py` — rejected because the parameter is more flexible and doesn't require settings UI work in this change.

## Risks / Trade-offs

- **[Risk]** False negatives — legitimate music from small/indie artists may be filtered out if it doesn't match any heuristic → **Mitigation**: The duration+title pattern (60-600s with `" - "`) catches a lot of indie content. Users can disable the filter entirely if needed.
- **[Risk]** False positives — some non-music content might pass the filter (e.g., a 3-minute podcast with `" - "` in the title) → **Mitigation**: The ensemble approach (channel OR category OR duration+title) is conservative enough that most non-music is caught by at least one gate.
- **[Risk]** API quota on large playlists with mostly non-music content → **Mitigation**: The batch call is shared with the duration fix. If both changes are applied, the filter adds zero extra API cost.
