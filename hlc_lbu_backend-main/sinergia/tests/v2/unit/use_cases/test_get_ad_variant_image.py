"""Unit_Test_Suite for GetAdVariantImageUseCase (spec get-ad-variant-image-use-case)."""
from unittest.mock import call as mocker_call

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from app.exceptions.base import (
    DataNotFoundException, ImageLibraryException, ParametersNotFoundException, StrapiException)
from app.v2.use_cases.image_library import GetAdVariantImageUseCase

PARAM_NAMES = ('brand_id', 'campaign_id', 'ad_id', 'channel_id', 'variant_id', 'image_id')
PARAM_MESSAGES = {
    'brand_id': 'Brand Id is required',
    'campaign_id': 'Campaign Id is required',
    'ad_id': 'Ad Id is required',
    'channel_id': 'Channel Id is required',
    'variant_id': 'Variant Id is required',
    'image_id': 'Image Id is required',
}
INVALID_VALUES = [None, '', '   ', '\t\n', 0]

VALID_ARGS = {
    'brand_id': 1,
    'campaign_id': 10,
    'ad_id': 20,
    'channel_id': 30,
    'variant_id': 50,
    'image_id': 'img-abc',
}


def _args(**overrides):
    values = dict(VALID_ARGS)
    values.update(overrides)
    return tuple(values[name] for name in PARAM_NAMES)


@pytest.fixture
def repos(mocker):
    campaign_cls = mocker.patch('app.v2.use_cases.image_library.CampaignRepository')
    ad_channel_cls = mocker.patch('app.v2.use_cases.image_library.AdChannelRepository')
    image_cls = mocker.patch('app.v2.use_cases.image_library.ImageLibraryRepository')
    campaign_cls.return_value.get_by_id_and_brand.return_value = {'id': 10}
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.return_value = {'id': 50}
    image_cls.return_value.get_image.return_value = {'url': 'https://img/x.png', 'image_prompt': 'p'}
    return campaign_cls, ad_channel_cls, image_cls


def _assert_no_repository_calls(repos) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    campaign_cls.return_value.get_by_id_and_brand.assert_not_called()
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.assert_not_called()
    image_cls.return_value.get_image.assert_not_called()


# --- Requirement 2: construction --------------------------------------------

def test_init_instantiates_repositories(repos) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos

    use_case = GetAdVariantImageUseCase()

    campaign_cls.assert_called_once_with()
    ad_channel_cls.assert_called_once_with()
    image_cls.assert_called_once_with()
    assert use_case.campaign_repository is campaign_cls.return_value
    assert use_case.ad_channel_repository is ad_channel_cls.return_value
    assert use_case.image_library_repository is image_cls.return_value


def test_execute_uses_injected_repositories_only(repos) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    use_case = GetAdVariantImageUseCase()

    use_case.execute(*_args())

    # Classes are only instantiated in __init__, never inside execute
    assert campaign_cls.call_count == 1
    assert ad_channel_cls.call_count == 1
    assert image_cls.call_count == 1
    campaign_cls.return_value.get_by_id_and_brand.assert_called_once()
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.assert_called_once()
    image_cls.return_value.get_image.assert_called_once()


# --- Requirement 3: parameter validation ------------------------------------

@pytest.mark.parametrize('invalid_value', INVALID_VALUES, ids=repr)
@pytest.mark.parametrize('param_name', PARAM_NAMES)
def test_invalid_param_raises_parameters_not_found(repos, param_name, invalid_value) -> None:
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(ParametersNotFoundException) as exc_info:
        use_case.execute(*_args(**{param_name: invalid_value}))

    assert exc_info.value.code == 'PAR001'
    assert exc_info.value.text == PARAM_MESSAGES[param_name]


def test_validation_reports_first_invalid_param_in_order(repos) -> None:
    use_case = GetAdVariantImageUseCase()

    # campaign_id, channel_id and image_id invalid -> campaign_id reported
    with pytest.raises(ParametersNotFoundException) as exc_info:
        use_case.execute(*_args(campaign_id=0, channel_id=None, image_id=''))
    assert exc_info.value.code == 'PAR001'
    assert exc_info.value.text == 'Campaign Id is required'

    # all invalid -> brand_id reported
    with pytest.raises(ParametersNotFoundException) as exc_info:
        use_case.execute(None, None, None, None, None, None)
    assert exc_info.value.text == 'Brand Id is required'

    # variant_id and image_id invalid -> variant_id reported
    with pytest.raises(ParametersNotFoundException) as exc_info:
        use_case.execute(*_args(variant_id='  ', image_id=None))
    assert exc_info.value.text == 'Variant Id is required'


@pytest.mark.parametrize('param_name', PARAM_NAMES)
def test_invalid_param_does_not_call_repositories(repos, param_name) -> None:
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(ParametersNotFoundException) as exc_info:
        use_case.execute(*_args(**{param_name: None}))

    assert exc_info.value.text == PARAM_MESSAGES[param_name]
    _assert_no_repository_calls(repos)


@pytest.mark.parametrize('overrides', [
    {'brand_id': -1, 'campaign_id': -10, 'ad_id': -20, 'channel_id': -30, 'variant_id': -50},
    {'image_id': '0'},
    {'brand_id': -7, 'image_id': '0'},
], ids=['negative-ints', 'image-id-zero-string', 'mixed'])
def test_valid_edge_values_pass_validation(repos, overrides) -> None:
    campaign_cls, _, image_cls = repos
    use_case = GetAdVariantImageUseCase()
    args = _args(**overrides)

    result = use_case.execute(*args)

    campaign_cls.return_value.get_by_id_and_brand.assert_called_once_with(args[1], args[0])
    image_cls.return_value.get_image.assert_called_once_with(args[5])
    assert result['id'] == args[5]


def test_image_id_is_not_trimmed(repos) -> None:
    _, _, image_cls = repos
    use_case = GetAdVariantImageUseCase()
    padded_id = '  img-abc \t'

    result = use_case.execute(*_args(image_id=padded_id))

    image_cls.return_value.get_image.assert_called_once_with(padded_id)
    assert result['id'] == padded_id


# --- Requirement 4: campaign lookup -----------------------------------------

def test_success_calls_campaign_lookup_with_campaign_and_brand(repos) -> None:
    campaign_cls, _, _ = repos
    use_case = GetAdVariantImageUseCase()

    use_case.execute(*_args())

    campaign_cls.return_value.get_by_id_and_brand.assert_called_once_with(
        VALID_ARGS['campaign_id'], VALID_ARGS['brand_id'])


def test_campaign_not_found_raises_and_short_circuits(repos) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    campaign_cls.return_value.get_by_id_and_brand.return_value = None
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(DataNotFoundException) as exc_info:
        use_case.execute(*_args())

    assert type(exc_info.value) is DataNotFoundException
    assert exc_info.value.code == 'DAT001'
    assert exc_info.value.text == 'Campaign not found for brand'
    campaign_cls.return_value.get_by_id_and_brand.assert_called_once()
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.assert_not_called()
    image_cls.return_value.get_image.assert_not_called()


@pytest.mark.parametrize('campaign', [
    {'id': 10},
    {},
    {'id': 10, 'attributes': {'name': 'c'}},
    [],
    0,
    '',
], ids=repr)
def test_campaign_found_continues_to_variant_lookup(repos, campaign) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    campaign_cls.return_value.get_by_id_and_brand.return_value = campaign
    use_case = GetAdVariantImageUseCase()

    result = use_case.execute(*_args())

    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.assert_called_once()
    image_cls.return_value.get_image.assert_called_once()
    assert result['id'] == VALID_ARGS['image_id']


def test_campaign_lookup_exception_propagates(repos) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    original = StrapiException(text='Failed to GET campaigns: timeout')
    campaign_cls.return_value.get_by_id_and_brand.side_effect = original
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(StrapiException) as exc_info:
        use_case.execute(*_args())

    assert exc_info.value is original
    assert exc_info.value.code == 'STRAPI001'
    assert exc_info.value.text == 'Failed to GET campaigns: timeout'
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.assert_not_called()
    image_cls.return_value.get_image.assert_not_called()


# --- Requirement 5: ad variant (ad-channel) lookup --------------------------

def test_success_calls_variant_lookup_with_expected_args(repos) -> None:
    _, ad_channel_cls, _ = repos
    use_case = GetAdVariantImageUseCase()

    use_case.execute(*_args())

    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.assert_called_once_with(
        VALID_ARGS['variant_id'], VALID_ARGS['ad_id'],
        VALID_ARGS['campaign_id'], VALID_ARGS['channel_id'])


def test_variant_not_found_raises_and_short_circuits(repos) -> None:
    _, ad_channel_cls, image_cls = repos
    # Repository returns None when the ad-channel does not match all filters (5.6)
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.return_value = None
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(DataNotFoundException) as exc_info:
        use_case.execute(*_args())

    assert type(exc_info.value) is DataNotFoundException
    assert exc_info.value.code == 'DAT001'
    assert exc_info.value.text == 'Ad variant not found'
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.assert_called_once()
    image_cls.return_value.get_image.assert_not_called()


def test_variant_lookup_strapi_exception_propagates(repos) -> None:
    _, ad_channel_cls, image_cls = repos
    original = StrapiException(text='Failed to GET ad-channels: Read timed out')
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.side_effect = original
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(StrapiException) as exc_info:
        use_case.execute(*_args())

    assert exc_info.value is original
    assert exc_info.value.code == 'STRAPI001'
    assert exc_info.value.text == 'Failed to GET ad-channels: Read timed out'
    image_cls.return_value.get_image.assert_not_called()


# --- Requirement 6: image lookup and response -------------------------------

def test_success_calls_get_image_once(repos) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    use_case = GetAdVariantImageUseCase()

    use_case.execute(*_args())

    image_repo = image_cls.return_value
    image_repo.get_image.assert_called_once_with(VALID_ARGS['image_id'])
    args, kwargs = image_repo.get_image.call_args
    assert args == (VALID_ARGS['image_id'],)
    assert kwargs == {}
    # No further repository calls after get_image (6.4)
    assert campaign_cls.return_value.method_calls == [
        mocker_call.get_by_id_and_brand(VALID_ARGS['campaign_id'], VALID_ARGS['brand_id'])]
    assert ad_channel_cls.return_value.method_calls == [
        mocker_call.get_by_id_ad_campaign_and_channel(
            VALID_ARGS['variant_id'], VALID_ARGS['ad_id'],
            VALID_ARGS['campaign_id'], VALID_ARGS['channel_id'])]
    assert image_repo.method_calls == [mocker_call.get_image(VALID_ARGS['image_id'])]


@pytest.mark.parametrize('record', [
    None,
    ['https://img/x.png'],
    'https://img/x.png',
    {},
    {'image_prompt': 'p', 'imageId': 'img-abc'},
    {'url': 123},
    {'url': None},
    {'url': ['https://img/x.png']},
    {'url': ''},
    {'url': '   '},
    {'url': ' \t\n'},
    {'detail': 'Image not found'},
], ids=repr)
def test_image_not_found_raises_data_not_found(repos, record) -> None:
    _, _, image_cls = repos
    image_cls.return_value.get_image.return_value = record
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(DataNotFoundException) as exc_info:
        use_case.execute(*_args())

    assert type(exc_info.value) is DataNotFoundException
    assert exc_info.value.code == 'DAT001'
    assert exc_info.value.text == 'Image not found'


def test_image_library_exception_propagates(repos) -> None:
    _, _, image_cls = repos
    original = ImageLibraryException(text='Failed to GET images/img-abc: timeout')
    image_cls.return_value.get_image.side_effect = original
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(ImageLibraryException) as exc_info:
        use_case.execute(*_args())

    assert exc_info.value is original
    assert type(exc_info.value) is ImageLibraryException
    assert exc_info.value.code == 'IMG001'
    assert exc_info.value.text == 'Failed to GET images/img-abc: timeout'


def test_success_returns_id_url_prompt(repos) -> None:
    _, _, image_cls = repos
    url = ' https://bucket.s3/x.png?X-Amz-Signature=abc '
    image_cls.return_value.get_image.return_value = {
        'id': 'other-id',
        'imageId': 'other-id',
        'url': url,
        'image_prompt': 'a red car',
        'metadata': {'brand': 1},
    }
    use_case = GetAdVariantImageUseCase()

    result = use_case.execute(*_args())

    assert result == {'id': VALID_ARGS['image_id'], 'url': url, 'prompt': 'a red car'}
    assert set(result) == {'id', 'url', 'prompt'}


def test_success_returns_empty_string_prompt_unchanged(repos) -> None:
    _, _, image_cls = repos
    image_cls.return_value.get_image.return_value = {'url': 'https://img/x.png', 'image_prompt': ''}
    use_case = GetAdVariantImageUseCase()

    result = use_case.execute(*_args())

    assert result == {'id': VALID_ARGS['image_id'], 'url': 'https://img/x.png', 'prompt': ''}


_MISSING = object()


@pytest.mark.parametrize('prompt', [_MISSING, None, 42, ['a'], {'text': 'a'}],
                         ids=['missing', 'none', 'int', 'list', 'dict'])
def test_missing_or_null_image_prompt_returns_empty_string(repos, prompt) -> None:
    _, _, image_cls = repos
    record = {'url': 'https://img/x.png'}
    if prompt is not _MISSING:
        record['image_prompt'] = prompt
    image_cls.return_value.get_image.return_value = record
    use_case = GetAdVariantImageUseCase()

    result = use_case.execute(*_args())

    assert result == {'id': VALID_ARGS['image_id'], 'url': 'https://img/x.png', 'prompt': ''}


# --- Requirements 2.4, 3.9: error logging -----------------------------------

def _configure_campaign_not_found(repos) -> None:
    repos[0].return_value.get_by_id_and_brand.return_value = None


def _configure_variant_not_found(repos) -> None:
    repos[1].return_value.get_by_id_ad_campaign_and_channel.return_value = None


def _configure_image_not_found(repos) -> None:
    repos[2].return_value.get_image.return_value = {'detail': 'Image not found'}


@pytest.mark.parametrize('overrides, configure, exc_cls, text, identifiers', [
    ({'ad_id': 0}, None, ParametersNotFoundException, 'Ad Id is required', []),
    ({}, _configure_campaign_not_found, DataNotFoundException, 'Campaign not found for brand',
     ['campaign_id=10', 'brand_id=1']),
    ({}, _configure_variant_not_found, DataNotFoundException, 'Ad variant not found',
     ['variant_id=50', 'ad_id=20', 'campaign_id=10', 'channel_id=30']),
    ({}, _configure_image_not_found, DataNotFoundException, 'Image not found',
     ['image_id=img-abc']),
], ids=['invalid-param', 'campaign-not-found', 'variant-not-found', 'image-not-found'])
def test_errors_are_logged_once_before_raising(
        repos, mocker, overrides, configure, exc_cls, text, identifiers) -> None:
    logger = mocker.patch('app.v2.use_cases.image_library.logger')
    if configure is not None:
        configure(repos)
    use_case = GetAdVariantImageUseCase()

    with pytest.raises(exc_cls) as exc_info:
        use_case.execute(*_args(**overrides))

    assert type(exc_info.value) is exc_cls
    assert exc_info.value.text == text
    assert logger.error.call_count == 1
    message = str(logger.error.call_args[0][0])
    assert text in message
    for identifier in identifiers:
        assert identifier in message


# --- Property-based tests ----------------------------------------------------

_valid_int_ids = st.integers().filter(lambda x: x != 0)
_valid_image_ids = st.text(min_size=1).filter(lambda s: s.strip())
_valid_tuples = st.tuples(
    _valid_int_ids, _valid_int_ids, _valid_int_ids, _valid_int_ids, _valid_int_ids, _valid_image_ids)
_invalid_values = st.sampled_from([None, '', 0]) | st.text(alphabet=' \t\n\r', min_size=1)
_invalid_overrides = st.dictionaries(
    st.integers(min_value=0, max_value=len(PARAM_NAMES) - 1), _invalid_values, min_size=1)


# Feature: get-ad-variant-image-use-case, Property 1: Los Path_Params inválidos se rechazan en orden y sin acceder a datos
# **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(valid=_valid_tuples, overrides=_invalid_overrides)
def test_property_invalid_params_rejected_in_order(repos, valid, overrides) -> None:
    for repo_cls in repos:
        repo_cls.reset_mock()

    args = list(valid)
    for position, invalid_value in overrides.items():
        args[position] = invalid_value
    first_invalid = PARAM_NAMES[min(overrides)]

    use_case = GetAdVariantImageUseCase()
    with pytest.raises(ParametersNotFoundException) as exc_info:
        use_case.execute(*args)

    assert type(exc_info.value) is ParametersNotFoundException
    assert exc_info.value.code == 'PAR001'
    assert exc_info.value.text == PARAM_MESSAGES[first_invalid]
    _assert_no_repository_calls(repos)


_whitespace_padding = st.text(alphabet=' \t\n', max_size=3)
_padded_image_ids = st.tuples(_whitespace_padding, _valid_image_ids, _whitespace_padding).map(''.join)


def _recording(calls, name, result):
    def _side_effect(*args, **kwargs):
        calls.append((name, args, kwargs))
        return result
    return _side_effect


# Feature: get-ad-variant-image-use-case, Property 2: Los Path_Params válidos llegan sin transformar a cada colaborador
# **Validates: Requirements 3.10, 3.11, 4.2, 5.2, 6.1**
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    brand_id=_valid_int_ids,
    campaign_id=_valid_int_ids,
    ad_id=_valid_int_ids,
    channel_id=_valid_int_ids,
    variant_id=_valid_int_ids,
    image_id=_padded_image_ids,
)
@example(brand_id=1, campaign_id=10, ad_id=20, channel_id=30, variant_id=50, image_id='0')
@example(brand_id=-1, campaign_id=-10, ad_id=-20, channel_id=-30, variant_id=-50, image_id=' img \t')
def test_property_valid_params_forwarded_unchanged(
        repos, brand_id, campaign_id, ad_id, channel_id, variant_id, image_id) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    for repo_cls in repos:
        repo_cls.reset_mock()

    calls = []
    campaign_repo = campaign_cls.return_value
    ad_channel_repo = ad_channel_cls.return_value
    image_repo = image_cls.return_value
    campaign_repo.get_by_id_and_brand.side_effect = _recording(calls, 'campaign', {'id': campaign_id})
    ad_channel_repo.get_by_id_ad_campaign_and_channel.side_effect = _recording(
        calls, 'variant', {'id': variant_id})
    image_repo.get_image.side_effect = _recording(
        calls, 'image', {'url': 'https://img/x.png', 'image_prompt': 'p'})

    use_case = GetAdVariantImageUseCase()
    result = use_case.execute(brand_id, campaign_id, ad_id, channel_id, variant_id, image_id)

    assert calls == [
        ('campaign', (campaign_id, brand_id), {}),
        ('variant', (variant_id, ad_id, campaign_id, channel_id), {}),
        ('image', (image_id,), {}),
    ]
    campaign_repo.get_by_id_and_brand.assert_called_once_with(campaign_id, brand_id)
    ad_channel_repo.get_by_id_ad_campaign_and_channel.assert_called_once_with(
        variant_id, ad_id, campaign_id, channel_id)
    image_repo.get_image.assert_called_once_with(image_id)
    assert result['id'] == image_id


_json_scalars = st.one_of(st.none(), st.booleans(), st.integers(), st.floats(allow_nan=False), st.text())
_extra_keys = st.dictionaries(
    st.text().filter(lambda k: k != 'url'), _json_scalars, max_size=5)
_non_str_urls = st.one_of(
    st.none(), st.booleans(), st.integers(), st.floats(allow_nan=False),
    st.lists(st.text(), max_size=3), st.dictionaries(st.text(), st.text(), max_size=3))
_blank_urls = st.text(alphabet=' \t\n\r', max_size=5)  # includes ''


def _with_url(url_strategy):
    return st.tuples(_extra_keys, url_strategy).map(lambda pair: {**pair[0], 'url': pair[1]})


_non_existing_images = st.one_of(
    st.none(),
    st.integers(),
    st.lists(_json_scalars, max_size=5),
    st.text(),
    st.just({}),
    _extra_keys,                 # dict without 'url' (may be empty)
    _with_url(_non_str_urls),    # 'url' is not a str
    _with_url(_blank_urls),      # 'url' empty or whitespace only
)


# Feature: get-ad-variant-image-use-case, Property 3: Los registros que no son Existing_Image producen "Image not found"
# **Validates: Requirements 6.2**
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(record=_non_existing_images)
def test_property_non_existing_image_raises_not_found(repos, record) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    for repo_cls in repos:
        repo_cls.reset_mock()
    campaign_cls.return_value.get_by_id_and_brand.return_value = {'id': 10}
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.return_value = {'id': 50}
    image_cls.return_value.get_image.return_value = record

    use_case = GetAdVariantImageUseCase()
    with pytest.raises(DataNotFoundException) as exc_info:
        use_case.execute(*_args())

    assert type(exc_info.value) is DataNotFoundException
    assert exc_info.value.code == 'DAT001'
    assert exc_info.value.text == 'Image not found'
    image_cls.return_value.get_image.assert_called_once_with(VALID_ARGS['image_id'])


_PROMPT_MISSING = object()
_existing_urls = st.tuples(_whitespace_padding, _valid_image_ids, _whitespace_padding).map(''.join)
_record_extra_values = st.one_of(
    _json_scalars, st.lists(st.integers(), max_size=3), st.dictionaries(st.text(), st.text(), max_size=3))
_record_extra_keys = st.dictionaries(
    st.text().filter(lambda k: k not in ('url', 'image_prompt')), _record_extra_values, max_size=5)
_image_prompts = st.one_of(
    st.just(_PROMPT_MISSING),
    st.none(),
    st.text(),
    st.integers(),
    st.lists(st.text(), max_size=3),
    st.dictionaries(st.text(), st.text(), max_size=3),
)


# Feature: get-ad-variant-image-use-case, Property 4: La respuesta es exactamente {id, url, prompt} con valores str derivados del registro
# **Validates: Requirements 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 7.7**
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    image_id=_padded_image_ids,
    url=_existing_urls,
    extra=_record_extra_keys,
    record_id=_record_extra_values,
    prompt=_image_prompts,
)
def test_property_response_keys_and_types(repos, image_id, url, extra, record_id, prompt) -> None:
    campaign_cls, ad_channel_cls, image_cls = repos
    for repo_cls in repos:
        repo_cls.reset_mock()
    campaign_cls.return_value.get_by_id_and_brand.return_value = {'id': 10}
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.return_value = {'id': 50}

    record = dict(extra)
    # Record 'id' always differs from image_id so the response must not use it
    record['id'] = record_id if record_id != image_id else ['not', image_id]
    record['url'] = url
    if prompt is not _PROMPT_MISSING:
        record['image_prompt'] = prompt
    image_cls.return_value.get_image.return_value = record

    use_case = GetAdVariantImageUseCase()
    result = use_case.execute(*_args(image_id=image_id))

    assert set(result) == {'id', 'url', 'prompt'}
    assert all(isinstance(value, str) for value in result.values())
    assert result['id'] == image_id
    assert result['url'] == record['url']
    expected_prompt = prompt if isinstance(prompt, str) else ''
    assert result['prompt'] == expected_prompt
    image_cls.return_value.get_image.assert_called_once_with(image_id)
