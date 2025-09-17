# Requirements Document

## Introduction

Fix critical error in SettingsService.get() method calls that is preventing token scoring from working. The error "SettingsService.get() takes 2 positional arguments but 3 were given" is occurring during token score calculations, causing the scoring system to fail.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want the token scoring system to work without errors, so that tokens can be properly scored and displayed.

#### Acceptance Criteria

1. WHEN the scoring system processes tokens THEN it SHALL NOT throw SettingsService.get() argument errors
2. WHEN SettingsService.get() is called THEN it SHALL use the correct number of arguments
3. WHEN token scoring runs THEN it SHALL complete successfully without errors

### Requirement 2

**User Story:** As a developer, I want all SettingsService.get() calls to use consistent method signatures, so that the code is maintainable and error-free.

#### Acceptance Criteria

1. WHEN reviewing SettingsService.get() calls THEN all calls SHALL use the correct signature
2. WHEN SettingsService.get() is called THEN it SHALL accept only (self, key) parameters
3. WHEN default values are needed THEN the code SHALL handle them appropriately

### Requirement 3

**User Story:** As a user, I want to see token scores calculated and displayed, so that I can make informed trading decisions.

#### Acceptance Criteria

1. WHEN tokens are processed THEN they SHALL have calculated scores
2. WHEN viewing the token list THEN scores SHALL be visible and accurate
3. WHEN the scoring system runs THEN it SHALL process all tokens without errors