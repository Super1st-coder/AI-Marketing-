# Implementation Plan: Ad Variant Pin Format Feature

## Overview

This implementation plan covers the pin format feature for ad variants. The feature enables pinning a specific media format within an ad variant, which will be used as the default display format. The implementation focuses on the Use Cases layer since the endpoint and data structures already exist.

## Tasks

- [x] 1. Implement PinFormatAdVariantUseCase
  - [x] 1.1 Add imports for required repositories (AccountRepository, CampaignRepository, AdChannelRepository, BrandRepository, AdRepository)
    - _Requirements: Architecture layering - Use Cases layer_
  
  - [x] 1.2 Implement __init__ method to initialize all repositories
    - Initialize self.account_repo = AccountRepository()
    - Initialize self.campaign_repo = CampaignRepository()
    - Initialize self.ad_channel_repo = AdChannelRepository()
    - Initialize self.brand_repo = BrandRepository()
    - Initialize self.ad_repo = AdRepository()
    - _Requirements: Architecture layering - Use Cases layer_
  
  - [x] 1.3 Implement parameter validation
    - Extract brand_id, campaign_id, ad_id, channel_id, variant_id, format_id from payload
    - Check all parameters are present, raise ParametersNotFoundException if missing
    - _Requirements: 1.1, 1.2_
  
  - [x] 1.4 Implement account validation
    - Get account by email using self.account_repo.get_by_email(self.account_email)
    - If account not found, raise DataNotFoundException
    - Extract parent_account_id from account attributes
    - _Requirements: 1.3_
  
  - [x] 1.5 Implement campaign ownership validation
    - Call self.campaign_repo.get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)
    - If campaign not found, raise DataNotFoundException with appropriate message
    - _Requirements: 1.3_
  
  - [x] 1.6 Implement ad existence validation
    - Populate: ['ad_set_ref2.media_platform_project_id', 'channel_ref']
    - Call self.ad_repo.get_by_id(ad_id, populate)
    - If ad not found, raise DataNotFoundException
    - _Requirements: 1.3_
  
  - [x] 1.7 Implement ad_variant existence validation
    - Call self.ad_channel_repo.get_by_id_and_ad_and_channel(variant_id, ad_id, channel_id)
    - If ad_channel not found, raise DataNotFoundException
    - _Requirements: 1.3_
  
  - [x] 1.8 Validate format_id exists in media_formats
    - Extract media_formats array from ad_channel attributes
    - Check if format_id exists in the formats array
    - If not found, raise DataNotFoundException('Format not found in ad variant')
    - _Requirements: 1.3_
  
  - [x] 1.9 Find currently pinned format (if any)
    - Use next() to find first format with pinned=True
    - Store the format ID or None if no pinned format exists
    - _Requirements: 1.4, 2.1_
  
  - [x] 1.10 Update pinned status for all formats
    - Iterate through all formats in media_formats
    - For each format, create a copy with pinned=True only if it matches format_id
    - Set pinned=False for all other formats
    - _Requirements: 1.4, 2.1_
  
  - [x] 1.11 Save updated media_formats to Strapi
    - Prepare update_data = {'media_formats': updated_formats}
    - Call self.ad_channel_repo.update(variant_id, update_data)
    - If update fails (returns False/None), raise DataNotFoundException
    - _Requirements: 1.4_
  
  - [x] 1.12 Build and return response
    - Return dict with ok=1 and data containing:
      - variant_id
      - pinned_format_id (the requested format_id)
      - previous_pinned_format_id (the previously pinned format, or None)
      - formats array with all format details (id, uid, unit, width, height, errors, pinned, visual_id, sharing_id, visual_url, preview_url)
    - _Requirements: 1.4, 1.5_

- [x] 2. Write unit tests for PinFormatAdVariantUseCase
  - [x] 2.1 Test successful pin when no format is pinned
    - Mock all repositories to return valid data
    - Call execute with valid payload
    - Verify response contains pinned_format_id and formats with correct pinned status
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 1.4_
  
  - [x] 2.2 Test successful pin when another format is already pinned
    - Mock ad_channel with one format having pinned=True
    - Call execute to pin a different format
    - Verify response contains correct previous_pinned_format_id
    - Verify only the new format has pinned=True
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 1.4, 2.1_
  
  - [x] 2.3 Test pin non-existent format raises error
    - Mock ad_channel with media_formats but request invalid format_id
    - Call execute and assert DataNotFoundException is raised
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 1.3_
  
  - [x] 2.4 Test unauthorized account access raises error
    - Mock account_repo to return None
    - Call execute and assert DataNotFoundException is raised
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 1.3_
  
  - [x] 2.5 Test campaign not found raises error
    - Mock account to exist, but campaign_repo to return None
    - Call execute and assert DataNotFoundException is raised
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 1.3_
  
  - [x] 2.6 Test ad not found raises error
    - Mock account and campaign to exist, but ad_repo to return None
    - Call execute and assert DataNotFoundException is raised
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 1.3_
  
  - [x] 2.7 Test variant not found raises error
    - Mock account, campaign, ad to exist, but ad_channel_repo to return None
    - Call execute and assert DataNotFoundException is raised
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 1.3_

- [x] 3. Write property-based tests for PinFormatAdVariantUseCase
  - [x] 3.1 Test pin invariant (Property 1)
    - **Property 1: Pin invariant**
    - **Validates: Requirements 1.4**
    - For any ad variant and valid format ID, pinning a format results in exactly one pinned format
    - Generate random variants and format IDs, call pin operation
    - Assert sum of pinned formats == 1
    - _Requirements: 1.4_
  
  - [x] 3.2 Test pin-unpin round trip (Property 3)
    - **Property 3: Round trip preservation**
    - **Validates: Requirements 2.1**
    - For any ad variant, pinning format A then unpinning results in no pinned formats
    - Generate random variant, pin format, then unpin format
    - Assert sum of pinned formats == 0 after unpin
    - _Requirements: 2.1_
  
  - [x] 3.3 Test pin idempotence (Property 4)
    - **Property 4: Idempotence**
    - **Validates: Requirements 1.1, 1.3**
    - For any ad variant and format ID, pinning the same format twice produces same result
    - Generate random variant, pin format twice
    - Assert both responses have same pinned_format_id
    - _Requirements: 1.1, 1.3_

- [x] 4. Write integration tests
  - [x] 4.1 End-to-end workflow test
    - Set up valid test data (brand, campaign, ad, channel, variant)
    - Call pin_format endpoint with valid payload
    - Verify response returns correct data structure
    - Verify pinned status is persisted by fetching variant again
    - _Requirements: 1.4_

- [x] 5. Implement UnpinFormatAdVariantUseCase (optional)
  - [x] 5.1 Implement __init__ method (reuse same repositories as PinFormatAdVariantUseCase)
    - _Requirements: Architecture layering - Use Cases layer_
  
  - [x] 5.2 Implement parameter validation (same as PinFormatAdVariantUseCase but without format_id)
    - Extract brand_id, campaign_id, ad_id, channel_id, variant_id
    - Validate all required parameters
    - _Requirements: 2.1_
  
  - [x] 5.3 Implement account and ad_variant validation
    - Reuse account validation from PinFormatAdVariantUseCase
    - Reuse ad_variant validation from PinFormatAdVariantUseCase
    - _Requirements: 2.1_
  
  - [x] 5.4 Find currently pinned format (if any)
    - Extract media_formats from ad_channel
    - Use next() to find first format with pinned=True
    - Store format ID or None if no pinned format
    - _Requirements: 2.1_
  
  - [x] 5.5 Set all formats to pinned=false
    - Iterate through all formats
    - Create copies with pinned=False
    - _Requirements: 2.1_
  
  - [x] 5.6 Save to Strapi and return response
    - Update ad_channel with all formats pinned=false
    - Return response with previous_pinned_format_id (can be None)
    - _Requirements: 2.1_

- [x] 6. Write unit tests for UnpinFormatAdVariantUseCase (optional)
  - [x] 6.1 Test unpin when format is pinned
    - Mock ad_channel with one format pinned=True
    - Call execute
    - Verify response contains correct previous_pinned_format_id
    - Verify all formats now have pinned=False
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 2.1_
  
  - [x] 6.2 Test unpin when no format is pinned
    - Mock ad_channel with all formats pinned=False
    - Call execute
    - Verify response contains previous_pinned_format_id=None
    - Verify all formats still have pinned=False
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 2.1_
  
  - [x] 6.3 Test unauthorized access raises error
    - Mock account_repo to return None
    - Call execute and assert DataNotFoundException is raised
    - File location: `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`
    - _Requirements: 2.1_

- [x] 7. Write property-based tests for UnpinFormatAdVariantUseCase (optional)
  - [x] 7.1 Test unpin invariant (Property 2)
    - **Property 2: Unpin invariant**
    - **Validates: Requirements 2.2**
    - For any ad variant, unpinning results in zero pinned formats
    - Generate random variants (with or without pinned format)
    - Call unpin operation
    - Assert sum of pinned formats == 0
    - _Requirements: 2.2_

- [x] 8. Add API endpoint for unpin_format (optional)
  - [x] 8.1 Create UnpinFormatAdVariantStruct model
    - Define model with brand_id, campaign_id, ad_id, channel_id, variant_id fields
    - Add to ad.py resources file
    - _Requirements: Architecture layering - Resources layer_
  
  - [x] 8.2 Add /hiluca/brand/ad/variant/unpin_format endpoint
    - Create new route class HilucaResourceAdChannelVariantUnpinFormat
    - Add POST method with @ad_ns.doc decorator
    - Use @v2_api.expect(UnpinFormatAdVariantStruct)
    - Implement JWT authentication and access check
    - Call UnpinFormatAdVariantUseCase and return response
    - _Requirements: Architecture layering - Resources layer_

- [x] 9. Implement duplicate variant preserves pinned status (optional enhancement)
  - [x] 9.1 Create _preserve_pinned_format helper method
    - Takes source_variant_id and new_variant_id as parameters
    - Fetch source variant's media_formats
    - Find format with pinned=True (if any)
    - Update new variant's formats to match pinned status
    - Call ad_channel_repo.update on new variant
    - _Requirements: 3.1_
  
  - [x] 9.2 Integrate into variant duplication workflow
    - Locate where variant duplication occurs in Fury job
    - Call _preserve_pinned_format after creating duplicate
    - _Requirements: 3.1_

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5", "1.6", "1.7"] },
    { "id": 3, "tasks": ["1.8", "1.9"] },
    { "id": 4, "tasks": ["1.10", "1.11", "1.12"] },
    { "id": 5, "tasks": ["2.1", "2.2"] },
    { "id": 6, "tasks": ["2.3", "2.4", "2.5", "2.6", "2.7"] },
    { "id": 7, "tasks": ["3.1", "3.2", "3.3"] },
    { "id": 8, "tasks": ["4.1"] },
    { "id": 9, "tasks": ["5.1", "5.2", "5.3"] },
    { "id": 10, "tasks": ["5.4", "5.5", "5.6"] },
    { "id": 11, "tasks": ["6.1", "6.2", "6.3"] },
    { "id": 12, "tasks": ["7.1"] },
    { "id": 13, "tasks": ["8.1", "8.2"] },
    { "id": 14, "tasks": ["9.1", "9.2"] }
  ]
}
```

## Notes

1. **PBT Configuration**: Property-based tests should use fast-check or pytest-quickcheck with minimum 100 iterations per property.

2. **Test Tagging**: Each property-based test should be tagged with `Feature: ads-pin-format-variant, Property N: {property_text}`.

3. **Mock Strategy**: For unit tests, mock all repositories at the class level using unittest.mock.patch or pytest-mock.

4. **Error Testing**: For error cases, use pytest.raises or unittest.assertRaises to verify correct exceptions are raised.

5. **Repository Patterns**: Follow existing repository patterns in ad_set.py and other use cases for consistent error handling and data retrieval.

6. **No Breaking Changes**: The implementation should not break existing ad variant functionality.

7. **UI Integration**: The frontend UI should be updated to:
   - Display a visual indicator (icon, badge, highlight) on the pinned format
   - Show tooltip explaining the pinned format is the primary display
   - Allow users to pin by clicking on a format card
   - (Optional) Provide unpin button/menu option