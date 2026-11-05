# Design Document: Ad Variant Pin Format Feature

## Overview

This feature enables pinning/unpinning of specific media formats within an ad variant. Currently, when ad variants are generated, all media formats are created but none are marked as "preferred" or "primary". This feature allows users to select one media format from a variant to be the pinned (primary) format, which will be used as the default display when showing the ad variant across the platform.

Key aspects:
- Only the pinned status can be changed; formats cannot be deleted
- Exactly one format can be pinned at a time (except when none are pinned)
- Pinned status persists across ad variant duplication
- Visual indication of pinned format in user interfaces

## Architecture

### Current Architecture

The Sinergia project follows a clean layered architecture pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                   Flask Resources Layer                         │
│  sinergia/app/v2/resources/ad.py                                │
│  - HTTP endpoints for ad operations                            │
│  - Request validation using Flask-RESTPlus structs            │
│  - Authentication and authorization checks                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Use Cases Layer (Business Logic)              │
│  sinergia/app/v2/use_cases/ad.py                                │
│  - PinFormatAdVariantUseCase (to be implemented)               │
│  - Business validation and coordination                        │
│  - Orchestration of repository calls                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Repository Layer (Data Access)                │
│  sinergia/app/v2/repository/*                                   │
│  - AccountRepository, CampaignRepository                       │
│  - AdRepository, AdChannelRepository                           │
│  - Direct Strapi API interactions                              │
└─────────────────────────────────────────────────────────────────┘
```

### Component Flow

```
User Request
     │
     ▼
┌────────────────────────────────────────┐
│  Flask Resource Endpoint               │
│  POST /hiluca/brand/ad/variant/pin_format
│  - Validates auth & permissions        │
│  - Extracts payload from request       │
└────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────┐
│  PinFormatAdVariantUseCase             │
│  - Validates account access            │
│  - Validates campaign ownership        │
│  - Validates ad_channel existence      │
│  - Validates format_id in media_formats│
│  - Updates pinned status               │
└────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────┐
│  Repository Layer                      │
│  ad_channel_repo.update()              │
│  - Updates ad_channel in Strapi        │
└────────────────────────────────────────┘
     │
     ▼
  Response with updated data
```

### New Component

The `PinFormatAdVariantUseCase` class already exists in `sinergia/app/v2/use_cases/ad.py` (currently as an empty class) and needs to be implemented with the business logic for pinning media formats.

## Components and Interfaces

### 1. PinFormatAdVariantUseCase

**Location**: `sinergia/app/v2/use_cases/ad.py`

**Purpose**: Handle the business logic for pinning a specific media format within an ad variant. This is a pure business logic component that validates the request and coordinates repository calls without knowing about HTTP details.

**Dependencies**:
- `AccountRepository` - Validate account access to campaign
- `CampaignRepository` - Validate campaign ownership
- `AdChannelRepository` - Retrieve and update ad_channel with media_formats
- `BrandRepository` - Validate brand exists
- `AdRepository` - Validate ad exists

**Method Signature**:
```python
class PinFormatAdVariantUseCase:
    def __init__(self, account_email: str):
        self.account_email = account_email
        # Initialize repositories
    
    def execute(self, payload: dict) -> dict:
        """
        Args:
            payload: {
                'brand_id': int,
                'campaign_id': int,
                'ad_id': int,
                'channel_id': int,
                'variant_id': int,      # ad_channel ID
                'format_id': str        # media format ID to pin (e.g., 'facebook-post')
            }
        
        Returns:
            {
                'ok': 1,
                'data': {
                    'variant_id': int,
                    'pinned_format_id': str,
                    'previous_pinned_format_id': str | None,
                    'formats': [
                        {
                            'id': str,          # Format identifier (e.g., 'facebook-post')
                            'uid': str,         # Unique ID
                            'unit': str,        # Measurement unit (e.g., 'px')
                            'width': int,
                            'height': int,
                            'errors': list,
                            'pinned': bool,
                            'visual_id': str,
                            'sharing_id': str,
                            'visual_url': str,
                            'preview_url': str
                        }
                    ]  # Updated formats array
                }
            }
        
        Raises:
            ParametersNotFoundException: Missing required parameters
            DataNotFoundException: Validation failures
        """
```

**Validation Rules**:
1. Account must have access to the campaign (parent account check)
2. Ad channel (variant) must exist and belong to the specified ad and channel
3. Requested `format_id` must exist in the ad channel's `media_formats` array
4. The `pinned` field already exists on each format and is currently always `false`

### 2. Existing API Endpoint

**Location**: `sinergia/app/v2/resources/ad.py`

**Endpoint**: `POST /hiluca/brand/ad/variant/pin_format`

This endpoint already exists in the resources file:

```python
@ad_ns.route('/hiluca/brand/ad/variant/pin_format')
class HilucaResourceAdChannelVariantSelect(ProxySecureResource): 
    @v2_api.expect(PinFormatAdVariantStruct)
    def post(self):
        user_id = security_credentials['username']
        payload = request.json
        data = PinFormatAdVariantUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200
```

**Request Structure** (`PinFormatAdVariantStruct` - already defined):
```python
PinFormatAdVariantStruct = v2_api.model('PinFormatAdVariantStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),  # ad_channel ID
    'format_id': fields.String()     # media format ID to pin
})
```

**Response Structure**:
```json
{
  "ok": 1,
  "data": {
    "variant_id": 123,
    "pinned_format_id": "facebook-post",
    "previous_pinned_format_id": "instagram-portrait",
    "formats": [
      {
        "id": "facebook-post",
        "uid": "45124a95-21da-11f1-b0d8-0293afdb0cd1",
        "unit": "px",
        "width": 1200,
        "height": 1200,
        "errors": [],
        "pinned": true,
        "visual_id": "61818152-7726-4f6a-ae7b-ba339a28a3f8",
        "sharing_id": "b042b003-7a7c-4a52-8f5a-23417e68e38a",
        "visual_url": "https://production-banners.s3-eu-west-1.amazonaws.com/c7f8a281-b153-43cd-a45a-a669890ceaf9/61818152-7726-4f6a-ae7b-ba339a28a3f8.jpeg",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/c87c1252-4d41-45b9-84b8-2b5f8d92f56b.png"
      },
      {
        "id": "instagram-portrait",
        "uid": "abc123...",
        "unit": "px",
        "width": 1080,
        "height": 1350,
        "errors": [],
        "pinned": false,
        "visual_id": "...",
        "sharing_id": "...",
        "visual_url": "https://production-banners.s3-eu-west-1.amazonaws.com/...",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/..."
      }
    ]
  }
}
```

### 3. (Optional) UnpinFormatAdVariantUseCase

**Location**: `sinergia/app/v2/use_cases/ad.py`

**Purpose**: Allow users to unpin all formats, returning to a state where no format is marked as preferred. This is a useful complement to the pin functionality.

**Dependencies**: Same as `PinFormatAdVariantUseCase`

**Method Signature**:
```python
class UnpinFormatAdVariantUseCase:
    def __init__(self, account_email: str):
        self.account_email = account_email
        # Initialize same repositories as PinFormatAdVariantUseCase
    
    def execute(self, payload: dict) -> dict:
        """
        Args:
            payload: {
                'brand_id': int,
                'campaign_id': int,
                'ad_id': int,
                'channel_id': int,
                'variant_id': int
            }
        
        Returns:
            {
                'ok': 1,
                'data': {
                    'variant_id': int,
                    'previous_pinned_format_id': str | None,
                    'formats': [
                        {
                            'id': str,
                            'uid': str,
                            'unit': str,
                            'width': int,
                            'height': int,
                            'errors': list,
                            'pinned': bool,
                            'visual_id': str,
                            'sharing_id': str,
                            'visual_url': str,
                            'preview_url': str
                        }
                    ]  # All formats with pinned=false
                }
            }
        """
```

**Optional API Endpoint** (if desired for completeness):
```python
# Add to resources/ad.py if needed
@ad_ns.route('/hiluca/brand/ad/variant/unpin_format')
class HilucaResourceAdChannelVariantUnpinFormat(ProxySecureResource): 
    @v2_api.expect(UnpinFormatAdVariantStruct)
    def post(self):
        user_id = security_credentials['username']
        payload = request.json
        data = UnpinFormatAdVariantUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200
```

## Data Models

### Current Ad Channel Structure

The `pinned` field already exists on each format in the `media_formats` array and is initialized to `false` by `_build_media_formats()` in `ad_set.py`.

```python
ad_channel = {
    "id": 123,
    "attributes": {
        "media_formats": [
            {
                "id": "facebook-post",
                "uid": "45124a95-21da-11f1-b0d8-0293afdb0cd1",
                "unit": "px",
                "width": 1200,
                "height": 1200,
                "errors": [],
                "pinned": false,  # ← Currently always false, needs to be set
                "visual_id": "61818152-7726-4f6a-ae7b-ba339a28a3f8",
                "sharing_id": "b042b003-7a7c-4a52-8f5a-23417e68e38a",
                "visual_url": "https://production-banners.s3-eu-west-1.amazonaws.com/c7f8a281-b153-43cd-a45a-a669890ceaf9/61818152-7726-4f6a-ae7b-ba339a28a3f8.jpeg",
                "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/c87c1252-4d41-45b9-84b8-2b5f8d92f56b.png"
            },
            {
                "id": "instagram-portrait",
                "uid": "abc123...",
                "unit": "px",
                "width": 1080,
                "height": 1350,
                "errors": [],
                "pinned": false,  # ← Currently always false, needs to be set
                "visual_id": "...",
                "sharing_id": "...",
                "visual_url": "https://production-banners.s3-eu-west-1.amazonaws.com/...",
                "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/..."
            }
        ],
        "selected": true/false,
        "media_elements": [...],
        "channel_attributes": [...]
    }
}
```

### Updated Ad Channel Structure

No schema changes required. After pinning a format, the `media_formats` array will have exactly one format with `pinned: true`:

```python
{
    "id": 123,
    "attributes": {
        "media_formats": [
            {
                "id": "facebook-post",
                "uid": "45124a95-21da-11f1-b0d8-0293afdb0cd1",
                "unit": "px",
                "width": 1200,
                "height": 1200,
                "errors": [],
                "pinned": true,  # ← Now pinned
                "visual_id": "61818152-7726-4f6a-ae7b-ba339a28a3f8",
                "sharing_id": "b042b003-7a7c-4a52-8f5a-23417e68e38a",
                "visual_url": "https://production-banners.s3-eu-west-1.amazonaws.com/c7f8a281-b153-43cd-a45a-a669890ceaf9/61818152-7726-4f6a-ae7b-ba339a28a3f8.jpeg",
                "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/c87c1252-4d41-45b9-84b8-2b5f8d92f56b.png"
            },
            {
                "id": "instagram-portrait",
                "uid": "abc123...",
                "unit": "px",
                "width": 1080,
                "height": 1350,
                "errors": [],
                "pinned": false,  # ← Unpinned
                "visual_id": "...",
                "sharing_id": "...",
                "visual_url": "https://production-banners.s3-eu-west-1.amazonaws.com/...",
                "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/..."
            }
        ],
        ...
    }
}
```

## Implementation Strategy

The implementation is focused on the Use Cases layer since the endpoint and data structures already exist.

### Phase 1: Core Use Case Implementation

**File**: `sinergia/app/v2/use_cases/ad.py`

Implement the `PinFormatAdVariantUseCase` class that was previously empty:

```python
class PinFormatAdVariantUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()
        self.brand_repo = BrandRepository()
        self.ad_repo = AdRepository()

    def execute(self, payload):
        # 1. Validate parameters
        brand_id = payload.get('brand_id')
        campaign_id = payload.get('campaign_id')
        ad_id = payload.get('ad_id')
        channel_id = payload.get('channel_id')
        variant_id = payload.get('variant_id')
        format_id = payload.get('format_id')
        
        if not all([brand_id, campaign_id, ad_id, channel_id, variant_id, format_id]):
            raise ParametersNotFoundException('All parameters are required')
        
        # 2. Get account and validate access
        account = self.account_repo.get_by_email(self.account_email)
        if not account:
            raise DataNotFoundException('Account not found')
        
        parent_account_id = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
        
        # 3. Get campaign to verify ownership
        campaign = self.campaign_repo.get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)
        if not campaign:
            raise DataNotFoundException('Campaign not found or does not belong to account')
        
        # 4. Get ad to verify ad exists
        populate = ['ad_set_ref2.media_platform_project_id', 'channel_ref']
        ad = self.ad_repo.get_by_id(ad_id, populate)
        if not ad:
            raise DataNotFoundException('Ad not found')
        
        # 5. Get ad_channel by variant_id (already have this from existing use cases)
        ad_channel = self.ad_channel_repo.get_by_id_and_ad_and_channel(variant_id, ad_id, channel_id)
        if not ad_channel:
            raise DataNotFoundException('Ad variant not found')
        
        # 6. Get media_formats from ad_channel
        media_formats = ad_channel.get('attributes', {}).get('media_formats', [])
        if not isinstance(media_formats, list):
            raise DataNotFoundException('No media formats found in ad variant')
        
        # 7. Validate format_id exists in formats
        format_exists = any(f.get('id') == format_id for f in media_formats)
        if not format_exists:
            raise DataNotFoundException('Format not found in ad variant')
        
        # 8. Find currently pinned format (if any)
        currently_pinned = next((f for f in media_formats if f.get('pinned') is True), None)
        pinned_format_id = currently_pinned.get('id') if currently_pinned else None
        
        # 9. Update pinned status for all formats
        updated_formats = []
        for fmt in media_formats:
            is_requested_format = fmt.get('id') == format_id
            fmt_copy = {**fmt}
            fmt_copy['pinned'] = is_requested_format  # Only requested format is pinned
            updated_formats.append(fmt_copy)
        
        # 10. Update ad_channel in Strapi
        update_data = {
            'media_formats': updated_formats
        }
        
        success = self.ad_channel_repo.update(variant_id, update_data)
        if not success:
            raise DataNotFoundException('Failed to update ad variant')
        
        # 11. Return result
        return {
            'ok': 1,
            'data': {
                'variant_id': variant_id,
                'pinned_format_id': format_id,
                'previous_pinned_format_id': pinned_format_id,
                'formats': [
                    {
                        'id': format.get('id'),          # Format identifier (e.g., 'facebook-post')
                        'uid': format.get('uid'),        # Unique ID
                        'unit': format.get('unit'),      # Measurement unit (e.g., 'px')
                        'width': format.get('width'),
                        'height': format.get('height'),
                        'errors': format.get('errors'),
                        'pinned': format.get('pinned'),  # True for requested format
                        'visual_id': format.get('visual_id'),
                        'sharing_id': format.get('sharing_id'),
                        'visual_url': format.get('visual_url'),
                        'preview_url': format.get('preview_url')
                    }
                    for format in updated_formats
                ]
            }
        }
```

### Phase 2: (Optional) Unpin Format Use Case

If needed for completeness, implement `UnpinFormatAdVariantUseCase`:

```python
class UnpinFormatAdVariantUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()
        self.brand_repo = BrandRepository()
        self.ad_repo = AdRepository()

    def execute(self, payload):
        # Reuse validation logic from PinFormatAdVariantUseCase (steps 1-7)
        # Instead of pinning a specific format, set all formats to pinned=false
        
        # 8. Get currently pinned format (if any)
        currently_pinned = next((f for f in media_formats if f.get('pinned') is True), None)
        pinned_format_id = currently_pinned.get('id') if currently_pinned else None
        
        # 9. Update all formats to pinned=false
        updated_formats = []
        for fmt in media_formats:
            fmt_copy = {**fmt}
            fmt_copy['pinned'] = False
            updated_formats.append(fmt_copy)
        
        # 10. Update ad_channel in Strapi
        update_data = {
            'media_formats': updated_formats
        }
        
        success = self.ad_channel_repo.update(variant_id, update_data)
        if not success:
            raise DataNotFoundException('Failed to update ad variant')
        
        # 11. Return result
        return {
            'ok': 1,
            'data': {
                'variant_id': variant_id,
                'previous_pinned_format_id': pinned_format_id,
                'formats': [
                    {
                        'id': format.get('id'),
                        'uid': format.get('uid'),
                        'unit': format.get('unit'),
                        'width': format.get('width'),
                        'height': format.get('height'),
                        'errors': format.get('errors'),
                        'pinned': format.get('pinned'),
                        'visual_id': format.get('visual_id'),
                        'sharing_id': format.get('sharing_id'),
                        'visual_url': format.get('visual_url'),
                        'preview_url': format.get('preview_url')
                    }
                    for format in updated_formats
                ]
            }
        }
```

### Phase 3: Duplicate Ad Variant - Preserve Pinned Status

When duplicating an ad variant, the pinned status should be copied to the duplicate. This can be implemented as a helper method:

```python
def _preserve_pinned_format(source_variant_id: int, new_variant_id: int):
    """Copy pinned status from source variant to new variant."""
    source_ad_channel = ad_channel_repo.get_by_id(source_variant_id)
    if not source_ad_channel:
        return
    
    media_formats = source_ad_channel.get('attributes', {}).get('media_formats', [])
    pinned_format = next((f for f in media_formats if f.get('pinned') is True), None)
    
    if pinned_format:
        # Pin the same format in the new variant
        new_formats = []
        for fmt in media_formats:
            fmt_copy = {
                **fmt,
                'pinned': (fmt.get('id') == pinned_format.get('id'))
            }
            new_formats.append(fmt_copy)
        
        ad_channel_repo.update(new_variant_id, {
            'media_formats': [
                {
                    'id': fmt.get('id'),
                    'uid': fmt.get('uid'),
                    'unit': fmt.get('unit'),
                    'width': fmt.get('width'),
                    'height': fmt.get('height'),
                    'errors': fmt.get('errors'),
                    'pinned': fmt.get('pinned'),
                    'visual_id': fmt.get('visual_id'),
                    'sharing_id': fmt.get('sharing_id'),
                    'visual_url': fmt.get('visual_url'),
                    'preview_url': fmt.get('preview_url')
                }
                for fmt in new_formats
            ]
        })
```

## Data Flow

### Pin Format Flow

```
User Interface
     │
     ├─> POST /hiluca/brand/ad/variant/pin_format
     │    Request: {brand_id, campaign_id, ad_id, channel_id, variant_id, format_id}
     │
     ▼
┌────────────────────────────────────────┐
│  Flask Resource Endpoint               │
│  - Validates auth & permissions        │
│  - Extracts payload from request       │
│  - Calls PinFormatAdVariantUseCase     │
└────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────┐
│  PinFormatAdVariantUseCase.execute()   │
│  - Validates account access to campaign│
│  - Validates ad_channel exists         │
│  - Validates format_id in media_formats│
│  - Unpins currently pinned format      │
│  - Pins requested format               │
│  - Updates ad_channel in Strapi        │
└────────────────────────────────────────┘
     │
     ▼
  Response: {ok: 1, data: {variant_id, pinned_format_id, formats: [...]}}
     │
     ▼
User Interface
     ├─> Update pinned status in UI
     ├─> Show visual indicator on pinned format
     └─> Refresh format list
```

### Unpin Format Flow (Optional)

```
User Interface
     │
     ├─> POST /hiluca/brand/ad/variant/unpin_format
     │    Request: {brand_id, campaign_id, ad_id, channel_id, variant_id}
     │
     ▼
┌────────────────────────────────────────┐
│  Flask Resource Endpoint               │
│  - Validates auth & permissions        │
│  - Calls UnpinFormatAdVariantUseCase   │
└────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────┐
│  UnpinFormatAdVariantUseCase.execute() │
│  - Validates account access            │
│  - Validates ad_channel exists         │
│  - Sets all formats to pinned=false    │
│  - Updates ad_channel in Strapi        │
└────────────────────────────────────────┘
     │
     ▼
  Response: {ok: 1, data: {variant_id, formats: [...]}}
```

## Error Handling

The implementation should follow the existing error handling patterns in the ad.py use cases file.

### Validation Errors

1. **Missing Parameters**: `ParametersNotFoundException`
   - All parameters are required: brand_id, campaign_id, ad_id, channel_id, variant_id, format_id
   
2. **Account Not Found**: `DataNotFoundException`
   - Account email doesn't exist in the system

3. **Campaign Not Found**: `DataNotFoundException`
   - Campaign doesn't exist or doesn't belong to the account (check via parent_account_id)

4. **Ad Not Found**: `DataNotFoundException`
   - Ad ID doesn't exist or doesn't belong to the campaign

5. **Ad Variant Not Found**: `DataNotFoundException`
   - Variant ID doesn't exist or doesn't belong to the ad

6. **Format Not Found**: `DataNotFoundException`
   - Requested format_id doesn't exist in the ad variant's media_formats

### Update Errors

7. **Failed to Update**: `DataNotFoundException`
   - Strapi update operation failed
   - Return: `{'ok': 1, 'data': {}}` with appropriate error in logs

### Unpin Format Errors

8. **No Pinned Format**: Success case (not an error)
   - If no format is pinned, return success with `previous_pinned_format_id: null`
   - This is a valid operation - unpinning when nothing is pinned

## Testing Strategy

### Unit Tests

**File Location**: Per the project structure conventions (`.kiro/steering/structure.md`), unit tests for the use_cases layer (`app/v2/use_cases/`) must be located at `tests/v2/unit/use_cases/`. Unit tests for `PinFormatAdVariantUseCase` and `UnpinFormatAdVariantUseCase` must be placed at `tests/v2/unit/use_cases/test_pin_format_ad_variant.py`.

**Test Cases**:

1. **Pin Format Tests**:
   - ✅ Pin a format when no format is currently pinned
   - ✅ Pin a format when another format is already pinned (should unpin existing)
   - ✅ Attempt to pin a non-existent format (should raise DataNotFoundException)
   - ✅ Pin a format with invalid variant_id (should raise DataNotFoundException)
   - ✅ Pin a format with unauthorized account (should raise DataNotFoundException)

2. **Unpin Format Tests** (if implemented):
   - ✅ Unpin when a format is pinned (should unpin and return previous format ID)
   - ✅ Unpin when no format is pinned (should succeed with null previous format)
   - ✅ Unpin with invalid variant_id (should raise DataNotFoundException)

3. **Integration Tests**:
   - ✅ End-to-end workflow: generate variant → pin format → verify display
   - ✅ Duplicate variant with pinned format preserved
   - ✅ Multiple users pin/unpin same variant (concurrency test)

### Property-Based Tests

1. **Invariant**: For any ad variant, pinning operation results in exactly one or zero pinned formats
   ```python
   # For all variants and format IDs, pin operation should result in exactly one pinned format
   def test_pin_invariant(variant, format_id):
       result = pin_format(variant.id, format_id)
       pinned_count = sum(1 for f in result.formats if f.pinned)
       assert pinned_count == 1
   ```

2. **Round Trip**: For any variant, pinning format A, then unpinning, results in no pinned formats
   ```python
   # For all variants and format IDs, pin then unpin should result in zero pinned formats
   def test_pin_unpin_roundtrip(variant, format_id):
       pin_result = pin_format(variant.id, format_id)
       assert sum(1 for f in pin_result.formats if f.pinned) == 1
       
       unpin_result = unpin_format(variant.id)
       assert sum(1 for f in unpin_result.formats if f.pinned) == 0
   ```

3. **Idempotence**: Pinning the same format twice has the same effect as pinning once
   ```python
   # For all variants and format IDs, pin(x) then pin(x) == pin(x)
   def test_pin_idempotence(variant, format_id):
       result1 = pin_format(variant.id, format_id)
       result2 = pin_format(variant.id, format_id)
       assert result1.pinned_format_id == result2.pinned_format_id
   ```

### Test Coverage Matrix

| Scenario | Test Type | Property/Example |
|----------|-----------|------------------|
| Pin format (no prior pin) | Unit | Specific example |
| Pin format (replace existing) | Unit | Specific example |
| Pin non-existent format | Unit | Error case |
| Unpin format (has pinned) | Unit | Specific example |
| Unpin format (no pinned) | Unit | Edge case |
| Duplicate variant preserves pinned | Integration | End-to-end |
| Concurrency test | Integration | Multiple users |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Pin invariant

*For any* ad variant and valid format ID, pinning a format results in exactly one pinned format

**Validates: Requirements 1.4**

### Property 2: Unpin invariant

*For any* ad variant, unpinning a format results in zero pinned formats

**Validates: Requirements 2.2**

### Property 3: Round trip preservation

*For any* ad variant, pinning format A then unpinning results in the same state as the original variant (no pinned formats)

**Validates: Requirements 2.1**

### Property 4: Idempotence

*For any* ad variant and format ID, pinning the same format twice produces the same result as pinning once

**Validates: Requirements 1.1, 1.3**

### Property 5: Uniqueness

*For any* ad variant, at most one format can have `pinned=true` at any time

**Validates: Requirements 1.4**

## Implementation Tasks

### Phase 1: Core Functionality

- [ ] 1.1 Implement PinFormatAdVariantUseCase.execute()
  - [ ] Validate all required parameters (brand_id, campaign_id, ad_id, channel_id, variant_id, format_id)
  - [ ] Validate account access to campaign (check parent_account_id)
  - [ ] Validate ad_channel exists and belongs to ad (reuse existing method from other use cases)
  - [ ] Validate format_id exists in media_formats
  - [ ] Find currently pinned format (if any)
  - [ ] Update all formats: pin requested, unpin others
  - [ ] Save updated media_formats to ad_channel
  - [ ] Return formatted response with previous_pinned_format_id

- [ ] 1.2 Implement UnpinFormatAdVariantUseCase.execute() (optional)
  - [ ] Reuse validation logic from PinFormatAdVariantUseCase
  - [ ] Get currently pinned format (if any)
  - [ ] Set all formats to pinned=false
  - [ ] Save to ad_channel
  - [ ] Return formatted response with previous_pinned_format_id

- [ ] 1.3 Add API endpoint for unpin (if needed)
  - [ ] Add UnpinFormatAdVariantStruct model
  - [ ] Add /hiluca/brand/ad/variant/unpin_format endpoint
  - [ ] Wire to UnpinFormatAdVariantUseCase

### Phase 2: Testing

- [ ] 2.1 Write unit tests for PinFormatAdVariantUseCase
  - [ ] Test normal pin operation (when no format is pinned)
  - [ ] Test pin when another format is pinned (should unpin existing)
  - [ ] Test pin non-existent format (should raise DataNotFoundException)
  - [ ] Test unauthorized access (should raise DataNotFoundException)

- [ ] 2.2 Write unit tests for UnpinFormatAdVariantUseCase (optional)
  - [ ] Test unpin when format is pinned
  - [ ] Test unpin when no format is pinned (should succeed)
  - [ ] Test unauthorized access

- [ ] 2.3 Write property-based tests
  - [ ] Test pin invariant (exactly one or zero pinned after operation)
  - [ ] Test pin-unpin round trip
  - [ ] Test pin idempotence

### Phase 3: Integration

- [ ] 3.1 Duplicate variant preserves pinned status (optional enhancement)
  - [ ] Implement _preserve_pinned_format helper method
  - [ ] Call after variant duplication in Fury job

## Error Handling Summary

| Error Code | Scenario | User Message |
|------------|----------|--------------|
| 400 | Missing parameters | "All parameters are required" |
| 404 | Account not found | "Account not found" |
| 404 | Campaign not found | "Campaign not found or does not belong to account" |
| 404 | Ad not found | "Ad not found" |
| 404 | Ad variant not found | "Ad variant not found" |
| 404 | Format not found | "Format not found in ad variant" |
| 500 | Update failed | "Failed to update ad variant" |

## Notes

1. **No schema changes required**: The `pinned` field already exists in the data model and is initialized to `false` by `_build_media_formats()` in `ad_set.py`.

2. **Architecture layering**: The implementation follows the Sinergia project's clean layered architecture:
   - **Resources Layer**: Existing Flask endpoint handles HTTP concerns
   - **Use Cases Layer**: Business logic implementation (what we're adding)
   - **Repository Layer**: Data access to Strapi API

3. **Validation strategy**: The use case validates that:
   - Account has access to the campaign (using parent_account_id)
   - Ad channel exists and belongs to the ad
   - Requested format exists in the ad variant's media_formats

4. **Uniqueness enforcement**: The implementation explicitly sets all formats to `pinned=false` except the requested one, ensuring exactly one format is pinned (or zero if unpinning).

5. **Idempotent operation**: Pinning the same format twice has no additional effect - the result is identical to pinning once.

6. **No deletion**: Formats cannot be deleted - only their pinned status can change.

7. **UI expectations**: The frontend is expected to:
   - Show a visual indicator (icon, label, highlight) on the pinned format
   - Display a tooltip explaining it's the primary format
   - Allow pinning by clicking on a format
   - Allow unpinning via a button or menu action (optional)
