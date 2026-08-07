## 1. Project Bootstrap

- [ ] 1.1 Initialize Python project with `pyproject.toml` and `src/tmd/` package structure
- [ ] 1.2 Add all dependencies: textual, google-api-python-client, google-auth-httplib2, yt-dlp, sounddevice, numpy, librosa, pydantic-settings
- [ ] 1.3 Create project entry point: `tmd` console script
- [ ] 1.4 Create `~/.config/tmd/` config directory helper

## 2. Core Infrastructure

- [ ] 2.1 Implement settings manager with `pydantic-settings` (audio quality, download dir, config paths)
- [ ] 2.2 Implement SQLite database layer with `songs` table schema and CRUD operations
- [ ] 2.3 Implement database migration/initialization on first run

## 3. Authentication

- [ ] 3.1 Implement Google OAuth2 desktop flow with `google-auth-oauthlib`
- [ ] 3.2 Implement local redirect server on `localhost:8080` for auth code capture
- [ ] 3.3 Implement secure token storage with 600/700 file permissions
- [ ] 3.4 Implement automatic token refresh on startup
- [ ] 3.5 Implement logout (delete credentials, return to login screen)

## 4. Sync Engine

- [ ] 4.1 Implement YouTube Data API `playlistItems.list` fetcher for LL playlist
- [ ] 4.2 Implement pagination handling for large liked playlists
- [ ] 4.3 Implement diff algorithm: remote vs local video IDs
- [ ] 4.4 Implement insert-new-songs to SQLite with `pending` status
- [ ] 4.5 Implement sync-to-download queue bridge

## 5. Download Manager

- [ ] 5.1 Implement yt-dlp subprocess wrapper with MP3 audio extraction
- [ ] 5.2 Implement concurrent download queue (max 2 simultaneous)
- [ ] 5.3 Implement yt-dlp stdout parser for real-time progress extraction
- [ ] 5.4 Implement download progress event emission to TUI
- [ ] 5.5 Implement exponential backoff retry logic (3 retries: 5s, 15s, 45s)
- [ ] 5.6 Implement filename sanitization and `~/Music/liked-songs/` output path
- [ ] 5.7 Update database `file_path` and `status` on completion/failure

## 6. Search Module

- [ ] 6.1 Implement YouTube Data API `search.list` query handler
- [ ] 6.2 Implement search results renderer with hyperlinks (`[link=...]`) to browser
- [ ] 6.3 Implement download-and-like action (playlistItems.insert + queue download)
- [ ] 6.4 Implement "already liked" confirmation dialog

## 7. Audio Player & Visualizer

- [ ] 7.1 Implement MP3 loading with `librosa.load()` into float32 PCM array
- [ ] 7.2 Implement `sounddevice` OutputStream callback for chunked playback
- [ ] 7.3 Implement playback state machine (play/pause/stop/skip)
- [ ] 7.4 Implement 1024-sample Hann window + `numpy.fft.rfft` pipeline
- [ ] 7.5 Implement log-spaced frequency bin aggregation (32 bars, 20Hz–20kHz)
- [ ] 7.6 Implement Textual Canvas visualizer widget with Unicode block rendering
- [ ] 7.7 Implement gradient coloring (green→yellow→red) on frequency bars
- [ ] 7.8 Implement volume control (+/- 10%) via software gain on PCM chunks

## 8. TUI Screens & Navigation

- [ ] 8.1 Implement base Textual App with dark theme CSS
- [ ] 8.2 Implement Login screen ("Sign in with Google" button, auth status)
- [ ] 8.3 Implement Library screen (DataTable/ListView, sort by `added_to_yt_at DESC`)
- [ ] 8.4 Implement Search screen (Input widget, results list with hyperlinks)
- [ ] 8.5 Implement Player overlay/panel (now playing, progress bar, visualizer canvas, controls)
- [ ] 8.6 Implement Settings screen (quality selector, directory path, logout button)
- [ ] 8.7 Implement global keybindings: `/`→Search, `,`→Settings, `q`→quit, `Space`→play/pause, `n`/`p`→next/previous
- [ ] 8.8 Implement toast notification widget for download/success events

## 9. Integration & Polish

- [ ] 9.1 Wire all screens together with reactive data bindings
- [ ] 9.2 Implement startup flow: auth check → sync → queue downloads → show library
- [ ] 9.3 Implement download progress bars in Library screen
- [ ] 9.4 Handle edge cases: no songs, no internet, auth revoked, yt-dlp not found
- [ ] 9.5 Add loading spinners for sync and search operations
- [ ] 9.6 Final visual polish: spacing, borders, colors, transitions

## 10. Testing & Documentation

- [ ] 10.1 Test OAuth2 flow end-to-end with real Google account
- [ ] 10.2 Test sync with actual YouTube liked playlist
- [ ] 10.3 Test download queue with multiple concurrent downloads
- [ ] 10.4 Test audio playback and visualizer performance
- [ ] 10.5 Test search, preview links, and download-and-like flow
- [ ] 10.6 Write README with setup instructions (Google Cloud OAuth client setup)
- [ ] 10.7 Write requirements.txt / lock dependencies
