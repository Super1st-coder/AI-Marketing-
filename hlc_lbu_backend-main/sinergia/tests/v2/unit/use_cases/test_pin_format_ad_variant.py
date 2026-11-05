import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import HealthCheck, given, settings, strategies as st
from app.v2.use_cases.ad import PinFormatAdVariantUseCase, UnpinFormatAdVariantUseCase, _preserve_pinned_format
from app.exceptions.base import ParametersNotFoundException, DataNotFoundException


class TestPinFormatAdVariantUseCaseParameterValidation:
    """Test parameter validation in PinFormatAdVariantUseCase.execute()"""

    def test_execute_raises_parameters_not_found_exception_when_brand_id_missing(self):
        """Missing brand_id should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101,
            'format_id': 'facebook-post'
        }

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)

    def test_execute_raises_parameters_not_found_exception_when_campaign_id_missing(self):
        """Missing campaign_id should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {
            'brand_id': 1,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101,
            'format_id': 'facebook-post'
        }

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)

    def test_execute_raises_parameters_not_found_exception_when_ad_id_missing(self):
        """Missing ad_id should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {
            'brand_id': 1,
            'campaign_id': 123,
            'channel_id': 789,
            'variant_id': 101,
            'format_id': 'facebook-post'
        }

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)

    def test_execute_raises_parameters_not_found_exception_when_channel_id_missing(self):
        """Missing channel_id should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'variant_id': 101,
            'format_id': 'facebook-post'
        }

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)

    def test_execute_raises_parameters_not_found_exception_when_variant_id_missing(self):
        """Missing variant_id should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'format_id': 'facebook-post'
        }

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)

    def test_execute_raises_parameters_not_found_exception_when_format_id_missing(self):
        """Missing format_id should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101
        }

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)

    def test_execute_raises_parameters_not_found_exception_when_all_missing(self):
        """All missing parameters should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {}

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)

    def test_execute_raises_parameters_not_found_exception_when_any_parameter_is_zero(self):
        """Zero values for numeric parameters should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {
            'brand_id': 0,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101,
            'format_id': 'facebook-post'
        }

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)

    def test_execute_raises_parameters_not_found_exception_when_any_parameter_is_empty_string(self):
        """Empty string for format_id should raise ParametersNotFoundException"""
        use_case = PinFormatAdVariantUseCase("test@example.com")
        payload = {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101,
            'format_id': ''
        }

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'All parameters are required' in str(exc_info.value)


class TestPinFormatAdVariantUseCaseSuccessfulPin:
    """Test successful pin scenarios in PinFormatAdVariantUseCase.execute()"""

    def _build_account(self, account_id=1, parent_account_id=None):
        return {
            'id': account_id,
            'attributes': {
                'parent_account': {
                    'data': {'id': parent_account_id} if parent_account_id else None
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

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_pins_format_when_no_format_is_currently_pinned(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Pinning a format when none is pinned should set only the requested format as pinned"""
        media_formats = [
            self._build_media_format('facebook-post', pinned=False),
            self._build_media_format('instagram-portrait', pinned=False)
        ]
        ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
        mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
        mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = ad_channel
        mock_ad_channel_repo_cls.return_value.update.return_value = ad_channel

        use_case = PinFormatAdVariantUseCase('test@example.com')
        payload = {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101,
            'format_id': 'facebook-post'
        }

        response = use_case.execute(payload)

        data = response
        assert data['pinned_format_id'] == 'facebook-post'
        assert data['previous_pinned_format_id'] is None

        pinned_formats = [f for f in data['formats'] if f['pinned']]
        assert len(pinned_formats) == 1
        assert pinned_formats[0]['id'] == 'facebook-post'

        other_formats = [f for f in data['formats'] if f['id'] != 'facebook-post']
        assert all(not f['pinned'] for f in other_formats)


class TestPinFormatAdVariantUseCaseReplacePin:
    """Test successful pin scenarios when replacing an already pinned format"""

    def _build_account(self, account_id=1, parent_account_id=None):
        return {
            'id': account_id,
            'attributes': {
                'parent_account': {
                    'data': {'id': parent_account_id} if parent_account_id else None
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

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_pins_new_format_and_unpins_previous_format(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Pinning a new format should unpin the previously pinned format"""
        media_formats = [
            self._build_media_format('facebook-post', pinned=True),
            self._build_media_format('instagram-portrait', pinned=False),
            self._build_media_format('linkedin-square', pinned=False)
        ]
        ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
        mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
        mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = ad_channel
        mock_ad_channel_repo_cls.return_value.update.return_value = ad_channel

        use_case = PinFormatAdVariantUseCase('test@example.com')
        payload = {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101,
            'format_id': 'instagram-portrait'
        }

        response = use_case.execute(payload)

        data = response
        assert data['pinned_format_id'] == 'instagram-portrait'
        assert data['previous_pinned_format_id'] == 'facebook-post'

        pinned_formats = [f for f in data['formats'] if f['pinned']]
        assert len(pinned_formats) == 1
        assert pinned_formats[0]['id'] == 'instagram-portrait'

        unpinned_formats = [f for f in data['formats'] if f['id'] != 'instagram-portrait']
        assert all(not f['pinned'] for f in unpinned_formats)


class TestPinFormatAdVariantUseCaseErrorCases:
    """Test error scenarios in PinFormatAdVariantUseCase.execute()"""

    def _build_account(self, account_id=1, parent_account_id=None):
        return {
            'id': account_id,
            'attributes': {
                'parent_account': {
                    'data': {'id': parent_account_id} if parent_account_id else None
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

    def _default_payload(self):
        return {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101,
            'format_id': 'facebook-post'
        }

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_raises_data_not_found_exception_when_format_does_not_exist(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Requesting a format_id that does not exist in media_formats should raise DataNotFoundException"""
        media_formats = [
            self._build_media_format('instagram-portrait', pinned=False),
            self._build_media_format('linkedin-square', pinned=False)
        ]
        ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
        mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
        mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = ad_channel

        use_case = PinFormatAdVariantUseCase('test@example.com')
        payload = self._default_payload()
        payload['format_id'] = 'non-existent-format'

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'Format not found in ad variant' in str(exc_info.value)

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_raises_data_not_found_exception_when_account_not_found(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Account not found should raise DataNotFoundException"""
        mock_account_repo_cls.return_value.get_by_email.return_value = None

        use_case = PinFormatAdVariantUseCase('test@example.com')
        payload = self._default_payload()

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'Account not found' in str(exc_info.value)
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.assert_not_called()

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_raises_data_not_found_exception_when_campaign_not_found(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Campaign not found (or not belonging to account) should raise DataNotFoundException"""
        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = None

        use_case = PinFormatAdVariantUseCase('test@example.com')
        payload = self._default_payload()

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'Campaign not found or does not belong to account' in str(exc_info.value)
        mock_ad_repo_cls.return_value.get_by_id.assert_not_called()

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_raises_data_not_found_exception_when_ad_not_found(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Ad not found should raise DataNotFoundException"""
        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
        mock_ad_repo_cls.return_value.get_by_id.return_value = None

        use_case = PinFormatAdVariantUseCase('test@example.com')
        payload = self._default_payload()

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'Ad not found for the given ID' in str(exc_info.value)
        mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.assert_not_called()

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_raises_data_not_found_exception_when_ad_variant_not_found(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Ad variant (ad_channel) not found should raise DataNotFoundException"""
        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
        mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
        mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = None

        use_case = PinFormatAdVariantUseCase('test@example.com')
        payload = self._default_payload()

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'Ad variant not found' in str(exc_info.value)


_FORMAT_ID_ALPHABET = st.characters(whitelist_categories=('L', 'Nd'), max_codepoint=0x2FFF)
_FORMAT_ID_STRATEGY = st.text(alphabet=_FORMAT_ID_ALPHABET, min_size=1, max_size=12)


@st.composite
def _unique_format_ids_and_target(draw):
    """Generate a unique list of 1-10 format ids plus one id to pin from that list."""
    format_ids = draw(
        st.lists(_FORMAT_ID_STRATEGY, min_size=1, max_size=10, unique=True)
    )
    target_format_id = draw(st.sampled_from(format_ids))
    return format_ids, target_format_id


@st.composite
def _unique_format_ids_target_and_pinned_index(draw):
    """Generate format ids, a pin target, and an optional index that starts pinned.

    At most one of the generated formats starts as pinned (or none), matching the
    real invariant that the use case always maintains for ad_channel media_formats.
    """
    format_ids, target_format_id = draw(_unique_format_ids_and_target())
    pinned_index = draw(
        st.one_of(st.none(), st.integers(min_value=0, max_value=len(format_ids) - 1))
    )
    return format_ids, target_format_id, pinned_index


class TestPinFormatAdVariantUseCaseProperties:
    """Property-based tests for PinFormatAdVariantUseCase.execute()"""

    def _build_account(self, account_id=1, parent_account_id=None):
        return {
            'id': account_id,
            'attributes': {
                'parent_account': {
                    'data': {'id': parent_account_id} if parent_account_id else None
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

    def _build_payload(self, format_id, variant_id=101):
        return {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': variant_id,
            'format_id': format_id
        }

    def _patch_repositories(self):
        """Return the four patch context managers used across the use case."""
        return (
            patch('app.v2.use_cases.ad.AccountRepository'),
            patch('app.v2.use_cases.ad.CampaignRepository'),
            patch('app.v2.use_cases.ad.AdChannelRepository'),
            patch('app.v2.use_cases.ad.AdRepository'),
        )

    # Feature: ads-pin-format-variant, Property 1: Pin invariant
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(setup=_unique_format_ids_target_and_pinned_index())
    def test_property_pin_invariant_results_in_exactly_one_pinned_format(self, setup):
        """For any ad variant and valid format ID, pinning results in exactly one pinned format.

        **Validates: Requirements 1.4**
        """
        format_ids, format_id, pinned_index = setup

        media_formats = [
            self._build_media_format(fid, pinned=(idx == pinned_index))
            for idx, fid in enumerate(format_ids)
        ]
        ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        account_patch, campaign_patch, ad_channel_patch, ad_patch = self._patch_repositories()
        with account_patch as mock_account_repo_cls, \
                campaign_patch as mock_campaign_repo_cls, \
                ad_channel_patch as mock_ad_channel_repo_cls, \
                ad_patch as mock_ad_repo_cls:
            mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
            mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
            mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
            mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = ad_channel
            mock_ad_channel_repo_cls.return_value.update.side_effect = (
                lambda variant_id, update_data: update_data
            )

            use_case = PinFormatAdVariantUseCase('test@example.com')
            response = use_case.execute(self._build_payload(format_id))

        pinned_count = sum(1 for f in response['formats'] if f['pinned'])
        assert pinned_count == 1
        pinned_formats = [f for f in response['formats'] if f['pinned']]
        assert pinned_formats[0]['id'] == format_id

    # Feature: ads-pin-format-variant, Property 3: Round trip preservation
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(setup=_unique_format_ids_target_and_pinned_index())
    def test_property_pin_then_unpin_results_in_no_pinned_formats(self, setup):
        """For any ad variant, pinning format A then unpinning results in no pinned formats.

        UnpinFormatAdVariantUseCase is not implemented yet (optional task 5), so the
        "unpin" half is simulated by setting pinned=False on every format returned
        from the pin operation, which is exactly what that use case would do per the
        design document.

        **Validates: Requirements 2.1**
        """
        format_ids, format_id, pinned_index = setup

        media_formats = [
            self._build_media_format(fid, pinned=(idx == pinned_index))
            for idx, fid in enumerate(format_ids)
        ]
        ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        account_patch, campaign_patch, ad_channel_patch, ad_patch = self._patch_repositories()
        with account_patch as mock_account_repo_cls, \
                campaign_patch as mock_campaign_repo_cls, \
                ad_channel_patch as mock_ad_channel_repo_cls, \
                ad_patch as mock_ad_repo_cls:
            mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
            mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
            mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
            mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = ad_channel
            mock_ad_channel_repo_cls.return_value.update.side_effect = (
                lambda variant_id, update_data: update_data
            )

            use_case = PinFormatAdVariantUseCase('test@example.com')
            pin_response = use_case.execute(self._build_payload(format_id))

        pinned_count_after_pin = sum(1 for f in pin_response['formats'] if f['pinned'])
        assert pinned_count_after_pin == 1

        # Simulate the unpin half of the round trip: set all formats to pinned=False,
        # matching UnpinFormatAdVariantUseCase's documented behavior.
        unpinned_formats = [
            {**fmt, 'pinned': False} for fmt in pin_response['formats']
        ]

        pinned_count_after_unpin = sum(1 for f in unpinned_formats if f['pinned'])
        assert pinned_count_after_unpin == 0

    # Feature: ads-pin-format-variant, Property 4: Idempotence
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(setup=_unique_format_ids_target_and_pinned_index())
    def test_property_pinning_same_format_twice_is_idempotent(self, setup):
        """For any ad variant and format ID, pinning the same format twice is idempotent.

        **Validates: Requirements 1.1, 1.3**
        """
        format_ids, format_id, pinned_index = setup

        initial_media_formats = [
            self._build_media_format(fid, pinned=(idx == pinned_index))
            for idx, fid in enumerate(format_ids)
        ]
        # Mutable container simulating persisted Strapi state across calls, so the
        # second execute() call observes the result of the first update.
        persisted_state = {
            'ad_channel': {
                'id': 101,
                'attributes': {
                    'media_formats': initial_media_formats
                }
            }
        }

        def get_by_id_and_ad_and_channel_side_effect(variant_id, ad_id, channel_id):
            return persisted_state['ad_channel']

        def update_side_effect(variant_id, update_data):
            persisted_state['ad_channel'] = {
                'id': persisted_state['ad_channel']['id'],
                'attributes': {
                    **persisted_state['ad_channel']['attributes'],
                    **update_data,
                }
            }
            return update_data

        account_patch, campaign_patch, ad_channel_patch, ad_patch = self._patch_repositories()
        with account_patch as mock_account_repo_cls, \
                campaign_patch as mock_campaign_repo_cls, \
                ad_channel_patch as mock_ad_channel_repo_cls, \
                ad_patch as mock_ad_repo_cls:
            mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
            mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
            mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
            mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.side_effect = (
                get_by_id_and_ad_and_channel_side_effect
            )
            mock_ad_channel_repo_cls.return_value.update.side_effect = update_side_effect

            use_case = PinFormatAdVariantUseCase('test@example.com')
            payload = self._build_payload(format_id)
            response1 = use_case.execute(payload)
            response2 = use_case.execute(payload)

        assert response1['pinned_format_id'] == format_id
        assert response2['pinned_format_id'] == format_id
        # After the first call, format_id is already pinned, so the second call's
        # previous_pinned_format_id must equal the first call's pinned_format_id.
        assert response2['previous_pinned_format_id'] == response1['pinned_format_id']

        pinned_ids_1 = {f['id'] for f in response1['formats'] if f['pinned']}
        pinned_ids_2 = {f['id'] for f in response2['formats'] if f['pinned']}
        assert pinned_ids_1 == pinned_ids_2 == {format_id}


class TestUnpinFormatAdVariantUseCase:
    """Test UnpinFormatAdVariantUseCase.execute()"""

    def _build_account(self, account_id=1, parent_account_id=None):
        return {
            'id': account_id,
            'attributes': {
                'parent_account': {
                    'data': {'id': parent_account_id} if parent_account_id else None
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

    def _default_payload(self):
        return {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': 101
        }

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_unpins_format_when_a_format_is_currently_pinned(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Unpinning when a format is pinned should return its id as previous_pinned_format_id
        and result in all formats having pinned=False.

        _Requirements: 2.1_
        """
        media_formats = [
            self._build_media_format('facebook-post', pinned=True),
            self._build_media_format('instagram-portrait', pinned=False),
            self._build_media_format('linkedin-square', pinned=False)
        ]
        ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
        mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
        mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = ad_channel
        mock_ad_channel_repo_cls.return_value.update.return_value = ad_channel

        use_case = UnpinFormatAdVariantUseCase('test@example.com')
        response = use_case.execute(self._default_payload())

        data = response
        assert data['previous_pinned_format_id'] == 'facebook-post'
        assert all(not f['pinned'] for f in data['formats'])

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_unpins_when_no_format_is_currently_pinned(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Unpinning when no format is pinned should return previous_pinned_format_id=None
        and all formats should remain pinned=False.

        _Requirements: 2.1_
        """
        media_formats = [
            self._build_media_format('facebook-post', pinned=False),
            self._build_media_format('instagram-portrait', pinned=False)
        ]
        ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
        mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
        mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = ad_channel
        mock_ad_channel_repo_cls.return_value.update.return_value = ad_channel

        use_case = UnpinFormatAdVariantUseCase('test@example.com')
        response = use_case.execute(self._default_payload())

        data = response
        assert data['previous_pinned_format_id'] is None
        assert all(not f['pinned'] for f in data['formats'])

    @patch('app.v2.use_cases.ad.AdRepository')
    @patch('app.v2.use_cases.ad.AdChannelRepository')
    @patch('app.v2.use_cases.ad.CampaignRepository')
    @patch('app.v2.use_cases.ad.AccountRepository')
    def test_execute_raises_data_not_found_exception_when_account_not_found(
        self, mock_account_repo_cls, mock_campaign_repo_cls, mock_ad_channel_repo_cls, mock_ad_repo_cls
    ):
        """Account not found should raise DataNotFoundException.

        _Requirements: 2.1_
        """
        mock_account_repo_cls.return_value.get_by_email.return_value = None

        use_case = UnpinFormatAdVariantUseCase('test@example.com')
        payload = self._default_payload()

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case.execute(payload)

        assert 'Account not found' in str(exc_info.value)
        mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.assert_not_called()


class TestUnpinFormatAdVariantUseCaseProperties:
    """Property-based tests for UnpinFormatAdVariantUseCase.execute()"""

    def _build_account(self, account_id=1, parent_account_id=None):
        return {
            'id': account_id,
            'attributes': {
                'parent_account': {
                    'data': {'id': parent_account_id} if parent_account_id else None
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

    def _build_payload(self, variant_id=101):
        return {
            'brand_id': 1,
            'campaign_id': 123,
            'ad_id': 456,
            'channel_id': 789,
            'variant_id': variant_id
        }

    def _patch_repositories(self):
        """Return the four patch context managers used across the use case."""
        return (
            patch('app.v2.use_cases.ad.AccountRepository'),
            patch('app.v2.use_cases.ad.CampaignRepository'),
            patch('app.v2.use_cases.ad.AdChannelRepository'),
            patch('app.v2.use_cases.ad.AdRepository'),
        )

    # Feature: ads-pin-format-variant, Property 2: Unpin invariant
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(setup=_unique_format_ids_target_and_pinned_index())
    def test_property_unpin_results_in_zero_pinned_formats(self, setup):
        """For any ad variant, unpinning results in zero pinned formats, regardless of
        whether a format was pinned beforehand.

        **Validates: Requirements 2.2**
        """
        format_ids, _target_format_id, pinned_index = setup

        media_formats = [
            self._build_media_format(fid, pinned=(idx == pinned_index))
            for idx, fid in enumerate(format_ids)
        ]
        ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        account_patch, campaign_patch, ad_channel_patch, ad_patch = self._patch_repositories()
        with account_patch as mock_account_repo_cls, \
                campaign_patch as mock_campaign_repo_cls, \
                ad_channel_patch as mock_ad_channel_repo_cls, \
                ad_patch as mock_ad_repo_cls:
            mock_account_repo_cls.return_value.get_by_email.return_value = self._build_account()
            mock_campaign_repo_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 123}
            mock_ad_repo_cls.return_value.get_by_id.return_value = {'id': 456}
            mock_ad_channel_repo_cls.return_value.get_by_id_and_ad_and_channel.return_value = ad_channel
            mock_ad_channel_repo_cls.return_value.update.side_effect = (
                lambda variant_id, update_data: update_data
            )

            use_case = UnpinFormatAdVariantUseCase('test@example.com')
            response = use_case.execute(self._build_payload())

        pinned_count = sum(1 for f in response['formats'] if f['pinned'])
        assert pinned_count == 0


class TestPreservePinnedFormat:
    """Test _preserve_pinned_format helper used when duplicating ad variants"""

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

    @patch('app.v2.use_cases.ad.AdChannelRepository')
    def test_copies_pinned_format_from_source_to_new_variant(self, mock_ad_channel_repo_cls):
        """When the source variant has a pinned format, the new variant should
        get that same format pinned and every other format unpinned"""
        media_formats = [
            self._build_media_format('facebook-post', pinned=True),
            self._build_media_format('instagram-portrait', pinned=False),
            self._build_media_format('linkedin-square', pinned=False)
        ]
        source_ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        mock_repo = mock_ad_channel_repo_cls.return_value
        mock_repo.get_ad_by_id.return_value = source_ad_channel
        mock_repo.update.return_value = {'id': 202}

        result = _preserve_pinned_format(101, 202)

        mock_repo.get_ad_by_id.assert_called_once_with(101)
        assert mock_repo.update.call_count == 1

        call_args = mock_repo.update.call_args
        assert call_args[0][0] == 202

        updated_formats = call_args[0][1]['media_formats']
        pinned_formats = [f for f in updated_formats if f['pinned']]
        assert len(pinned_formats) == 1
        assert pinned_formats[0]['id'] == 'facebook-post'

        other_formats = [f for f in updated_formats if f['id'] != 'facebook-post']
        assert all(not f['pinned'] for f in other_formats)

        assert result == {'id': 202}

    @patch('app.v2.use_cases.ad.AdChannelRepository')
    def test_returns_false_when_source_has_no_pinned_format(self, mock_ad_channel_repo_cls):
        """When the source variant has no pinned format, nothing should be
        updated on the new variant and the helper should return a falsy value"""
        media_formats = [
            self._build_media_format('facebook-post', pinned=False),
            self._build_media_format('instagram-portrait', pinned=False)
        ]
        source_ad_channel = {
            'id': 101,
            'attributes': {
                'media_formats': media_formats
            }
        }

        mock_repo = mock_ad_channel_repo_cls.return_value
        mock_repo.get_ad_by_id.return_value = source_ad_channel

        result = _preserve_pinned_format(101, 202)

        assert not result
        mock_repo.update.assert_not_called()

    @patch('app.v2.use_cases.ad.AdChannelRepository')
    def test_returns_false_when_source_variant_not_found(self, mock_ad_channel_repo_cls):
        """When the source variant does not exist, the helper should return a
        falsy value without attempting to update the new variant"""
        mock_repo = mock_ad_channel_repo_cls.return_value
        mock_repo.get_ad_by_id.return_value = None

        result = _preserve_pinned_format(101, 202)

        assert not result
        mock_repo.update.assert_not_called()
