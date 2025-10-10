# WebSocket Worker PostgreSQL Migration Fix

## Problem

After migrating from SQLite to PostgreSQL, the WebSocket worker (`tothemoon-ws`) was still using the old SQLite database (`dev.db`) because the `DATABASE_URL` environment variable was not set in `/etc/tothemoon.env`.

### Symptoms
- No new tokens appearing in monitoring status
- Last token added was at 09:17 UTC (over 1 hour ago)
- WebSocket worker was running but writing to wrong database

## Root Cause

The WebSocket worker service reads configuration from `/etc/tothemoon.env`, but this file was missing the `DATABASE_URL` variable after the PostgreSQL migration. Without this variable, the application defaults to SQLite (`dev.db`).

## Solution

Added `DATABASE_URL` to `/etc/tothemoon.env`:

```bash
sudo bash -c "echo 'DATABASE_URL=postgresql://tothemoon:tothemoon_secure_pass_2024@localhost/tothemoon_prod' >> /etc/tothemoon.env"
```

Then restarted the WebSocket worker:

```bash
sudo systemctl restart tothemoon-ws
```

## Verification

After the fix:
- WebSocket worker successfully connected to PostgreSQL
- Worker subscribed to Pump.fun migration events
- New tokens will now be added to the correct database

Check worker status:
```bash
sudo systemctl status tothemoon-ws
sudo journalctl -u tothemoon-ws --since "5 minutes ago"
```

## Prevention

When migrating databases in the future:
1. Update all environment files (`/etc/tothemoon.env`, `.env`)
2. Restart ALL services (main app + workers)
3. Verify each service is using the correct database

## Related Files
- `/etc/tothemoon.env` - Environment configuration for systemd services
- `/etc/systemd/system/tothemoon-ws.service` - WebSocket worker service definition
- `src/core/config.py` - Application configuration loader
- `src/adapters/db/base.py` - Database connection setup
