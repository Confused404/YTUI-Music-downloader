## Context

This is a greenfield Python project. The goal is a unified terminal application that replaces the manual workflow of checking YouTube Music liked songs, downloading them, organizing files, and playing them. Existing tools like yt-dlp handle downloading, but there is no integrated TUI solution with automatic sync, library management, and real-time audio visualization.

## Goals / Non-Goals

**Goals:**
- Single executable Python TUI app for discovering, downloading, and playing liked songs.
- Automatic sync of YouTube liked playlist on startup with background downloading.
- Real-time FFT audio visualizer rendered in the terminal.
- Search with browser preview and one-click download-to-liked flow.
- Modern, easy-on-the-eyes terminal UI using Textual.

**Non-Goals:**
- Support for video download or playback (audio-only).
- Support for streaming without downloading (offline-first design).
- Multi-user or cloud-synced library (single-device local storage).
- Playlist creation/management beyond the single liked playlist.
- Cross-platform support beyond Linux (initial target only).

## Decisions

**Decision: Use Textual over rich + custom curses**
- **Rationale**: Textual provides reactive widgets, built-in layout managers, CSS-like styling, and a Canvas widget needed for the visualizer. It drastically reduces TUI boilerplate.
- **Alternative considered**: `urwid` or `blessed` — lower-level, more manual widget work, harder to achieve modern look.

**Decision: Use YouTube Data API v3 (official) over ytmusicapi (unofficial)**
- **Rationale**: Official API is stable, documented, and the OAuth2 flow is well-understood. ytmusicapi is powerful but relies on internal endpoints that can break.
- **Trade-off**: YouTube Data API has quota limits (10,000 units/day); liked playlist fetches cost ~1 unit per page. This is sufficient for personal use.

**Decision: Use `sounddevice` + `numpy` for playback and FFT over `pygame.mixer`**
- **Rationale**: `sounddevice` provides raw PCM stream access required for FFT analysis. `pygame.mixer` abstracts audio too much to extract real-time samples.
- **Alternative considered**: `miniaudio` — good but heavier dependency with native bindings.

**Decision: Use `librosa` + `soundfile` for MP3 decoding over `pydub`**
- **Rationale**: `librosa` is the standard Python audio analysis library and integrates cleanly with `numpy` arrays for FFT. `soundfile` handles I/O.
- **Alternative considered**: `pydub` (ffmpeg wrapper) — introduces external ffmpeg dependency which complicates setup.

**Decision: SQLite for library metadata over JSON/flat files**
- **Rationale**: Need structured queries for sorting, filtering, and tracking download status. SQLite is zero-config and built into Python.

**Decision: Download MP3 at configurable bitrate rather than keeping native formats (m4a, webm)**
- **Rationale**: MP3 is universally supported by playback libraries and user expectation. yt-dlp can convert on-the-fly with ffmpeg.
- **Trade-off**: Slight quality loss from re-encoding; acceptable for convenience.

## Risks / Trade-offs

**Risk: YouTube Data API quota exhaustion** → Mitigation: Cache results aggressively; sync only on startup; search uses minimal quota.

**Risk: OAuth2 token exposure on shared machine** → Mitigation: Store in `~/.config/tmd/` with 600 permissions; offer logout/revoke.

**Risk: yt-dlp breaking changes** → Mitigation: Pin yt-dlp version in requirements; provide update instructions.

**Risk: FFT visualizer CPU usage** → Mitigation: 1024-sample FFT at ~30 FPS is lightweight on modern CPUs; cap at 30 FPS; skip rendering if terminal loses focus.

**Risk: Textual Canvas widget performance at high FPS** → Mitigation: Batch canvas updates; reduce bar count to 32 under load.

## Migration Plan

Not applicable — greenfield project. First-time setup requires:
1. `pip install -r requirements.txt`
2. Create Google Cloud OAuth2 desktop client
3. Run `tmd` → follow OAuth2 link
4. First sync auto-triggers on successful auth

## Open Questions

- Should the app auto-start playback of newest liked song after sync? (Leaning toward no — let user choose.)
- Should failed downloads retry automatically or require manual intervention?
- Exact Unicode block set for smoothest visualizer rendering across terminals.
