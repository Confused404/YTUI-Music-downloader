## 1. Auth Error Detection

- [x] 1.1 Add `TokenExpiredError` exception class to `auth.py`
- [x] 1.2 Modify `load_credentials()` to catch `RefreshError` with `invalid_grant`
- [x] 1.3 Clear stale credentials file (`logout()`) before raising `TokenExpiredError`
- [x] 1.4 Let other `RefreshError` variants propagate as normal `AuthenticationError`

## 2. Banner Widget

- [x] 1.5 Create `AuthBanner` widget class with dismissible X button + Re-authenticate button
- [x] 1.6 Add CSS styling for banner positioning (bottom-right, compact)
- [x] 1.7 Implement dismiss logic (X button hides banner)
- [x] 1.8 Implement re-auth logic (Re-authenticate button triggers `action_login()`)

## 3. TUI Integration

- [x] 1.9 Add `auth_expired` reactive flag to `TMDApp`
- [x] 1.10 Mount `AuthBanner` at app level in `on_mount()`
- [x] 1.11 Hide banner by default
- [x] 1.12 Catch `TokenExpiredError` in `_startup_sync()` silently (no toast)
- [x] 1.13 Set `auth_expired = True` when token expiry is detected
- [x] 1.14 Set `auth_expired = False` on successful re-authentication
- [x] 1.15 Wire banner visibility to `auth_expired` reactive flag

## 4. Recurring Banner

- [x] 1.16 Catch `TokenExpiredError` in search flow and re-show banner
- [x] 1.17 Catch `TokenExpiredError` in download-and-like flow and re-show banner
- [x] 1.18 Ensure banner reappears even if previously dismissed (auth_expired flag controls it)

## 5. Testing

- [ ] 1.19 Simulate expired token and verify banner appears
- [ ] 1.20 Verify dismissing banner allows continued Library use
- [ ] 1.21 Verify re-authenticating from banner hides it and resumes sync
- [ ] 1.22 Verify other auth errors still show proper error toasts

**Note:** Tasks 1.19–1.22 require manual runtime testing with a live YouTube OAuth session or by temporarily corrupting the credentials file.
