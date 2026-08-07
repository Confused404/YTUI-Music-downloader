## ADDED Requirements

### Requirement: Authenticate via Google OAuth2 desktop flow
The system SHALL initiate a Google OAuth2 desktop application flow when no valid token exists.

#### Scenario: First-time authentication
- **WHEN** the user launches the app with no stored credentials
- **THEN** the system opens the default browser to a Google OAuth2 consent screen
- **AND** starts a local redirect server on localhost:8080 to capture the authorization code
- **AND** exchanges the code for an access token and refresh token
- **AND** stores the token securely in ~/.config/tmd/credentials.json

#### Scenario: Token refresh on startup
- **WHEN** the user launches the app with expired credentials
- **THEN** the system automatically refreshes the access token using the stored refresh token
- **AND** proceeds to the library screen without user interaction

### Requirement: Secure token storage
The system SHALL store OAuth2 tokens with restrictive file permissions.

#### Scenario: Token file permissions
- **WHEN** the system writes credentials to disk
- **THEN** the file permissions SHALL be set to 600 (owner read/write only)
- **AND** the parent directory SHALL have 700 permissions

### Requirement: Logout and revoke
The system SHALL provide a logout mechanism that clears local tokens.

#### Scenario: User logs out
- **WHEN** the user selects "Logout" from settings
- **THEN** the system deletes ~/.config/tmd/credentials.json
- **AND** returns to the login screen
- **AND** the next startup requires re-authentication
