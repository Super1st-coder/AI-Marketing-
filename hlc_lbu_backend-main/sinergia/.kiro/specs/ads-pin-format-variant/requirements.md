# Requirements Document

## Introduction

This feature introduces the ability to pin a specific media format within an ad variant. Currently, when ad variants are generated, all media formats are created but none are marked as "preferred" or "primary". This feature allows users to select one media format from a variant to be the pinned (primary) format, which will be used as the default display when showing the ad variant across the platform.

## Glossary

- **Ad Variant**: A specific implementation of an ad with unique media elements, channel attributes, and media formats for a particular channel
- **Media Format**: A specific format of an ad (e.g., Instagram portrait, Facebook banner) with its own dimensions, assets, and visual assets
- **Pin**: To mark a specific media format as the primary or preferred format within an ad variant
- **Pinned Format**: The media format currently marked as the primary format for an ad variant
- **Ad Channel**: A record representing an ad variant with its associated media formats, media elements, and channel attributes

## Requirements

### Requirement 1: Pin a Media Format

**User Story:** As an advertiser or agency manager, I want to pin a specific media format within an ad variant, so that the most effective format becomes the default display format.

#### Acceptance Criteria

1. WHEN a user selects a media format to pin within an ad variant, THE System SHALL mark that media format as pinned and unpin any previously pinned format
2. WHILE a media format is pinned, THE System SHALL indicate it is the primary format in all user interfaces
3. WHEN a media format is pinned, THE System SHALL store this preference permanently until explicitly changed
4. WHERE multiple media formats exist in an ad variant, THE System SHALL ensure only one format can be pinned at a time

### Requirement 2: Unpin a Media Format

**User Story:** As an advertiser, I want to remove the pinned status from a media format, so that I can change the primary display format later.

#### Acceptance Criteria

1. WHEN a user selects to unpin the current pinned media format, THE System SHALL remove the pinned status from that format
2. WHEN the pinned status is removed and no other format is pinned, THE System SHALL indicate no format is currently pinned

### Requirement 3: Format Persistence

**User Story:** As a system, I want to ensure pinned format information persists across operations, so that user preferences are not lost during system updates.

#### Acceptance Criteria

1. WHEN an ad variant is saved or updated, THE System SHALL preserve the pinned format information
2. WHEN an ad variant is retrieved for display or editing, THE System SHALL include pinned format information
3. WHERE a media format is updated but remains part of the same ad variant, THE System SHALL preserve the pinned status
4. WHEN an ad variant is duplicated, THE System SHALL copy the pinned format status to the duplicate

### Requirement 4: Format Selection in User Interface

**User Story:** As a user, I want clear visual indication of which format is pinned, so that I can easily identify the primary format.

#### Acceptance Criteria

1. WHEN displaying an ad variant with multiple media formats, THE System SHALL visually indicate which format is pinned
2. WHERE a format is pinned, THE System SHALL display a clear visual marker (icon, label, or highlight)
3. WHEN hovering over or selecting a pinned format, THE System SHALL display an indicator explaining it is the primary format

### Requirement 5: Format Data Structure

**User Story:** As a developer, I want a consistent data structure for pinned format information, so that all components can reliably access this data.

#### Acceptance Criteria

1. WHEN a media format is pinned, THE System SHALL store a boolean `pinned` field on the media format object
2. WHEN retrieving media formats, THE System SHALL include the `pinned` field for each format
3. WHERE a media format does not have pinned status, THE System SHALL default the `pinned` field to false
4. WHEN multiple formats exist, THE System SHALL ensure exactly one format has `pinned` set to true at any time (except when none are pinned)

## Testing Strategy

### Unit Tests
- Test pin format functionality with valid format IDs
- Test unpin format functionality
- Test format data structure persistence

### Integration Tests
- Test end-to-end workflow: generate variant, pin format, verify display
- Test format update with pinned status preserved
- Test duplicate variant with pinned format copied

### Property-Based Tests
- For any ad variant with N formats, pin operation should result in exactly one pinned format
- For any ad variant, unpinning the current format should result in zero pinned formats
- For any ad variant, duplicating it should preserve the pinned format status