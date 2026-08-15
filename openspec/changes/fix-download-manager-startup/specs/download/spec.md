## MODIFIED Requirements

### Requirement: Startup download queue initialization
The system SHALL check for and queue existing pending/failed songs on every app startup, not only newly synced songs.

#### Scenario: App restart with pending songs
- **WHEN** the app starts and `_startup_sync()` runs
- **AND** `sync_liked_songs()` returns 0 new songs
- **AND** there are 5 songs in the database with `download_status='pending'` and `retry_count < 3`
- **THEN** the download manager SHALL start
- **AND** those 5 pending songs SHALL be queued for download

#### Scenario: Mixed new and pending songs
- **WHEN** `_startup_sync()` runs
- **AND** `sync_liked_songs()` returns 2 new songs
- **AND** there are 3 existing pending songs
- **THEN** all 5 songs (2 new + 3 pending) SHALL be queued
- **AND** the download manager SHALL start

#### Scenario: No pending or new songs
- **WHEN** `_startup_sync()` runs
- **AND** there are no new songs and no pending songs
- **THEN** the download manager SHALL NOT start
- **AND** the Library screen shows existing completed songs

#### Scenario: Permanently failed songs ignored
- **WHEN** there are songs with `download_status='permanently_failed'`
- **AND** `retry_count >= 3`
- **THEN** those songs SHALL NOT be queued on startup
