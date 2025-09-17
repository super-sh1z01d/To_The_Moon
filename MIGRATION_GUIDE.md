# Migration Guide

## Upgrading to Version 2.0.0 (Hybrid Momentum)

This guide helps you migrate from the legacy scoring system to the new Hybrid Momentum model.

## Overview

Version 2.0.0 introduces:
- **Hybrid Momentum scoring model** with 4 components
- **Enhanced dashboard** with component visualization
- **EWMA smoothing** for score stability
- **Multiple model support** with runtime switching

## Migration Steps

### 1. Backup Current System

```bash
# Backup database
pg_dump your_database > backup_$(date +%Y%m%d).sql

# Backup configuration
cp /etc/tothemoon.env /etc/tothemoon.env.backup

# Backup application directory
tar -czf tothemoon_backup_$(date +%Y%m%d).tar.gz /srv/tothemoon
```

### 2. Update Application Code

```bash
# Navigate to application directory
cd /srv/tothemoon

# Pull latest changes
sudo -u tothemoon git pull origin main

# Update Python dependencies
sudo -u tothemoon venv/bin/pip install -r requirements.txt
```

### 3. Apply Database Migrations

```bash
# Apply new schema changes
sudo -u tothemoon bash -c "source venv/bin/activate && python -m alembic upgrade head"
```

**New database fields added:**
- `token_scores.raw_components` (JSON) - Raw component values
- `token_scores.smoothed_components` (JSON) - EWMA smoothed components  
- `token_scores.scoring_model` (VARCHAR) - Model used for calculation

### 4. Update Frontend

```bash
# Rebuild frontend with new components
cd /srv/tothemoon/frontend
sudo -u tothemoon npm ci
sudo -u tothemoon npm run build
cd -
```

### 5. Update Configuration

Add new settings to your environment file:

```bash
# Edit configuration
sudo nano /etc/tothemoon.env
```

Add these optional settings:
```bash
# Hybrid Momentum Model Settings
SCORING_MODEL_ACTIVE=hybrid_momentum
W_TX=0.25
W_VOL=0.25  
W_FRESH=0.25
W_OI=0.25
EWMA_ALPHA=0.3
FRESHNESS_THRESHOLD_HOURS=6.0

# Data Filtering
MIN_POOL_LIQUIDITY_USD=500
MAX_PRICE_CHANGE_5M=0.5
MIN_SCORE_CHANGE=0.05
```

### 6. Restart Services

```bash
# Restart application services
sudo systemctl restart tothemoon.service
sudo systemctl restart tothemoon-ws.service

# Check service status
sudo systemctl status tothemoon.service
sudo systemctl status tothemoon-ws.service
```

### 7. Verify Migration

```bash
# Check application health
curl http://localhost:8000/health

# Verify active scoring model
curl http://localhost:8000/settings/scoring_model_active

# Test API with new fields
curl "http://localhost:8000/tokens/?limit=1" | jq '.items[0] | {score, raw_components, smoothed_components, scoring_model}'
```

## Configuration Migration

### Legacy Settings Mapping

Old settings are automatically mapped to new structure:

| Legacy Setting | New Setting | Notes |
|----------------|-------------|-------|
| `weight_s` | `weight_s` | Preserved for legacy model |
| `weight_l` | `weight_l` | Preserved for legacy model |
| `weight_m` | `weight_m` | Preserved for legacy model |
| `weight_t` | `weight_t` | Preserved for legacy model |
| N/A | `w_tx` | New: Transaction Acceleration weight |
| N/A | `w_vol` | New: Volume Momentum weight |
| N/A | `w_fresh` | New: Token Freshness weight |
| N/A | `w_oi` | New: Orderflow Imbalance weight |
| N/A | `ewma_alpha` | New: EWMA smoothing parameter |
| N/A | `freshness_threshold_hours` | New: Freshness detection threshold |

### API Changes

#### New Endpoints
- `POST /settings/model/switch` - Switch between scoring models
- `GET /settings/weights` - Get all model weights
- `GET /settings/validation/errors` - Get validation errors

#### Enhanced Endpoints
- `GET /tokens/` - Now includes `raw_components`, `smoothed_components`, `scoring_model`, `created_at`
- `GET /tokens/{mint}` - Enhanced with component breakdown
- `PUT /settings/{key}` - Enhanced validation for new settings

#### Deprecated Endpoints
None - full backward compatibility maintained.

## Frontend Migration

### New Components
- **ScoreCell** - Enhanced score display with component breakdown
- **ComponentsCell** - Individual component visualization
- **AgeCell** - Token age with freshness indicators

### New Features
- **Adaptive table** - Automatically shows/hides columns based on active model
- **Component sorting** - Sort by TX, Vol, Fresh, OI components
- **Fresh token filter** - Filter tokens by age
- **Visual indicators** - Color coding and progress bars

### Removed Features
- **Price delta columns** - "Δ 5м / 15м" and "Транз. 5м" columns removed for cleaner UI

## Data Migration

### Automatic Migration
- Existing `token_scores` records are preserved
- New fields are populated as `NULL` initially
- Legacy scores continue to work unchanged

### Component Population
New component data will be populated as tokens are updated:

1. **Immediate**: New tokens get full component data
2. **Gradual**: Existing tokens get components on next score update
3. **Manual**: Force update with `POST /tokens/{mint}/refresh`

### Score Recalculation
To populate components for all existing tokens:

```bash
# Trigger full recalculation
curl -X POST http://localhost:8000/admin/recalculate

# Or use utility script
sudo -u tothemoon bash -c "source venv/bin/activate && python scripts/compute_scores.py --all"
```

## Model Switching

### Switch to Hybrid Momentum
```bash
curl -X POST http://localhost:8000/settings/model/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "hybrid_momentum"}'
```

### Switch to Legacy (if needed)
```bash
curl -X POST http://localhost:8000/settings/model/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "legacy"}'
```

### Verify Switch
```bash
# Check active model
curl http://localhost:8000/settings/scoring_model_active

# Check frontend adaptation
# Open http://localhost:8000/app and verify table columns
```

## Troubleshooting

### Common Issues

#### 1. Migration Fails
```bash
# Check migration status
sudo -u tothemoon bash -c "source venv/bin/activate && python -m alembic current"

# View migration history
sudo -u tothemoon bash -c "source venv/bin/activate && python -m alembic history"

# Force migration (if safe)
sudo -u tothemoon bash -c "source venv/bin/activate && python -m alembic upgrade head"
```

#### 2. Services Won't Start
```bash
# Check service logs
sudo journalctl -u tothemoon.service -n 50
sudo journalctl -u tothemoon-ws.service -n 50

# Check configuration
sudo -u tothemoon bash -c "source venv/bin/activate && python -c 'from src.core.config import settings; print(settings.dict())'"
```

#### 3. Frontend Issues
```bash
# Rebuild frontend
cd /srv/tothemoon/frontend
sudo -u tothemoon rm -rf node_modules dist
sudo -u tothemoon npm install
sudo -u tothemoon npm run build

# Check static files
ls -la /srv/tothemoon/frontend/dist/
```

#### 4. API Returns Old Format
```bash
# Verify model is switched
curl http://localhost:8000/settings/scoring_model_active

# Force token refresh
curl -X POST http://localhost:8000/tokens/YOUR_TOKEN_MINT/refresh

# Check API response format
curl "http://localhost:8000/tokens/?limit=1" | jq '.items[0] | keys'
```

### Rollback Procedure

If you need to rollback to the previous version:

```bash
# 1. Stop services
sudo systemctl stop tothemoon.service tothemoon-ws.service

# 2. Restore database
psql your_database < backup_YYYYMMDD.sql

# 3. Restore configuration
sudo cp /etc/tothemoon.env.backup /etc/tothemoon.env

# 4. Checkout previous version
cd /srv/tothemoon
sudo -u tothemoon git checkout previous_version_tag

# 5. Restore dependencies
sudo -u tothemoon venv/bin/pip install -r requirements.txt

# 6. Rebuild frontend
cd frontend
sudo -u tothemoon npm ci
sudo -u tothemoon npm run build
cd -

# 7. Restart services
sudo systemctl start tothemoon.service tothemoon-ws.service
```

## Performance Considerations

### Database Performance
- New JSON fields are indexed for performance
- Component calculations are optimized
- EWMA smoothing adds minimal overhead

### Memory Usage
- In-memory EWMA state is lightweight
- Component data adds ~200 bytes per token score
- Overall memory impact is minimal

### API Performance
- Response times may increase by 1-2ms due to additional fields
- Database queries are optimized with proper indexing
- Frontend rendering performance improved due to removed columns

## Testing Migration

### Test Environment
Always test migration in a staging environment first:

```bash
# Create test database
createdb tothemoon_test

# Test migration
DATABASE_URL=postgresql://user:pass@localhost/tothemoon_test python -m alembic upgrade head

# Test API
DATABASE_URL=postgresql://user:pass@localhost/tothemoon_test python -m uvicorn src.app.main:app --port 8001
```

### Validation Checklist
- [ ] Database migration completes without errors
- [ ] All services start successfully
- [ ] API returns new fields in responses
- [ ] Frontend displays component columns (Hybrid Momentum mode)
- [ ] Frontend hides component columns (Legacy mode)
- [ ] Model switching works via API
- [ ] Settings validation works correctly
- [ ] Token refresh populates components
- [ ] Logs show no errors

## Support

If you encounter issues during migration:

1. **Check logs**: `sudo journalctl -u tothemoon.service -f`
2. **Verify configuration**: Review `/etc/tothemoon.env`
3. **Test API**: Use curl to test endpoints
4. **Check database**: Verify migration applied correctly
5. **Review documentation**: Check README.md and API_REFERENCE.md

For additional support, check the GitHub repository issues or create a new issue with:
- Migration step where issue occurred
- Error messages from logs
- System configuration details
- Database migration status