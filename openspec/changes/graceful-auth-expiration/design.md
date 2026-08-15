## Context

The current auth flow breaks when Google's `refresh_token` expires (7 days in Testing mode). The user sees a raw `invalid_grant` error and stays on a broken Library screen. The user wants graceful degradation: continue using the app (browse/play local songs) with a dismissible banner prompting re-auth.

## Goals / Non-Goals

**Goals:**
- Detect `invalid_grant` specifically and distinguish it from other auth errors
- Allow the user to continue browsing/playing already-downloaded songs
- Show a non-intrusive, dismissible banner (bottom-right) with a Re-authenticate button
- Re-show the banner on subsequent sync/search attempts that hit expired auth
- Clean up stale credential files automatically

**Non-Goals:**
- Auto-retrying auth without user action
- Publishing the Google Cloud app (out of scope)
- Offline mode indicators beyond the banner
- Token refresh scheduling or background renewal

## Decisions

**1. Where to catch the error**
- Catch in `auth.py` `load_credentials()`, wrap in `TokenExpiredError`, clear stale file
- Propagate to `tui_app.py` where UI decides what to show
- Rationale: Single point of auth error detection, UI-agnostic

**2. Banner persistence**
- Mount banner at `TMDApp` level (not inside a screen) so it persists across screen switches
- Use `display = False/True` to show/hide instead of mounting/unmounting
- Rationale: Avoids DOM manipulation overhead, simple reactive toggle

**3. Dismissible but recurring**
- Banner has an X button to dismiss
- On next sync/search attempt that hits expired auth, banner reappears
- Rationale: User can clear visual clutter but won't forget to re-auth indefinitely

**4. No error toast for token expiry**
- `TokenExpiredError` is caught silently in `_startup_sync()` (no `self.notify()`)
- The banner itself is the notification
- Rationale: Avoids double-notification and keeps error path clean

## Risks / Trade-offs

- **[Risk]** User dismisses banner and forgets to re-auth, then wonders why sync stopped → **Mitigation**: Banner reappears on every sync/search attempt
- **[Risk]** Banner overlaps with other UI elements on small terminals → **Mitigation**: Keep banner compact (3 rows), position at bottom-right
- **[Risk]** `invalid_grant` might have other causes (not just expiry) → **Mitigation**: Only catch `invalid_grant`, let other `RefreshError` variants propagate as normal errors
