## ADDED Requirements

### Requirement: Channel name music whitelist
The system SHALL identify music content by checking if the video's channel name contains known music markers.

#### Scenario: VEVO channel
- **WHEN** a liked video's channel title is "AdeleVEVO"
- **THEN** the system classifies it as music and includes it in sync

#### Scenario: Topic channel
- **WHEN** a liked video's channel title is "Taylor Swift - Topic"
- **THEN** the system classifies it as music and includes it in sync

#### Scenario: Non-music channel
- **WHEN** a liked video's channel title is "PewDiePie"
- **AND** the channel name contains no music markers
- **THEN** the system proceeds to Pass 2 heuristic evaluation

### Requirement: YouTube category ID filter
The system SHALL classify content as music if its YouTube `categoryId` is `"10"` (Music category).

#### Scenario: Music category video
- **WHEN** a video's `categoryId` is `"10"`
- **THEN** the system classifies it as music and includes it in sync

#### Scenario: Entertainment category video
- **WHEN** a video's `categoryId` is `"24"` (Entertainment)
- **AND** it did not pass the channel whitelist
- **THEN** the system proceeds to Pass 3 heuristic evaluation

### Requirement: Duration and title pattern filter
The system SHALL classify ambiguous content as music if its duration is between 60–600 seconds AND its title contains `" - "`.

#### Scenario: Indie song matching pattern
- **WHEN** a video has duration `PT4M12S` (252 seconds)
- **AND** its title is "Unknown Artist - Great Song"
- **THEN** the system classifies it as music and includes it in sync

#### Scenario: Podcast matching duration but not title
- **WHEN** a video has duration `PT5M30S` (330 seconds)
- **AND** its title is "My Podcast Episode 42"
- **AND** it did not pass earlier heuristics
- **THEN** the system classifies it as non-music and excludes it from sync

#### Scenario: Long mix failing duration gate
- **WHEN** a video has duration `PT1H15M` (4500 seconds)
- **AND** it did not pass earlier heuristics
- **THEN** the system classifies it as non-music and excludes it from sync

### Requirement: Configurable filter toggle
The system SHALL allow the music filter to be enabled or disabled via a parameter.

#### Scenario: Filter enabled (default)
- **WHEN** `sync_liked_songs()` is called with `filter_music_only=True`
- **THEN** only items classified as music are synced

#### Scenario: Filter disabled
- **WHEN** `sync_liked_songs()` is called with `filter_music_only=False`
- **THEN** all liked videos are synced regardless of content type
