# Design Document

## Overview

Fix the SettingsService.get() method signature mismatch that is causing scoring system failures. The current code calls `self.settings.get(key, default_value)` but the method only accepts `(self, key)`. This causes the error "SettingsService.get() takes 2 positional arguments but 3 were given".

## Architecture

The issue is in the method signature inconsistency:
- **Current calls**: `self.settings.get("key", "default_value")` (2 arguments)
- **Actual method**: `def get(self, key: str) -> Optional[str]` (1 argument)

## Components and Interfaces

### SettingsService.get() Method
- **Current signature**: `get(self, key: str) -> Optional[str]`
- **Problem**: Code expects it to accept default values like dict.get()
- **Solution**: Modify calling code to handle None returns properly

### Affected Files
1. `src/domain/scoring/scoring_service.py` - Multiple calls with default values
2. `src/domain/scoring/hybrid_momentum_model.py` - Weight configuration calls

## Data Models

No data model changes required. The SettingsService already handles defaults through:
- `DEFAULT_SETTINGS` dictionary
- Internal caching mechanism
- Proper None handling

## Error Handling

### Current Error Pattern
```python
# This causes the error:
value = self.settings.get("key", "default")
```

### Fixed Pattern
```python
# This will work:
value = self.settings.get("key") or "default"
```

## Testing Strategy

1. **Unit Tests**: Verify all settings calls work correctly
2. **Integration Tests**: Test scoring system with various settings
3. **Error Handling**: Ensure graceful handling of missing settings
4. **Regression Tests**: Verify existing functionality still works

## Implementation Plan

### Phase 1: Fix Method Calls
- Replace all `self.settings.get(key, default)` calls
- Use `self.settings.get(key) or default` pattern
- Maintain backward compatibility

### Phase 2: Validation
- Test all scoring scenarios
- Verify settings are loaded correctly
- Ensure no performance regression

### Phase 3: Cleanup
- Add type hints for clarity
- Update documentation
- Add defensive programming patterns