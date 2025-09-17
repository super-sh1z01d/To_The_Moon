# 🚀 Deployment Checklist - Parameter Cleanup

## 📋 Pre-Deployment Checks

### ✅ Code Quality
- [x] Python syntax validation passed
- [x] Frontend build successful
- [x] No import errors
- [x] Legacy compatibility maintained

### ✅ Changes Summary
- [x] Removed `max_price_change_5m` from Hybrid Momentum model
- [x] Updated settings UI (field removed)
- [x] Updated documentation
- [x] Maintained legacy compatibility
- [x] Added migration notes

### ✅ Files Modified
- [x] `src/domain/settings/defaults.py` - removed parameter
- [x] `src/domain/settings/service.py` - removed validation
- [x] `src/domain/scoring/scoring_service.py` - updated Hybrid Momentum
- [x] `src/domain/metrics/enhanced_dex_aggregator.py` - removed parameter
- [x] `src/app/routes/tokens.py` - legacy compatibility
- [x] `frontend/src/pages/Settings.tsx` - removed UI field
- [x] Documentation files updated

## 🔄 Deployment Steps

### 1. Backup Current State
```bash
# Create backup of current deployment
sudo cp -r /opt/to_the_moon /opt/to_the_moon_backup_$(date +%Y%m%d_%H%M%S)
```

### 2. Stop Services
```bash
sudo systemctl stop to-the-moon
sudo systemctl stop to-the-moon-worker
```

### 3. Deploy Code
```bash
cd /opt/to_the_moon
git pull origin main
```

### 4. Update Dependencies (if needed)
```bash
python3 -m pip install -r requirements.txt
```

### 5. Build Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### 6. Database Migration (if needed)
```bash
# No database changes required for this update
python3 -m alembic upgrade head
```

### 7. Start Services
```bash
sudo systemctl start to-the-moon
sudo systemctl start to-the-moon-worker
```

### 8. Verify Deployment
```bash
sudo systemctl status to-the-moon
sudo systemctl status to-the-moon-worker
curl -f http://localhost:8000/health || echo "Health check failed"
```

## 🧪 Post-Deployment Testing

### API Tests
- [ ] GET /health - service health
- [ ] GET /settings - settings load correctly
- [ ] GET /tokens - token list loads
- [ ] POST /tokens/{mint}/score - scoring works
- [ ] Settings UI loads without max_price_change_5m field

### Functional Tests
- [ ] Hybrid Momentum scoring works
- [ ] Legacy scoring still works
- [ ] Settings can be updated
- [ ] Dashboard displays correctly
- [ ] No console errors in browser

## 🔍 Monitoring Points

### Logs to Watch
```bash
# Application logs
sudo journalctl -u to-the-moon -f

# Worker logs  
sudo journalctl -u to-the-moon-worker -f

# Check for errors
sudo journalctl -u to-the-moon --since "5 minutes ago" | grep -i error
```

### Key Metrics
- [ ] Scoring service response times
- [ ] Database query performance
- [ ] Memory usage stable
- [ ] No increase in error rates

## 🚨 Rollback Plan

If issues occur:

### Quick Rollback
```bash
sudo systemctl stop to-the-moon to-the-moon-worker
sudo rm -rf /opt/to_the_moon
sudo mv /opt/to_the_moon_backup_* /opt/to_the_moon
sudo systemctl start to-the-moon to-the-moon-worker
```

### Verify Rollback
```bash
curl -f http://localhost:8000/health
# Check that max_price_change_5m field is back in settings
```

## 📝 Expected Behavior Changes

### What Users Will See
- ❌ "Максимальное изменение цены (%)" field removed from settings
- ✅ All other functionality unchanged
- ✅ Hybrid Momentum scoring continues to work
- ✅ Legacy scoring continues to work

### What Won't Change
- ✅ Token scoring accuracy
- ✅ API endpoints
- ✅ Database structure
- ✅ Performance characteristics

## 🎯 Success Criteria

- [ ] Services start successfully
- [ ] No errors in logs for 10 minutes
- [ ] Settings UI loads without removed field
- [ ] Scoring continues to work normally
- [ ] Dashboard functions correctly
- [ ] Memory usage remains stable

---
**Deployment Date:** $(date)  
**Version:** 2.0.0 - Parameter Cleanup  
**Estimated Downtime:** < 2 minutes  
**Risk Level:** Low (no breaking changes)