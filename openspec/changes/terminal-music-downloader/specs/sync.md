## ADDED Requirements

### Requirement: Fetch liked songs playlist on startup
The system SHALL fetch the user's YouTube "Liked Videos" playlist on every startup after successful authentication.

#### Scenario: Startup sync
- **WHEN** the app starts and the user is authenticated
- **THEN** the system calls the YouTube Data API playlistItems.list endpoint for the LL playlist
- **AND** paginates through all results to retrieve the complete list
- **AND** extracts video IDs, titles, channel names (artists), and publishedAt timestamps

### Requirement: Diff remote liked songs against local library
The system SHALL compare fetched remote liked songs with the local SQLite library and identify additions.

#### Scenario: New liked songs detected
- **WHEN** the sync engine receives the remote liked songs list
- **THEN** it queries the local songs table for all known video IDs
- **AND** identifies video IDs present remotely but absent locally
- **AND** inserts the new songs into the database with download_status: pending
- **AND** preserves the publishedAt timestamp as added_to_yt_at for sorting

#### Scenario: No new songs
- **WHEN** the sync engine finds zero new video IDs
- **THEN** it logs "Library up to date" and skips the download queue

### Requirement: Queue new songs for background download
The system SHALL pass pending songs to the Download Manager after sync completes.

#### Scenario: Queue pending downloads
- **WHEN** the sync engine finishes inserting new pending songs
- **THEN** it emits a signal/event to the Download Manager with the list of video IDs to fetch
- **AND** the Download Manager begins processing immediately
