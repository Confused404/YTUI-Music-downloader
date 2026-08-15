## Why

When a user's Google OAuth2 refresh token expires (common in Testing mode apps where tokens die after 7 days), the app currently shows a raw `invalid_grant` error and leaves the user on a broken Library screen. The user should be able to continue browsing and playing already-downloaded songs while being gently reminded that sync is paused. A non-intrusive, dismissible banner in the bottom-right corner provides this graceful degradation.

## What Changes

- Add `TokenExpiredError` exception to `auth.py` that clears stale credentials and wraps the `invalid_grant` error
- Catch `TokenExpiredError` in `tui_app.py` `_startup_sync()` without showing an error toast
- Add `auth_expired` reactive flag to `TMDApp`
- Create `AuthBanner` widget (bottom-right, dismissible with X button + Re-authenticate button)
- Mount banner at app level so it persists across screen switches
- Re-show banner on any subsequent sync/search attempt that hits expired auth
- Add CSS styling for banner positioning and appearance

## Capabilities

### New Capabilities

- `auth-degradation`: Graceful handling of expired OAuth tokens with non-intrusive UI
- `auth-banner`: Persistent but dismissible notification widget for re-authentication

### Modified Capabilities

- `auth`: Add `TokenExpiredError` and automatic stale credential cleanup
- `sync`: Catch and propagate token expiration instead of generic error
- `tui`: Add `auth_expired` reactive state and banner integration

## Impact

- No database schema changes
- No external dependencies
- Only affects the auth flow error path — normal operation unchanged
- Banner is dismissible and non-blocking
