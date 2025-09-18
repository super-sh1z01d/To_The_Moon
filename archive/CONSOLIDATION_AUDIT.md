# Documentation Consolidation Audit

## File Categorization Results

### ✅ Core Files to Update and Keep
| File | Status | Action | Target Location |
|------|--------|--------|-----------------|
| README.md | Needs major update | Rewrite | Root |
| ARCHITECTURE.md | Needs update | Update & move | docs/ARCHITECTURE.md |
| API_REFERENCE.md | Needs update | Update & move | docs/API_REFERENCE.md |
| DEVELOPMENT.md | Needs consolidation | Merge & move | docs/DEVELOPMENT.md |
| CHANGELOG.md | Keep | Minor updates | Root |
| conventions.md | Merge | Merge into CONTRIBUTING.md | Root |

### 📦 Files to Archive - Implementation Reports
| File | Category | Archive Location |
|------|----------|------------------|
| DASHBOARD_ENHANCEMENT_SUMMARY.md | Enhancement Report | archive/reports/ |
| IMPLEMENTATION_SUMMARY.md | Implementation Report | archive/reports/ |
| SETTINGS_PAGE_IMPROVEMENT_REPORT.md | Enhancement Report | archive/reports/ |
| TABLE_CLEANUP_SUMMARY.md | Cleanup Report | archive/reports/ |
| FINAL_DASHBOARD_REPORT.md | Enhancement Report | archive/reports/ |
| DOCUMENTATION_UPDATE_REPORT.md | Process Report | archive/reports/ |
| SETTINGS_DESCRIPTIONS_IMPROVEMENT.md | Enhancement Report | archive/reports/ |

### 🔄 Files to Consolidate - Deployment Guides
| File | Content Type | Target |
|------|--------------|--------|
| DEPLOYMENT_GUIDE.md | Main deployment | docs/DEPLOYMENT.md |
| DEPLOYMENT_CHECKLIST.md | Checklist | docs/DEPLOYMENT.md (section) |
| SERVER_DEPLOYMENT_INSTRUCTIONS.md | Server setup | docs/DEPLOYMENT.md (section) |
| UPDATE_INSTRUCTIONS.md | Update process | docs/DEPLOYMENT.md (section) |
| DEPLOYMENT_PLAN.md | Planning doc | archive/deprecated/ |
| DEPLOYMENT_READINESS_REPORT.md | Status report | archive/reports/ |
| DEPLOYMENT_READY_REPORT.md | Status report | archive/reports/ |

### 🗑️ Files to Archive - Outdated Content
| File | Reason | Archive Location |
|------|--------|------------------|
| PARAMETER_REMOVAL_NOTICE.md | Historical notice | archive/deprecated/ |
| MIGRATION_GUIDE.md | Old version migration | archive/migrations/ |
| VOLATILITY_FIXES.md | Specific fix report | archive/reports/ |
| DATA_FILTERING.md | Superseded by code docs | archive/deprecated/ |
| SCORING_POTENTIAL.md | Outdated analysis | archive/deprecated/ |
| USER_VISIBLE_CHANGES.md | Historical changes | archive/deprecated/ |

### 📁 Directory Content Analysis
| Directory | Files | Action |
|-----------|-------|--------|
| docs/ | 2 files | Expand to 6 files |
| doc/ | 1 file | Review and archive |
| Root | 29 .md files | Reduce to 5 files |

## Content Update Requirements

### README.md - Major Rewrite Needed
**Current Issues:**
- References old scoring models
- Missing hybrid momentum information
- Outdated setup instructions
- Incomplete feature list

**Required Updates:**
- [ ] Hybrid momentum scoring model description
- [ ] Current API endpoints
- [ ] Updated deployment methods
- [ ] Recent system improvements (scheduler monitoring, data quality)
- [ ] Correct technology stack

### API_REFERENCE.md - Significant Updates
**Missing Content:**
- [ ] /health/scheduler endpoint
- [ ] Updated token response models (raw_components, smoothed_components)
- [ ] Hybrid momentum scoring parameters
- [ ] Enhanced error responses
- [ ] New admin endpoints

### ARCHITECTURE.md - Major Updates Required
**Outdated Sections:**
- [ ] Scoring model architecture (still shows old model)
- [ ] Missing EWMA smoothing service
- [ ] Missing scheduler health monitoring
- [ ] Missing data quality validation system
- [ ] Missing fallback mechanisms

### DEVELOPMENT.md - Consolidation Needed
**Sources to Merge:**
- Current DEVELOPMENT.md
- conventions.md
- Scattered development info in other files

## Consolidation Strategy

### Phase 1: Structure (Completed)
- [x] Create docs/ directory
- [x] Create archive/ directory
- [x] Create navigation files

### Phase 2: Core Updates (Next)
1. Rewrite README.md with current system state
2. Update and move ARCHITECTURE.md
3. Update and move API_REFERENCE.md
4. Create new SCORING_MODEL.md

### Phase 3: Consolidation
1. Merge deployment guides into docs/DEPLOYMENT.md
2. Merge development docs into docs/DEVELOPMENT.md + CONTRIBUTING.md
3. Create docs/TROUBLESHOOTING.md

### Phase 4: Archival
1. Move implementation reports to archive/reports/
2. Move outdated content to archive/deprecated/
3. Move old migration guides to archive/migrations/

### Phase 5: Cleanup
1. Remove consolidated source files
2. Update cross-references
3. Validate all links

## Success Metrics Tracking

### File Count Reduction
- **Before:** 29 markdown files in root
- **Target:** ≤5 markdown files in root
- **Current:** 29 (not started)

### Content Freshness
- **Before:** ~60% outdated content
- **Target:** 100% current content
- **Current:** Audit complete, updates needed

### Structure Clarity
- **Before:** Fragmented across multiple locations
- **Target:** Clear docs/ hierarchy
- **Current:** Structure created, content migration needed