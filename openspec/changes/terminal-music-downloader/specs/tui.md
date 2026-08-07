## ADDED Requirements

### Requirement: Define application screens
The system SHALL organize the TUI into distinct screens with clear navigation.

#### Scenario: Screen structure
- **WHEN** the app starts
- **THEN** it presents the Login screen if unauthenticated, or the Library screen if authenticated
- **AND** the user can navigate to Search via / or s keybinding
- **AND** the user can navigate to Settings via , keybinding
- **AND** pressing q from any screen prompts to quit

### Requirement: Login screen
The system SHALL display a clear login screen for unauthenticated users.

#### Scenario: Login flow UI
- **WHEN** the app is launched with no credentials
- **THEN** the Login screen shows the app name and a prominent "Sign in with Google" button
- **AND** clicking the button shows a message: "Opening browser for authentication..."
- **AND** upon successful auth, automatically transitions to Library screen

### Requirement: Library screen with roladex view
The system SHALL display the liked songs library as a scrollable, sortable list.

#### Scenario: Library view
- **WHEN** the user is on the Library screen
- **THEN** a scrollable DataTable or ListView shows all songs sorted by added_to_yt_at DESC
- **AND** columns include: #, Title, Artist, Duration, Status
- **AND** the currently selected row is highlighted with a distinct style
- **AND** pressing Enter on a row starts playback
- **AND** pressing / switches to Search screen

### Requirement: Search screen with input and results
The system SHALL provide a dedicated search interface with real-time or on-submit querying.

#### Scenario: Search interface
- **WHEN** the user navigates to the Search screen
- **THEN** an Input widget at the top accepts the search query
- **AND** pressing Enter submits the query and shows a loading spinner
- **AND** results appear below as a list with Title, Artist, Duration
- **AND** each result is rendered as a hyperlink to https://www.youtube.com/watch?v=<id>
- **AND** pressing d on a result triggers download-and-like

### Requirement: Player overlay panel
The system SHALL show a persistent or togglable player panel with visualizer and controls.

#### Scenario: Player panel display
- **WHEN** a song is playing or paused
- **THEN** a bottom or side panel shows: Now Playing title/artist, progress bar, visualizer canvas, and control hints
- **AND** the visualizer animates in real-time during playback
- **AND** the progress bar shows elapsed time / total duration

### Requirement: Settings screen
The system SHALL expose configuration options in a dedicated settings screen.

#### Scenario: Settings view
- **WHEN** the user opens Settings
- **THEN** the screen shows: Audio Quality selector (128k/192k/256k/320k), Download Directory path, Logout button
- **AND** changes are saved immediately to ~/.config/tmd/settings.json

### Requirement: Modern visual styling
The system SHALL use a visually appealing, easy-on-the-eyes color scheme and layout.

#### Scenario: Default theme
- **WHEN** the app renders any screen
- **THEN** it uses a dark theme with muted accent colors (e.g., deep blue/purple background, cyan highlights, soft white text)
- **AND** borders and dividers use rounded box-drawing characters where supported
- **AND** the layout has adequate padding and spacing between widgets
