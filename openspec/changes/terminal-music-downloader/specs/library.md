## ADDED Requirements

### Requirement: Store song metadata in SQLite
The system SHALL maintain a local SQLite database with a structured songs table.

#### Scenario: Database schema
- **WHEN** the app initializes for the first time
- **THEN** it creates a songs table with columns: video_id (PRIMARY KEY), title, artist, duration_secs, thumbnail_url, file_path, added_to_yt_at, downloaded_at, download_status

### Requirement: File storage organization
The system SHALL store downloaded MP3 files in a predictable directory structure.

#### Scenario: Save downloaded song
- **WHEN** a download completes successfully
- **THEN** the file is saved to ~/Music/liked-songs/{artist} - {title}.mp3
- **AND** the file_path column in the database is updated accordingly

### Requirement: Sort library by most recently added
The system SHALL display the library sorted with newest liked songs at the top.

#### Scenario: Library view sort order
- **WHEN** the user views the library screen
- **THEN** songs are ordered by added_to_yt_at DESC (most recent first)
- **AND** pending downloads appear with a spinner or "Downloading..." indicator
- **AND** failed downloads appear with an error icon

### Requirement: Track download status per song
The system SHALL maintain accurate download status for each song in the database.

#### Scenario: Status lifecycle
- **WHEN** a song is first discovered during sync
- **THEN** its status is set to pending
- **AND** when download starts, status changes to downloading
- **AND** on success, status changes to completed and downloaded_at is set
- **AND** on failure, status changes to failed
