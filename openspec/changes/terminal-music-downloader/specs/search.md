## ADDED Requirements

### Requirement: Search YouTube via Data API
The system SHALL provide a search input that queries the YouTube Data API search.list endpoint.

#### Scenario: User searches for a song
- **WHEN** the user types a query and presses Enter on the search screen
- **THEN** the system sends the query to search.list with type=video and maxResults=25
- **AND** displays results with title, channel (artist), duration, and published date

### Requirement: Render clickable preview hyperlinks
The system SHALL display each search result as a clickable hyperlink that opens the default browser.

#### Scenario: Preview a search result
- **WHEN** the user clicks or presses Enter on a search result row
- **THEN** the system opens https://www.youtube.com/watch?v=<video_id> in the default browser
- **AND** the app remains focused in the terminal

### Requirement: Download and add to liked playlist
The system SHALL provide a download action on each search result that downloads the song AND adds it to the user's YouTube liked playlist.

#### Scenario: Download and like a searched song
- **WHEN** the user presses the Download keybinding (e.g., d) on a search result
- **THEN** the system immediately calls playlistItems.insert to add the video to the LL playlist
- **AND** queues the song in the Download Manager
- **AND** inserts the song into the local SQLite library with download_status: pending
- **AND** shows a success toast notification

#### Scenario: Already liked song
- **WHEN** the user attempts to download a song already in the liked playlist
- **THEN** the system shows a confirmation: "Already liked. Download locally anyway?"
- **AND** if confirmed, queues download without re-adding to LL playlist
