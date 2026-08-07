## ADDED Requirements

### Requirement: Download audio from YouTube via yt-dlp
The system SHALL invoke yt-dlp to download the best available audio stream for each queued video.

#### Scenario: Successful download
- **WHEN** the Download Manager dequeues a pending song
- **THEN** it spawns yt-dlp with arguments for audio-only download (-x --audio-format mp3 --audio-quality <quality>)
- **AND** writes the output to ~/Music/liked-songs/{artist} - {title}.mp3
- **AND** sanitizes filenames to remove illegal characters

### Requirement: Support concurrent downloads with a limit
The system SHALL limit concurrent downloads to prevent bandwidth exhaustion.

#### Scenario: Concurrent download queue
- **WHEN** multiple songs are pending
- **THEN** the Download Manager processes up to 2 downloads simultaneously
- **AND** queues additional songs in FIFO order
- **AND** updates the database download_status to downloading for active downloads

### Requirement: Track and report download progress
The system SHALL parse yt-dlp stdout to extract real-time download progress.

#### Scenario: Progress updates
- **WHEN** yt-dlp reports progress (e.g., [download] 45.3% of 3.50MiB at 1.20MiB/s)
- **THEN** the Download Manager parses the percentage
- **AND** emits progress events to the TUI for display in a progress bar widget

### Requirement: Handle download failures
The system SHALL mark failed downloads and retry with exponential backoff.

#### Scenario: Download failure
- **WHEN** yt-dlp exits with a non-zero code or network error
- **THEN** the system updates download_status to failed
- **AND** increments a retry counter in the database
- **AND** retries up to 3 times with delays of 5s, 15s, and 45s
- **AND** after 3 failures, marks the song as permanently_failed and logs the error

### Requirement: Configurable audio quality
The system SHALL allow users to select MP3 bitrate in settings.

#### Scenario: Quality selection
- **WHEN** the user sets audio quality to "320k" in settings
- **THEN** subsequent yt-dlp invocations use --audio-quality 320K
- **AND** the setting persists across restarts in ~/.config/tmd/settings.json
