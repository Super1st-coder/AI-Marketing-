from unittest.mock import patch

from app.v2.use_cases.ad import PinFormatAdVariantUseCase


class TestPinFormatAdVariantEndToEndWorkflow:
    """End-to-end workflow test for PinFormatAdVariantUseCase.

    Unlike the unit tests in tests/v2/unit/use_cases/test_pin_format_ad_variant.py
    (which mock repository return values statically per-call), this test exercises
    the full execute() call chain against a shared, mutable "fake Strapi" state.
    AdChannelRepository.update() actually mutates the stored ad_channel, and
    get_by_id_and_ad_and_channel() always reflects the current stored state. This
    proves the full workflow: valid brand/campaign/ad/channel/variant setup ->
    pin_format call -> response structure verification -> persisted state
    verification via a second fetch (simulating "fetching variant again").
    """

    BRAND_ID = 1
    CAMPAIGN_ID = 123
    AD_ID = 456
    CHANNEL_ID = 789
    VARIANT_ID = 101
    ACCOUNT_EMAIL = "test@example.com"

    def _build_account(self):
        return {
            'id': 1,
            'attributes': {
                'parent_account': {
                    'data': None
                }
            }
        }

    def _build_media_format(self, format_id, pinned=False):
        return {
            'id': format_id,
            'uid': f'uid-{format_id}',
            'unit': 'px',
            'width': 1200,
            'height': 1200,
            'errors': [],
            'pinned': pinned,
            'visual_id': f'visual-{format_id}',
            'sharing_id': f'sharing-{format_id}',
            'visual_url': f'https://example.com/{format_id}.jpeg',
            'preview_url': f'https://example.com/{format_id}-preview.png'
        }

    def _build_payload(self, format_id):
        return {
            'brand_id': self.BRAND_ID,
            'campaign_id': self.CAMPAIGN_ID,
            'ad_id': self.AD_ID,
            'channel_id': self.CHANNEL_ID,
            'variant_id': self.VARIANT_ID,
            'format_id': format_id
        }

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_end_to_end_pin_format_workflow_persists_pinned_state(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Full workflow: set up valid data -> pin format -> verify response ->
        fetch variant again and verify the pinned status was actually persisted.
        """
        # 1. Set up valid test data (brand, campaign, ad, channel, variant)
        media_formats = [
            self._build_media_format('facebook-post', pinned=False),
            self._build_media_format('instagram-portrait', pinned=False),
            self._build_media_format('linkedin-square', pinned=False)
        ]

        # Shared mutable "fake Strapi" state, keyed by variant_id, simulating a
        # real persistence store.
        fake_strapi_state = {
            self.VARIANT_ID: {
                'id': self.VARIANT_ID,
                'attributes': {
                    'media_formats': media_formats
                }
            }
        }

        def fake_get_by_id_and_ad_and_channel(variant_id, ad_id, channel_id):
            # Returns the current stored state, not a static value, so any prior
            # update() call is reflected on the next fetch.
            stored = fake_strapi_state.get(variant_id)
            if stored is None or ad_id != self.AD_ID or channel_id != self.CHANNEL_ID:
                return None
            return stored

        def fake_update(variant_id, update_data):
            # Actually mutates the stored ad_channel, simulating a real Strapi
            # persistence layer rather than a shallow mock return value.
            stored = fake_strapi_state.get(variant_id)
            if stored is None:
                return None
            stored['attributes'] = {**stored['attributes'], **update_data}
            fake_strapi_state[variant_id] = stored
            return stored

        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': self.CAMPAIGN_ID}
        mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': self.AD_ID}
        mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.side_effect = fake_get_by_id_and_ad_and_channel
        mock_ad_channel_repo_cls.return_value.update.side_effect = fake_update

        use_case = PinFormatAdVariantUseCase(self.ACCOUNT_EMAIL)

        # 2. Call pin_format endpoint (use case) with valid payload
        payload = self._build_payload('instagram-portrait')
        response = use_case.execute(payload)

        # 3. Verify response returns correct data structure
        assert response['ok'] == 1
        data = response['data']
        assert data['variant_id'] == self.VARIANT_ID
        assert data['pinned_format_id'] == 'instagram-portrait'
        assert data['previous_pinned_format_id'] is None
        assert len(data['formats']) == 3

        expected_fields = {
            'id', 'uid', 'unit', 'width', 'height', 'errors', 'pinned',
            'visual_id', 'sharing_id', 'visual_url', 'preview_url'
        }
        for fmt in data['formats']:
            assert expected_fields.issubset(fmt.keys())

        pinned_formats = [f for f in data['formats'] if f['pinned']]
        assert len(pinned_formats) == 1
        assert pinned_formats[0]['id'] == 'instagram-portrait'

        # 4. Verify pinned status is persisted by fetching variant again
        refetched_ad_channel = use_case.ad_channel_repo.get_by_id_and_ad_and_channel(
            self.VARIANT_ID, self.AD_ID, self.CHANNEL_ID
        )
        assert refetched_ad_channel is not None
        refetched_formats = refetched_ad_channel['attributes']['media_formats']

        refetched_pinned = [f for f in refetched_formats if f['pinned']]
        assert len(refetched_pinned) == 1
        assert refetched_pinned[0]['id'] == 'instagram-portrait'

        for fmt in refetched_formats:
            if fmt['id'] != 'instagram-portrait':
                assert fmt['pinned'] is False
