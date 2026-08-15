## ADDED Requirements

### Requirement: Batch-fetch video durations
The system SHALL call `youtube.videos().list(part="contentDetails")` in batches of up to 50 video IDs per request to fetch real durations for all songs in the liked playlist.

#### Scenario: Playlist with less than 50 songs
- **WHEN** the sync engine fetches the liked playlist and finds 30 songs
- **THEN** it makes a single `videos().list` call with all 30 IDs
- **AND** parses each `contentDetails.duration` into integer seconds

#### Scenario: Playlist with more than 50 songs
- **WHEN** the sync engine fetches the liked playlist and finds 120 songs
- **THEN** it makes three `videos().list` calls with 50, 50, and 20 IDs respectively
- **AND** all returned durations are merged into the song dicts

### Requirement: Parse ISO 8601 duration strings
The system SHALL parse YouTube's ISO 8601 duration format into integer seconds.

#### Scenario: Standard music duration
- **WHEN** the API returns `PT3M45S`
- **THEN** the parsed duration is `225` seconds

#### Scenario: Long mix or live set
- **WHEN** the API returns `PT1H2M3S`
- **THEN** the parsed duration is `3723` seconds

#### Scenario: Very short clip
- **WHEN** the API returns `PT45S`
- **THEN** the parsed duration is `45` seconds

#### Scenario: Invalid or missing duration
- **WHEN** the API returns an invalid or missing duration string
- **THEN** the parsed duration defaults to `0` seconds

### Requirement: Store durations in database
The system SHALL insert real durations into new songs and backfill existing songs with `duration_secs=0`.

#### Scenario: New song sync
- **WHEN** a new liked song is synced with a fetched duration of `225` seconds
- **THEN** the song is inserted into the database with `duration_secs=225`

#### Scenario: Existing song backfill
- **WHEN** a song already exists in the database with `duration_secs=0`
- **AND** the sync fetches a real duration of `180` seconds for that video
- **THEN** the database record is updated to `duration_secs=180`

#### Scenario: Song with valid duration unchanged
- **WHEN** a song already exists in the database with `duration_secs=300`
- **AND** the sync re-fetches the duration
- **THEN** the database record remains at `duration_secs=300`
