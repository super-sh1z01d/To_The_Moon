# Database Password Fix

## Problem

After PostgreSQL migration, the main application service was failing with authentication errors:
```
password authentication failed for user "tothemoon"
```

This caused:
- 500 errors on all API endpoints
- Frontend unable to load tokens
- Scheduler jobs failing

## Root Cause

The `/etc/tothemoon.env` file (used by systemd services) had an incorrect PostgreSQL password:
- **Incorrect**: `tothemoon_secure_pass_2024`
- **Correct**: `ToTheMoon2025Secure`

The `.env` file in the project directory had the correct password, but systemd services use `/etc/tothemoon.env`.

## Solution

Updated the DATABASE_URL in `/etc/tothemoon.env`:

```bash
sudo sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql://tothemoon:ToTheMoon2025Secure@localhost:5432/tothemoon_prod|" /etc/tothemoon.env
```

Then restarted all services:

```bash
sudo systemctl restart tothemoon tothemoon-ws
```

## Verification

Test API endpoint:
```bash
curl http://localhost:8000/tokens?status=active&limit=5
```

Should return JSON with token data instead of 500 error.

## Related Issues

This was the second database configuration issue after PostgreSQL migration:
1. **WebSocket worker** - Missing DATABASE_URL entirely (fixed earlier)
2. **Main service** - Wrong password in DATABASE_URL (fixed now)

## Prevention

When updating database credentials:
1. Update `.env` in project directory
2. Update `/etc/tothemoon.env` for systemd services
3. Restart ALL services
4. Verify each service connects successfully

## Files Affected

- `/etc/tothemoon.env` - Systemd service environment
- `/srv/tothemoon/.env` - Project environment (already correct)
