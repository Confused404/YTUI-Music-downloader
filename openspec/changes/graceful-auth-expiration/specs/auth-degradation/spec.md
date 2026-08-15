## ADDED Requirements

### Requirement: Detect expired refresh tokens
The system SHALL detect `invalid_grant` errors during token refresh and distinguish them from other authentication failures.

#### Scenario: Token expired after 7 days
- **WHEN** `load_credentials()` attempts to refresh an expired token
- **AND** Google returns `invalid_grant`
- **THEN** the system clears the stale credentials file
- **AND** raises `TokenExpiredError` with a user-friendly message

#### Scenario: Other auth failure
- **WHEN** `load_credentials()` encounters a non-`invalid_grant` auth error
- **THEN** the system raises the original `AuthenticationError` without clearing credentials

### Requirement: Show dismissible auth banner
The system SHALL display a non-intrusive banner when token expiration is detected.

#### Scenario: Sync fails with expired token
- **WHEN** `_startup_sync()` catches `TokenExpiredError`
- **THEN** no error toast is shown
- **AND** the auth banner appears in the bottom-right corner

#### Scenario: User dismisses banner
- **WHEN** the user clicks the X button on the banner
- **THEN** the banner is hidden
- **AND** the user can continue using the Library screen normally

#### Scenario: Banner reappears on next auth failure
- **WHEN** the user attempts a sync or search after dismissing the banner
- **AND** the auth token is still expired
- **THEN** the banner reappears

### Requirement: Re-authenticate from banner
The system SHALL allow one-click re-authentication directly from the banner.

#### Scenario: User clicks Re-authenticate
- **WHEN** the user clicks the Re-authenticate button
- **THEN** the OAuth flow starts (browser opens)
- **AND** on success, the banner is hidden
- **AND** sync resumes automatically
