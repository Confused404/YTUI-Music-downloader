## 1. Core Fix

- [x] 1.1 Modify `_startup_sync()` to call `self.db.get_pending_songs()` after sync
- [x] 1.2 Combine `new_songs` and `pending_songs` for download manager start decision
- [x] 1.3 Queue all pending songs into download manager if any exist
- [x] 1.4 Show notification when pending songs are queued on startup

## 2. Testing

- [ ] 1.5 Simulate restart with pending songs and verify they get queued
- [ ] 1.6 Simulate restart with no pending songs and verify download manager doesn't start unnecessarily
- [ ] 1.7 Verify permanently failed songs (retry_count >= 3) are not re-queued
- [ ] 1.8 Test mixed scenario: new songs + existing pending songs

**Note:** Tasks 1.5–1.8 require manual runtime testing with actual pending songs in the database.
