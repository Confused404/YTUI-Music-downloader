## Why

Managing music from YouTube Music liked songs is cumbersome: users must manually check for newly liked songs, download them individually, and organize files. There is no unified terminal-based tool that automates discovery, downloading, and playback with a polished modern interface. This change builds a single Terminal Music Downloader (TMD) that connects to a user's Google account, syncs liked songs, auto-downloads new additions, and provides a stunning TUI with real-time audio visualization.

## What Changes

- Create a Python terminal application using Textual with a modern, reactive TUI.
- Integrate Google OAuth2 authentication for YouTube Data API v3 access.
- Implement automatic sync of the user's YouTube "Liked Videos" playlist on startup, diffing against a local SQLite library.
- Build a background download manager using yt-dlp to fetch audio (MP3, 128k–320k configurable) for any new liked songs.
- Add a YouTube search screen with clickable hyperlinks to preview songs in the browser, and a download button that adds the song to both local storage and the YouTube liked playlist.
- Develop an in-terminal audio player using `sounddevice` with a real-time FFT frequency visualizer rendered on a Textual Canvas widget.
- Provide library browsing sorted by most recently added, with metadata, thumbnails, and download status.

## Capabilities

### New Capabilities

- `auth`: Google OAuth2 desktop flow, token storage, automatic refresh, and logout.
- `sync`: Fetch and diff the YouTube "Liked Videos" playlist against a local SQLite database; queue missing songs for download.
- `download`: yt-dlp integration with a background concurrent queue, progress tracking, MP3 conversion, and configurable audio quality.
- `search`: YouTube Data API search with hyperlinked preview results, plus a download-and-like action that adds the song to both local library and YouTube liked playlist.
- `library`: SQLite database schema, file storage in `~/Music/liked-songs/`, metadata management, and sorting by most-recently-added.
- `player`: Audio playback engine using `sounddevice`, real-time FFT analysis with `numpy`, and a visualizer widget rendered with Unicode block characters on a Textual Canvas.
- `tui`: Textual application structure defining screens (Login, Library, Player overlay, Search, Settings), reactive widgets, keybindings, and navigation flow.

### Modified Capabilities

- None. This is a greenfield project with no existing specs.

## Impact

- **New dependencies**: `textual`, `google-api-python-client`, `google-auth-httplib2`, `yt-dlp`, `sounddevice`, `numpy`, `librosa` (or `soundfile`), `pydantic-settings`.
- **External services**: YouTube Data API v3 (OAuth2 required), YouTube Music liked playlist.
- **File system**: Creates `~/Music/liked-songs/` for audio storage and `~/.config/tmd/` for credentials/settings.
- **Security**: OAuth2 tokens stored locally; users must create a Google Cloud desktop OAuth client.
- **Performance**: FFT visualizer runs at 30–60 FPS; download queue limited to 2 concurrent downloads to respect bandwidth.
