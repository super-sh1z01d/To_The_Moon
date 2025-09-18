# Requirements Document: Documentation Consolidation

## Introduction

The To The Moon project has accumulated extensive documentation across multiple files and directories, creating fragmentation and maintenance challenges. This specification aims to consolidate, update, and reorganize the documentation into a coherent, maintainable structure that reflects the current state of the system.

## Current Documentation Analysis

### Identified Documentation Files (30+ files):
- **Core Documentation**: README.md, ARCHITECTURE.md, API_REFERENCE.md
- **Development**: DEVELOPMENT.md, conventions.md, Makefile
- **Deployment**: Multiple deployment guides (DEPLOYMENT_*.md, SERVER_*.md)
- **Feature Reports**: Multiple implementation summaries and reports
- **Historical**: Changelogs, migration guides, update instructions
- **Scattered**: docs/, doc/ directories with additional content

### Problems with Current State:
1. **Fragmentation**: Information scattered across 30+ files
2. **Duplication**: Similar information repeated in multiple files
3. **Outdated Content**: Many files reference old system states
4. **Poor Discoverability**: No clear entry point or navigation
5. **Maintenance Burden**: Updates require changes in multiple places

## Requirements

### Requirement 1: Documentation Structure Consolidation

**User Story:** As a developer or operator, I want a clear, organized documentation structure so that I can quickly find the information I need.

#### Acceptance Criteria

1. WHEN I access the project THEN I SHALL find a single, comprehensive README.md that serves as the main entry point
2. WHEN I need technical details THEN I SHALL find them organized in a logical docs/ directory structure
3. WHEN I look for specific information THEN I SHALL find it in predictable locations without searching multiple files
4. WHEN I need to update documentation THEN I SHALL know exactly which file to modify

### Requirement 2: Content Accuracy and Currency

**User Story:** As a user of the system, I want documentation that accurately reflects the current system capabilities so that I can understand and use the system effectively.

#### Acceptance Criteria

1. WHEN I read the documentation THEN it SHALL reflect the current hybrid momentum scoring model
2. WHEN I follow setup instructions THEN they SHALL work with the current codebase
3. WHEN I check API documentation THEN it SHALL include all current endpoints and models
4. WHEN I review architecture information THEN it SHALL describe the current system design

### Requirement 3: Consolidated File Structure

**User Story:** As a maintainer, I want a minimal set of well-organized documentation files so that I can easily keep them updated.

#### Acceptance Criteria

1. WHEN I review the project root THEN I SHALL find no more than 5 documentation files
2. WHEN I need detailed documentation THEN I SHALL find it organized in the docs/ directory
3. WHEN I look for historical information THEN I SHALL find it in a dedicated archive or changelog
4. WHEN I need deployment information THEN I SHALL find it in a single, comprehensive guide

### Requirement 4: Clear Information Hierarchy

**User Story:** As a new team member, I want documentation organized by audience and use case so that I can quickly get up to speed.

#### Acceptance Criteria

1. WHEN I'm a new developer THEN I SHALL find clear getting-started instructions
2. WHEN I'm deploying the system THEN I SHALL find comprehensive deployment documentation
3. WHEN I'm using the API THEN I SHALL find complete API reference documentation
4. WHEN I need to understand the architecture THEN I SHALL find detailed technical documentation

### Requirement 5: Legacy Content Management

**User Story:** As a project maintainer, I want historical documentation preserved but not cluttering the main documentation so that I can reference past decisions without confusion.

#### Acceptance Criteria

1. WHEN I need historical context THEN I SHALL find it in a dedicated archive directory
2. WHEN I'm working with current documentation THEN I SHALL not be distracted by outdated information
3. WHEN I need to reference past implementations THEN I SHALL find them clearly marked as historical
4. WHEN I update documentation THEN I SHALL not need to update multiple historical versions

## Proposed New Structure

### Root Level (Maximum 5 files):
- `README.md` - Main project overview and quick start
- `CHANGELOG.md` - Version history and changes
- `CONTRIBUTING.md` - Development and contribution guidelines
- `LICENSE` - Project license
- `Makefile` - Development commands

### docs/ Directory:
- `docs/ARCHITECTURE.md` - System architecture and design
- `docs/API_REFERENCE.md` - Complete API documentation
- `docs/DEPLOYMENT.md` - Deployment and operations guide
- `docs/DEVELOPMENT.md` - Development setup and guidelines
- `docs/SCORING_MODEL.md` - Hybrid momentum scoring documentation

### archive/ Directory:
- Historical reports and outdated documentation
- Implementation summaries
- Migration guides for past versions

## Success Criteria

1. **Reduced File Count**: From 30+ documentation files to <10 active files
2. **Single Source of Truth**: Each piece of information exists in exactly one place
3. **Current and Accurate**: All documentation reflects the current system state
4. **Easy Navigation**: Clear hierarchy and cross-references
5. **Maintainable**: Updates require changes to minimal number of files

## Out of Scope

- Code documentation (docstrings, inline comments)
- Auto-generated documentation
- External documentation platforms
- Translation to other languages