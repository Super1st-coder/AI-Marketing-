"""Unit_Test_Suite for EditAdVariantImageUseCase (spec edit-ad-variant-image-use-case)."""
from types import SimpleNamespace
from typing import Any, Dict

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from app.exceptions.base import (DataNotFoundException, FuryException,
                                 IncorrectValidationException, ParametersNotFoundException,
                                 StrapiException)
from app.v2.use_cases.ad import (EDIT_IMAGE_REQUIRED_FIELDS, EditAdVariantImageUseCase,
                                 _edit_image_extract_job_id, _edit_image_has_banner_image,
                                 _edit_image_parent_account_id)

USER_ID = 'admin@hiluca.test'

VALID_PAYLOAD: Dict[str, Any] = {
    'brand_id': 1,
    'campaign_id': 10,
    'ad_id': 20,
    'channel_id': 30,
    'variant_id': 50,
    'image_name': 'banner-1',
    'image_id': 'img-abc',
    'n_variations': 3,
    'custom_prompt': 'Cambia el fondo a azul',
    'expand_zoom_option': 'ZOOM_1_5X',
}

# Sentinel: passing a field with this value removes the key from the payload.
MISSING = object()

# Pipeline steps in execution order; a failure at one step must leave the
# collaborators of every later step untouched (Req 10.10).
_STEPS = ('validation', 'account', 'campaign', 'variant', 'image')


def _payload(**overrides: Any) -> Dict[str, Any]:
    """Return a copy of VALID_PAYLOAD with overrides applied; MISSING drops the key."""
    values = dict(VALID_PAYLOAD)
    for key, value in overrides.items():
        if value is MISSING:
            values.pop(key, None)
        else:
            values[key] = value
    return values


def _assert_not_called_after(step: str, collaborators: SimpleNamespace) -> None:
    """Assert zero invocations of the collaborators that run after the failed step."""
    index = _STEPS.index(step)
    later_calls = [
        ('account', collaborators.account.return_value.get_by_email),
        ('campaign', collaborators.campaign.return_value.get_by_id_brand_and_account),
        ('variant', collaborators.ad_channel.return_value.get_by_id_ad_campaign_and_channel),
        ('image', collaborators.fury.return_value.post),
    ]
    for owner_step, method in later_calls:
        # A collaborator method is "after" the failed step when the step that
        # invokes it comes later in the pipeline than the failed step.
        if _STEPS.index(owner_step) > index:
            method.assert_not_called()


@pytest.fixture
def collaborators(mocker):
    account_cls = mocker.patch('app.v2.use_cases.ad.AccountRepository')
    campaign_cls = mocker.patch('app.v2.use_cases.ad.CampaignRepository')
    ad_channel_cls = mocker.patch('app.v2.use_cases.ad.AdChannelRepository')
    fury_cls = mocker.patch('app.v2.use_cases.ad.FuryClient')
    logger = mocker.patch('app.v2.use_cases.ad.logger')
    account_cls.return_value.get_by_email.return_value = {
        'id': 7, 'attributes': {'parent_account': {'data': None}}}
    campaign_cls.return_value.get_by_id_brand_and_account.return_value = {'id': 10}
    ad_channel_cls.return_value.get_by_id_ad_campaign_and_channel.return_value = {
        'id': 50, 'attributes': {'media_images_banner': [{'name': 'banner-1', 'image_id': 'img-abc'}]}}
    fury_cls.return_value.post.return_value = {
        'ok': 1, 'data': {'edit_job_id': 'job-1', 'status': 'RUNNING', 'poll_url': '/api/v2/jobs/job-1'}}
    return SimpleNamespace(account=account_cls, campaign=campaign_cls, ad_channel=ad_channel_cls,
                           fury=fury_cls, logger=logger)


# --- Requirement 2: construction (Req 10.14) --------------------------------

def test_init_stores_user_id_and_instantiates_collaborators_once(collaborators) -> None:
    use_case = EditAdVariantImageUseCase(USER_ID)

    assert use_case.user_id == USER_ID
    for cls in (collaborators.account, collaborators.campaign,
                collaborators.ad_channel, collaborators.fury):
        cls.assert_called_once_with()

    use_case.execute(_payload())

    for cls in (collaborators.account, collaborators.campaign,
                collaborators.ad_channel, collaborators.fury):
        assert cls.call_count == 1
    collaborators.account.return_value.get_by_email.assert_called_once_with(USER_ID)


# --- Requirement 9: happy path (Req 10.5) -----------------------------------

def test_happy_path_returns_job_id_and_posts_expected_payload(collaborators) -> None:
    result = EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert result == {'job_id': 'job-1'}
    expected = {
        'brand_id': 1,
        'campaign_id': 10,
        'ad_id': 20,
        'channel_id': 30,
        'variant_id': 50,
        'image_name': 'banner-1',
        'id_base_image': 'img-abc',
        'n_variations': 3,
        'custom_prompt': 'Cambia el fondo a azul',
        'expand_zoom_option': 'ZOOM_1_5X',
    }
    collaborators.fury.return_value.post.assert_called_once_with('/api/v2/variants/image/edit', expected)
    sent = collaborators.fury.return_value.post.call_args[0][1]
    assert len(sent) == 10
    assert 'id_base_image' in sent
    assert 'image_id' not in sent


# --- Requirement 3: presence of required parameters (Req 10.6) -------------

_REQUIRED_FIELDS = ('brand_id', 'campaign_id', 'ad_id', 'channel_id', 'variant_id',
                    'image_name', 'image_id', 'n_variations')
_MISSING_VALUES = (None, '', '   ', MISSING)


@pytest.mark.parametrize('missing_value', _MISSING_VALUES, ids=['none', 'empty', 'blank', 'absent'])
@pytest.mark.parametrize('field', _REQUIRED_FIELDS)
def test_missing_required_field_raises_parameters_not_found(collaborators, field: str,
                                                            missing_value: Any) -> None:
    with pytest.raises(ParametersNotFoundException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload(**{field: missing_value}))

    assert excinfo.value.code == 'PAR001'
    assert excinfo.value.text == f'{field} is required'
    _assert_not_called_after('validation', collaborators)


@pytest.mark.parametrize('payload', [None, [], 'x'], ids=['none', 'list', 'str'])
def test_non_dict_payload_raises_parameters_not_found(collaborators, payload: Any) -> None:
    with pytest.raises(ParametersNotFoundException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(payload)

    assert excinfo.value.code == 'PAR001'
    assert excinfo.value.text == 'Payload is required'
    _assert_not_called_after('validation', collaborators)


# --- Requirement 4: value validation (Req 10.7, 10.10) ----------------------

_ID_FIELDS = ('brand_id', 'campaign_id', 'ad_id', 'channel_id', 'variant_id')
_STRING_MSG = 'must be a string of at most 255 characters'
_PROMPT_MSG = 'custom_prompt must be a string of at most 2000 characters'
_ZOOM_MSG = ('expand_zoom_option must be one of: '
             'TOP, BOTTOM, LEFT, RIGHT, ZOOM_2X, ZOOM_1_5X, ZOOM_1_25X')
_REQUIRES_ONE_MSG = 'custom_prompt or expand_zoom_option is required'


def _invalid_cases() -> list:
    cases = []
    for field in _ID_FIELDS:
        for value in (0, -1, True, 1.0, '5'):
            cases.append(pytest.param(
                {field: value}, f'{field} must be an integer greater than or equal to 1',
                id=f'{field}-{value!r}'))
    for value in (0, 11, True, '5'):
        cases.append(pytest.param(
            {'n_variations': value}, 'n_variations must be an integer between 1 and 10',
            id=f'n_variations-{value!r}'))
    for field in ('image_name', 'image_id'):
        cases.append(pytest.param(
            {field: '  ' + 'a' * 256 + '  '}, f'{field} {_STRING_MSG}', id=f'{field}-256'))
        cases.append(pytest.param({field: 123}, f'{field} {_STRING_MSG}', id=f'{field}-int'))
    cases.append(pytest.param(
        {'custom_prompt': '  ' + 'p' * 2001 + '  '}, _PROMPT_MSG, id='custom_prompt-2001'))
    cases.append(pytest.param({'custom_prompt': 123}, _PROMPT_MSG, id='custom_prompt-int'))
    for value in ('top', 'ZOOM_3X', ' TOP', ''):
        cases.append(pytest.param(
            {'expand_zoom_option': value}, _ZOOM_MSG, id=f'expand_zoom_option-{value!r}'))
    for value in (None, '', '   '):
        cases.append(pytest.param(
            {'custom_prompt': value, 'expand_zoom_option': MISSING}, _REQUIRES_ONE_MSG,
            id=f'no-prompt-no-option-{value!r}'))
    return cases


@pytest.mark.parametrize('overrides, expected_text', _invalid_cases())
def test_invalid_value_raises_incorrect_validation(collaborators, overrides: Dict[str, Any],
                                                   expected_text: str) -> None:
    with pytest.raises(IncorrectValidationException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload(**overrides))

    assert excinfo.value.code == 'SYSVAL001'
    assert excinfo.value.text == expected_text
    _assert_not_called_after('validation', collaborators)


# --- Requirement 4: valid boundary values (Req 10.8) ------------------------

_LONG_NAME = 'n' * 255
_LONG_IMAGE_ID = 'i' * 255
_LONG_PROMPT = 'p' * 2000


def _boundary_cases() -> list:
    cases = [
        pytest.param({field: 1 for field in _ID_FIELDS}, id='ids-1'),
        pytest.param({'n_variations': 1}, id='n_variations-1'),
        pytest.param({'n_variations': 10}, id='n_variations-10'),
        pytest.param({'image_name': '  ' + _LONG_NAME + '  '}, id='image_name-255'),
        pytest.param({'image_id': '  ' + _LONG_IMAGE_ID + '  '}, id='image_id-255'),
        pytest.param({'custom_prompt': '  ' + _LONG_PROMPT + '  '}, id='custom_prompt-2000'),
    ]
    for option in ('TOP', 'BOTTOM', 'LEFT', 'RIGHT', 'ZOOM_2X', 'ZOOM_1_5X', 'ZOOM_1_25X'):
        cases.append(pytest.param({'expand_zoom_option': option}, id=f'expand_zoom_option-{option}'))
    return cases


@pytest.mark.parametrize('overrides', _boundary_cases())
def test_valid_boundary_values_return_job_id(collaborators, overrides: Dict[str, Any]) -> None:
    payload = _payload(**overrides)
    # The banner must match the stripped image_id sent in the payload (Req 4.9, 8.1).
    collaborators.ad_channel.return_value.get_by_id_ad_campaign_and_channel.return_value = {
        'id': 50,
        'attributes': {'media_images_banner': [
            {'name': payload['image_name'].strip(), 'image_id': payload['image_id'].strip()}]},
    }

    result = EditAdVariantImageUseCase(USER_ID).execute(payload)

    assert result == {'job_id': 'job-1'}
    collaborators.fury.return_value.post.assert_called_once()


# --- Property-based tests ---------------------------------------------------

_PAYLOAD_KEYS = frozenset(VALID_PAYLOAD)
_EXPAND_ZOOM_OPTIONS = ('TOP', 'BOTTOM', 'LEFT', 'RIGHT', 'ZOOM_2X', 'ZOOM_1_5X', 'ZOOM_1_25X')
_WHITESPACE = st.text(alphabet=' \t\n\r\x0b\x0c', max_size=5)
_ids = st.integers(min_value=1, max_value=10**9)


def _padded(core: st.SearchStrategy) -> st.SearchStrategy:
    """Wrap generated strings in arbitrary leading/trailing whitespace."""
    return st.tuples(_WHITESPACE, core, _WHITESPACE).map(lambda t: t[0] + t[1] + t[2])


_names = _padded(st.text(min_size=1, max_size=255).filter(lambda s: s.strip()))
_custom_prompts = st.one_of(
    st.just(MISSING), st.none(), _WHITESPACE, _padded(st.text(max_size=2000)))
_expand_zoom_options = st.one_of(st.just(MISSING), st.none(), st.sampled_from(_EXPAND_ZOOM_OPTIONS))
_extra_keys = st.dictionaries(
    st.text(max_size=20).filter(lambda k: k not in _PAYLOAD_KEYS and k != 'id_base_image'),
    st.one_of(st.none(), st.integers(), st.text(max_size=20), st.booleans()),
    max_size=5)


# Feature: edit-ad-variant-image-use-case, Property 1: Invariante de mapeo del Edit_Payload válido
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(brand_id=_ids, campaign_id=_ids, ad_id=_ids, channel_id=_ids, variant_id=_ids,
       n_variations=st.integers(min_value=1, max_value=10), image_name=_names, image_id=_names,
       custom_prompt=_custom_prompts, expand_zoom_option=_expand_zoom_options, extra=_extra_keys)
def test_property_valid_payload_maps_to_fury_payload(
        collaborators, brand_id: int, campaign_id: int, ad_id: int, channel_id: int,
        variant_id: int, n_variations: int, image_name: str, image_id: str, custom_prompt: Any,
        expand_zoom_option: Any, extra: Dict[str, Any]) -> None:
    """**Validates: Requirements 4.9, 6.1, 7.1, 9.1, 9.2, 9.3, 9.8** (Req 10.13)"""
    normalized_prompt = custom_prompt.strip() or None if isinstance(custom_prompt, str) else None
    expected_option = None if expand_zoom_option is MISSING else expand_zoom_option
    assume(normalized_prompt is not None or expected_option is not None)
    stripped_image_id = image_id.strip()
    # The logged image_id may legitimately contain the prompt text by coincidence.
    assume(normalized_prompt is None or normalized_prompt not in stripped_image_id)

    # Reset mocks per example; reset_mock() keeps return values, so the banner is re-set.
    for mock in (collaborators.account, collaborators.campaign, collaborators.ad_channel,
                 collaborators.fury, collaborators.logger):
        mock.reset_mock()
    variant_lookup = collaborators.ad_channel.return_value.get_by_id_ad_campaign_and_channel
    variant_lookup.return_value = {
        'id': variant_id,
        'attributes': {'media_images_banner': [
            {'name': image_name.strip(), 'image_id': stripped_image_id}]},
    }

    payload: Dict[str, Any] = dict(extra)
    payload.update({
        'brand_id': brand_id, 'campaign_id': campaign_id, 'ad_id': ad_id,
        'channel_id': channel_id, 'variant_id': variant_id, 'image_name': image_name,
        'image_id': image_id, 'n_variations': n_variations,
    })
    if custom_prompt is not MISSING:
        payload['custom_prompt'] = custom_prompt
    if expand_zoom_option is not MISSING:
        payload['expand_zoom_option'] = expand_zoom_option

    result = EditAdVariantImageUseCase(USER_ID).execute(payload)

    assert result == {'job_id': 'job-1'}
    # Lookups receive the values untransformed (parent account falls back to account id 7).
    collaborators.campaign.return_value.get_by_id_brand_and_account.assert_called_once_with(
        campaign_id, brand_id, 7)
    variant_lookup.assert_called_once_with(variant_id, ad_id, campaign_id, channel_id)

    post = collaborators.fury.return_value.post
    post.assert_called_once()
    endpoint, sent = post.call_args[0]
    assert endpoint == '/api/v2/variants/image/edit'
    assert sent == {
        'brand_id': brand_id,
        'campaign_id': campaign_id,
        'ad_id': ad_id,
        'channel_id': channel_id,
        'variant_id': variant_id,
        'image_name': image_name.strip(),
        'id_base_image': stripped_image_id,
        'n_variations': n_variations,
        'custom_prompt': normalized_prompt,
        'expand_zoom_option': expected_option,
    }
    assert len(sent) == 10
    assert 'image_id' not in sent

    # The prompt text is never logged (Req 9.8).
    if normalized_prompt is not None and len(normalized_prompt) >= 20:
        for call in collaborators.logger.info.call_args_list:
            for arg in list(call.args) + list(call.kwargs.values()):
                assert normalized_prompt not in str(arg)


_missing_values = st.one_of(st.just(MISSING), st.none(), st.text(alphabet=' \t\n\r\x0b\x0c'))
# Present (non-Missing_Value) values that are invalid for at least some fields (Req 3.3, 3.5).
_present_invalid_values = st.one_of(
    st.integers(max_value=0), st.integers(min_value=11), st.booleans(),
    st.floats(allow_nan=False), st.text(min_size=1, max_size=10).filter(lambda s: s.strip()),
    st.text(min_size=256, max_size=300).filter(lambda s: len(s.strip()) > 255),
    st.lists(st.integers(), max_size=3), st.just({}))
_optional_field_values = st.one_of(st.just(MISSING), st.none(), _present_invalid_values)
_non_dict_payloads = st.one_of(
    st.none(), st.lists(st.integers(), max_size=3), st.text(max_size=10), st.integers())


# Feature: edit-ad-variant-image-use-case, Property 2: Los parámetros obligatorios ausentes se rechazan en orden y sin acceder a datos
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(non_dict=st.booleans(), data=st.data())
def test_property_missing_required_fields_rejected_in_order(
        collaborators, non_dict: bool, data: st.DataObject) -> None:
    """**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 4.8**"""
    for mock in (collaborators.account, collaborators.campaign, collaborators.ad_channel,
                 collaborators.fury, collaborators.logger):
        mock.reset_mock()

    if non_dict:
        payload: Any = data.draw(_non_dict_payloads, label='payload')
        expected_text = 'Payload is required'
    else:
        missing_fields = data.draw(
            st.sets(st.sampled_from(EDIT_IMAGE_REQUIRED_FIELDS), min_size=1), label='missing')
        overrides: Dict[str, Any] = {
            field: data.draw(_missing_values, label=f'missing {field}') for field in missing_fields}
        # Optionally make other (present) fields invalid; presence must still win (Req 3.5).
        for field in VALID_PAYLOAD:
            if field in missing_fields:
                continue
            values = (_optional_field_values if field in ('custom_prompt', 'expand_zoom_option')
                      else _present_invalid_values)
            if data.draw(st.booleans(), label=f'invalidate {field}'):
                overrides[field] = data.draw(values, label=f'value {field}')
        payload = _payload(**overrides)
        first_missing = next(f for f in EDIT_IMAGE_REQUIRED_FIELDS if f in missing_fields)
        expected_text = f'{first_missing} is required'

    with pytest.raises(ParametersNotFoundException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(payload)

    assert type(excinfo.value) is ParametersNotFoundException
    assert excinfo.value.code == 'PAR001'
    assert excinfo.value.text == expected_text
    for method in (collaborators.account.return_value.get_by_email,
                   collaborators.campaign.return_value.get_by_id_brand_and_account,
                   collaborators.ad_channel.return_value.get_by_id_ad_campaign_and_channel,
                   collaborators.fury.return_value.post):
        method.assert_not_called()
    for cls in (collaborators.account, collaborators.campaign,
                collaborators.ad_channel, collaborators.fury):
        assert cls.return_value.method_calls == []


def _repeated(min_size: int, max_size: int) -> st.SearchStrategy:
    """Long strings built by repetition (cheap to generate), padded with whitespace."""
    core = st.tuples(st.integers(min_value=min_size, max_value=max_size),
                     st.sampled_from('abcXYZ0')).map(lambda t: t[1] * t[0])
    return _padded(core)


_numeric_strings = _padded(st.integers().map(str))
_non_int_values = st.one_of(st.booleans(), st.floats(), _numeric_strings,
                            st.lists(st.integers(), max_size=3))
_invalid_ids = st.one_of(_non_int_values, st.integers(max_value=0))
_invalid_n_variations = st.one_of(
    _non_int_values, st.integers(max_value=0), st.integers(min_value=11))
_non_str_values = st.one_of(st.booleans(), st.integers(), st.floats(),
                            st.lists(st.integers(), max_size=3))
_invalid_strings_255 = st.one_of(_non_str_values, _repeated(256, 300))
_invalid_prompts = st.one_of(_non_str_values, _repeated(2001, 2100))
_invalid_options = st.one_of(
    st.text(max_size=12).filter(lambda s: s not in _EXPAND_ZOOM_OPTIONS),
    st.sampled_from(_EXPAND_ZOOM_OPTIONS).map(str.lower),
    _WHITESPACE.flatmap(lambda ws: st.sampled_from(_EXPAND_ZOOM_OPTIONS).map(
        lambda o: ' ' + ws + o)),
    _non_str_values)
_INVALID_VALUE_STRATEGIES: Dict[str, st.SearchStrategy] = {
    **{field: _invalid_ids for field in _ID_FIELDS},
    'image_name': _invalid_strings_255,
    'image_id': _invalid_strings_255,
    'n_variations': _invalid_n_variations,
    'custom_prompt': _invalid_prompts,
    'expand_zoom_option': _invalid_options,
}
_VALIDATION_ORDER = (*_ID_FIELDS, 'image_name', 'image_id', 'n_variations',
                     'custom_prompt', 'expand_zoom_option')


def _is_valid_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _expected_validation_text(payload: Dict[str, Any]) -> Any:
    """Oracle: first rule broken following the order of Req 4.7, or None if valid."""
    for field in _ID_FIELDS:
        value = payload[field]
        if not _is_valid_integer(value) or value < 1:
            return f'{field} must be an integer greater than or equal to 1'
    for field in ('image_name', 'image_id'):
        value = payload[field]
        if not isinstance(value, str) or len(value.strip()) > 255:
            return f'{field} {_STRING_MSG}'
    n_variations = payload['n_variations']
    if not _is_valid_integer(n_variations) or not 1 <= n_variations <= 10:
        return 'n_variations must be an integer between 1 and 10'
    prompt = payload.get('custom_prompt')
    if prompt is not None and (not isinstance(prompt, str) or len(prompt.strip()) > 2000):
        return _PROMPT_MSG
    option = payload.get('expand_zoom_option')
    if option is not None and not (isinstance(option, str) and option in _EXPAND_ZOOM_OPTIONS):
        return _ZOOM_MSG
    if (prompt is None or not prompt.strip()) and option is None:
        return _REQUIRES_ONE_MSG
    return None


# Feature: edit-ad-variant-image-use-case, Property 3: Los valores inválidos se rechazan en orden y sin acceder a datos
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(neither=st.booleans(), data=st.data())
def test_property_invalid_values_rejected_in_order(
        collaborators, neither: bool, data: st.DataObject) -> None:
    """**Validates: Requirements 3.3, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8**"""
    for mock in (collaborators.account, collaborators.campaign, collaborators.ad_channel,
                 collaborators.fury, collaborators.logger):
        mock.reset_mock()

    overrides: Dict[str, Any] = {}
    candidates = _VALIDATION_ORDER
    if neither:
        # Neither a normalized prompt nor an option: the combined rule (Req 4.6) applies
        # unless an earlier field is invalid.
        overrides['custom_prompt'] = data.draw(
            st.one_of(st.just(MISSING), st.none(), _WHITESPACE), label='custom_prompt')
        overrides['expand_zoom_option'] = data.draw(
            st.sampled_from((MISSING, None)), label='expand_zoom_option')
        candidates = _VALIDATION_ORDER[:-2]
        invalid_fields = data.draw(st.sets(st.sampled_from(candidates)), label='invalid')
    else:
        invalid_fields = data.draw(
            st.sets(st.sampled_from(candidates), min_size=1), label='invalid')
    for field in invalid_fields:
        overrides[field] = data.draw(_INVALID_VALUE_STRATEGIES[field], label=f'value {field}')
    payload = _payload(**overrides)

    expected_text = _expected_validation_text(payload)
    assert expected_text is not None

    with pytest.raises(IncorrectValidationException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(payload)

    assert type(excinfo.value) is IncorrectValidationException
    assert excinfo.value.code == 'SYSVAL001'
    assert excinfo.value.text == expected_text
    for method in (collaborators.account.return_value.get_by_email,
                   collaborators.campaign.return_value.get_by_id_brand_and_account,
                   collaborators.ad_channel.return_value.get_by_id_ad_campaign_and_channel,
                   collaborators.fury.return_value.post):
        method.assert_not_called()
    for cls in (collaborators.account, collaborators.campaign,
                collaborators.ad_channel, collaborators.fury):
        assert cls.return_value.method_calls == []


# --- Requirements 5, 6, 7: account, campaign and variant lookups (Req 10.9, 10.10) ---

def _lookup(collaborators: SimpleNamespace, step: str) -> Any:
    return {
        'account': collaborators.account.return_value.get_by_email,
        'campaign': collaborators.campaign.return_value.get_by_id_brand_and_account,
        'variant': collaborators.ad_channel.return_value.get_by_id_ad_campaign_and_channel,
    }[step]


_LOOKUP_NOT_FOUND = (
    ('account', 'Account not found'),
    ('campaign', 'Campaign not found or does not belong to account'),
    ('variant', 'Ad variant not found'),
)


@pytest.mark.parametrize('empty_result', [None, {}], ids=['none', 'empty-dict'])
@pytest.mark.parametrize('step, expected_text', _LOOKUP_NOT_FOUND, ids=[s for s, _ in _LOOKUP_NOT_FOUND])
def test_lookup_without_result_raises_data_not_found(collaborators, step: str, expected_text: str,
                                                     empty_result: Any) -> None:
    _lookup(collaborators, step).return_value = empty_result

    with pytest.raises(DataNotFoundException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert type(excinfo.value) is DataNotFoundException
    assert excinfo.value.code == 'DAT001'
    assert excinfo.value.text == expected_text
    _lookup(collaborators, step).assert_called_once()
    _assert_not_called_after(step, collaborators)


@pytest.mark.parametrize('step', ['account', 'campaign', 'variant'])
def test_lookup_exception_propagates_same_instance(collaborators, step: str) -> None:
    original = StrapiException(f'Strapi failure in {step} lookup')
    _lookup(collaborators, step).side_effect = original

    with pytest.raises(StrapiException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert excinfo.value is original
    _assert_not_called_after(step, collaborators)


def test_variant_lookup_receives_payload_ids(collaborators) -> None:
    EditAdVariantImageUseCase(USER_ID).execute(_payload())

    collaborators.campaign.return_value.get_by_id_brand_and_account.assert_called_once_with(10, 1, 7)
    collaborators.ad_channel.return_value.get_by_id_ad_campaign_and_channel.assert_called_once_with(
        50, 20, 10, 30)


# --- Requirement 8: banner image lookup ---------------------------------------

def _image_not_found_cases() -> list:
    return [
        pytest.param({'image_id': 'img-abc'}, {'id': 50, 'attributes': {'media_images_banner': []}},
                     id='empty-list'),
        pytest.param({'image_id': 'img-abc'}, {'id': 50, 'attributes': {}}, id='absent'),
        pytest.param({'image_id': 'img-abc'},
                     {'id': 50, 'attributes': {'media_images_banner': None}}, id='none'),
        pytest.param({'image_id': 'img-abc'},
                     {'id': 50, 'attributes': {'media_images_banner': 'x'}}, id='str'),
        pytest.param({'image_id': 'img-abc'},
                     {'id': 50, 'attributes': {'media_images_banner': [
                         {'name': 'banner-1', 'image_id': 'img-other'}, {'name': 'banner-2'}]}},
                     id='no-match'),
        pytest.param({'image_id': '5'},
                     {'id': 50, 'attributes': {'media_images_banner': [
                         {'name': 'banner-1', 'image_id': 5}]}},
                     id='int-vs-str'),
        pytest.param({'image_id': 'img-abc'}, {'id': 50, 'attributes': None}, id='attributes-none'),
        pytest.param({'image_id': 'img-abc'},
                     {'id': 50, 'attributes': {'media_images_banner': [
                         None, 5, 'img-abc', ['img-abc']]}},
                     id='non-dict-items'),
    ]


@pytest.mark.parametrize('overrides, ad_variant', _image_not_found_cases())
def test_image_not_in_banners_raises_data_not_found(collaborators, overrides: Dict[str, Any],
                                                    ad_variant: Dict[str, Any]) -> None:
    collaborators.ad_channel.return_value.get_by_id_ad_campaign_and_channel.return_value = ad_variant

    # Any KeyError/TypeError would escape pytest.raises and fail the test.
    with pytest.raises(DataNotFoundException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload(**overrides))

    assert type(excinfo.value) is DataNotFoundException
    assert excinfo.value.code == 'DAT001'
    assert excinfo.value.text == 'Image not found in ad variant'
    _assert_not_called_after('variant', collaborators)


# --- Requirement 5.3: parent account resolution (Req 10.11) ---------------------

@pytest.mark.parametrize('parent_data, expected_account_id', [({'id': 99}, 99), (None, 7)],
                         ids=['parent-99', 'fallback-7'])
def test_campaign_lookup_uses_parent_account_id(collaborators, parent_data: Any,
                                                expected_account_id: int) -> None:
    collaborators.account.return_value.get_by_email.return_value = {
        'id': 7, 'attributes': {'parent_account': {'data': parent_data}}}

    result = EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert result == {'job_id': 'job-1'}
    collaborators.campaign.return_value.get_by_id_brand_and_account.assert_called_once_with(
        10, 1, expected_account_id)


# --- Property 4: tolerant Parent_Account resolution (Req 5.3) ------------------
# Each nesting level is generated as a (shape, value) pair so the oracle is
# derived from the generated shape, not from re-running isinstance checks.
_non_dict_values = st.one_of(st.integers(), st.text(max_size=5), st.booleans(),
                             st.lists(st.integers(), max_size=3), st.floats(allow_nan=False))
_filler_key = st.sampled_from(['name', 'email', 'extra'])
_ids_any = st.one_of(st.integers(), st.text(max_size=5), st.none())


def _level(child_key: str, child: st.SearchStrategy) -> st.SearchStrategy:
    """Shapes for a dict level: absent, None, non-dict, {}, or non-empty dict holding the child."""

    def _non_empty(pair: Any) -> Any:
        child_shape, child_value = pair
        if child_shape == 'absent':
            # Non-empty dict without child_key: needs a filler key.
            return _filler_key.map(lambda k: ('valid_without_child', child_shape, {k: 'x'}))
        return st.just(('valid', child_shape, {child_key: child_value}))

    return st.one_of(
        st.just(('absent', None, MISSING)),
        st.just(('none', None, None)),
        _non_dict_values.map(lambda v: ('non_dict', None, v)),
        st.just(('empty', None, {})),
        child.flatmap(_non_empty),
    )


# data level: absent, None, non-dict, {}, non-empty without id, or with id.
_data_level = st.one_of(
    st.just(('absent', MISSING)),
    st.just(('none', None)),
    _non_dict_values.map(lambda v: ('non_dict', v)),
    st.just(('empty', {})),
    _filler_key.map(lambda k: ('no_id', {k: 'x'})),
    _ids_any.map(lambda i: ('with_id', {'id': i})),
)


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(account_id=st.integers(), data=st.data())
def test_property_parent_account_resolution(account_id: int, data: st.DataObject) -> None:
    """Parent_Account is data.id only when every level is a non-empty dict and data has id.

    **Validates: Requirements 5.3**
    """
    # Feature: edit-ad-variant-image-use-case, Property 4: Resolución tolerante de la Parent_Account
    data_shape, data_value = data.draw(_data_level, label='data')
    parent_shape, _, parent_value = data.draw(
        _level('data', st.just((data_shape, data_value))), label='parent_account')
    attrs_shape, _, attrs_value = data.draw(
        _level('parent_account', st.just((parent_shape, parent_value))), label='attributes')

    account: Dict[str, Any] = {'id': account_id}
    if attrs_value is not MISSING:
        account['attributes'] = attrs_value

    # Oracle (Req 5.3): parent id only if attributes, parent_account and data are
    # non-empty dicts actually present along the path, and data contains 'id'.
    if attrs_shape == 'valid' and parent_shape == 'valid' and data_shape == 'with_id':
        expected = data_value['id']
    else:
        expected = account_id

    # Any KeyError/TypeError raised here fails the property.
    assert _edit_image_parent_account_id(account) == expected


# --- Property 5: banner image lookup equivalent to the oracle (Req 8.1-8.3) ---
_image_id_values = st.one_of(st.text(max_size=5), st.integers(min_value=-3, max_value=3))
_banner_items = st.one_of(
    st.fixed_dictionaries({'image_id': _image_id_values}, optional={'url': st.text(max_size=5)}),
    st.dictionaries(_filler_key, st.text(max_size=5), max_size=2),
    st.integers(),
    st.text(max_size=5),
    st.none(),
)
_non_list_values = st.one_of(st.integers(), st.text(max_size=5), st.booleans(),
                             st.floats(allow_nan=False), st.dictionaries(_filler_key, st.integers(), max_size=2))


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(items=st.lists(_banner_items, max_size=6), data=st.data())
def test_property_banner_image_lookup_matches_oracle(items: list, data: st.DataObject) -> None:
    """Lookup is True iff some dict item has an 'image_id' exactly == image_id.

    **Validates: Requirements 8.1, 8.2, 8.3**
    """
    # Feature: edit-ad-variant-image-use-case, Property 5: Búsqueda de imagen equivalente al oráculo
    banner_shape, banner_value = data.draw(st.one_of(
        st.just(('absent', MISSING)),
        st.just(('none', None)),
        _non_list_values.map(lambda v: ('non_list', v)),
        st.just(('list', items)),
    ), label='media_images_banner')
    attrs_shape, attrs_value = data.draw(st.one_of(
        st.just(('absent', MISSING)),
        st.just(('none', None)),
        _non_dict_values.map(lambda v: ('non_dict', v)),
        st.just(('dict', {} if banner_value is MISSING else {'media_images_banner': banner_value})),
    ), label='attributes')
    variant_is_dict = data.draw(st.booleans(), label='variant_is_dict')
    if variant_is_dict:
        ad_variant: Any = {'id': 50}
        if attrs_value is not MISSING:
            ad_variant['attributes'] = attrs_value
    else:
        ad_variant = data.draw(_non_dict_values, label='ad_variant')

    # Take image_id from an existing item sometimes to force matches.
    existing_ids = [it['image_id'] for it in items if isinstance(it, dict) and 'image_id' in it]
    candidates = [_image_id_values] + ([st.sampled_from(existing_ids)] if existing_ids else [])
    image_id = data.draw(st.one_of(*candidates), label='image_id')

    # Oracle (Req 8.1-8.3): only a list reached through dict variant/attributes counts;
    # non-dict items and items without image_id are skipped; exact == comparison.
    reachable = variant_is_dict and attrs_shape == 'dict' and banner_shape == 'list'
    expected = False
    if reachable:
        for item in items:
            if type(item) is dict and 'image_id' in item and item['image_id'] == image_id:
                expected = True
                break

    # Any KeyError/TypeError raised here fails the property.
    assert _edit_image_has_banner_image(ad_variant, image_id) is expected


# --- Requirement 9: Fury enqueue errors (Req 10.12) ----------------------------

_NO_JOB_ID_MSG = 'Fury response does not contain edit_job_id'
_FURY_ENQUEUE_MSG = 'Failed to enqueue image edit job in Fury'


def test_fury_exception_from_post_propagates_same_instance(collaborators) -> None:
    original = FuryException('Failed to POST /api/v2/variants/image/edit')
    collaborators.fury.return_value.post.side_effect = original

    with pytest.raises(FuryException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert excinfo.value is original


def test_non_sinergia_error_from_post_raises_fury_exception(collaborators) -> None:
    collaborators.fury.return_value.post.side_effect = RuntimeError()

    with pytest.raises(FuryException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert type(excinfo.value) is FuryException
    assert excinfo.value.code == 'FURY001'
    assert excinfo.value.text == _FURY_ENQUEUE_MSG


@pytest.mark.parametrize('response', [
    None, [], {}, {'data': {}}, {'data': {'edit_job_id': None}},
    {'data': {'edit_job_id': 123}}, {'data': {'edit_job_id': '   '}},
], ids=['none', 'list', 'empty-dict', 'empty-data', 'job-none', 'job-int', 'job-blank'])
def test_fury_response_without_job_id_raises_fury_exception(collaborators, response: Any) -> None:
    collaborators.fury.return_value.post.return_value = response

    with pytest.raises(FuryException) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert type(excinfo.value) is FuryException
    assert excinfo.value.code == 'FURY001'
    assert excinfo.value.text == _NO_JOB_ID_MSG


def test_fury_job_id_is_returned_unstripped(collaborators) -> None:
    collaborators.fury.return_value.post.return_value = {'data': {'edit_job_id': ' abc '}}

    result = EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert result == {'job_id': ' abc '}


# --- Requirement 2.4 / 9.8: logging (Req 10.15) --------------------------------

def _break_presence(c: SimpleNamespace) -> Dict[str, Any]:
    return _payload(brand_id=None)


def _break_value(c: SimpleNamespace) -> Dict[str, Any]:
    return _payload(brand_id=0)


def _break_lookup(step: str):
    def _apply(c: SimpleNamespace) -> Dict[str, Any]:
        _lookup(c, step).return_value = None
        return _payload()
    return _apply


def _break_image(c: SimpleNamespace) -> Dict[str, Any]:
    return _payload(image_id='img-missing')


def _break_fury_non_sinergia(c: SimpleNamespace) -> Dict[str, Any]:
    c.fury.return_value.post.side_effect = RuntimeError('boom')
    return _payload()


def _break_fury_response(c: SimpleNamespace) -> Dict[str, Any]:
    c.fury.return_value.post.return_value = {'data': {}}
    return _payload()


_OWN_ERROR_PATHS = [
    pytest.param(_break_presence, ParametersNotFoundException, id='presence'),
    pytest.param(_break_value, IncorrectValidationException, id='value'),
    pytest.param(_break_lookup('account'), DataNotFoundException, id='account'),
    pytest.param(_break_lookup('campaign'), DataNotFoundException, id='campaign'),
    pytest.param(_break_lookup('variant'), DataNotFoundException, id='variant'),
    pytest.param(_break_image, DataNotFoundException, id='image'),
    pytest.param(_break_fury_non_sinergia, FuryException, id='fury-non-sinergia'),
    pytest.param(_break_fury_response, FuryException, id='fury-no-job-id'),
]


@pytest.mark.parametrize('break_path, exc_type', _OWN_ERROR_PATHS)
def test_own_errors_are_logged_once_before_raising(collaborators, break_path: Any,
                                                   exc_type: type) -> None:
    payload = break_path(collaborators)

    with pytest.raises(exc_type) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(payload)

    assert collaborators.logger.error.call_count == 1
    call = collaborators.logger.error.call_args
    logged = ' '.join(str(arg) for arg in list(call.args) + list(call.kwargs.values()))
    assert excinfo.value.text in logged


def _propagate_lookup(step: str):
    def _apply(c: SimpleNamespace) -> Any:
        original = StrapiException(f'Strapi failure in {step} lookup')
        _lookup(c, step).side_effect = original
        return original
    return _apply


def _propagate_fury(c: SimpleNamespace) -> Any:
    original = FuryException('Failed to POST /api/v2/variants/image/edit')
    c.fury.return_value.post.side_effect = original
    return original


@pytest.mark.parametrize('arrange', [
    pytest.param(_propagate_lookup('account'), id='account'),
    pytest.param(_propagate_lookup('campaign'), id='campaign'),
    pytest.param(_propagate_lookup('variant'), id='variant'),
    pytest.param(_propagate_fury, id='fury'),
])
def test_propagated_errors_are_not_logged(collaborators, arrange: Any) -> None:
    original = arrange(collaborators)

    with pytest.raises(type(original)) as excinfo:
        EditAdVariantImageUseCase(USER_ID).execute(_payload())

    assert excinfo.value is original
    collaborators.logger.error.assert_not_called()


def test_happy_path_logs_info_without_prompt_text(collaborators) -> None:
    prompt = 'Reemplaza el fondo por una playa al atardecer'
    assert len(prompt) >= 20

    result = EditAdVariantImageUseCase(USER_ID).execute(_payload(custom_prompt=prompt))

    assert result == {'job_id': 'job-1'}
    assert collaborators.logger.info.call_count == 1
    call = collaborators.logger.info.call_args
    for arg in list(call.args) + list(call.kwargs.values()):
        assert prompt not in str(arg)


# --- Property 6: edit_job_id extraction equivalent to the oracle (Req 9.4, 9.7) ---
# Responses are generated as (shape, response) pairs so the oracle relies on the
# generated shape instead of re-running the implementation's isinstance checks.
_job_id_values = st.one_of(st.none(), st.integers(), st.text(),
                           st.text(alphabet=' \t\n\r', max_size=4))
_fury_responses = st.one_of(
    _non_dict_values.map(lambda v: ('non_dict', v)),
    st.none().map(lambda v: ('non_dict', v)),
    st.dictionaries(_filler_key, st.integers(), max_size=2).map(lambda d: ('no_data', d)),
    _non_dict_values.map(lambda v: ('data_non_dict', {'ok': 1, 'data': v})),
    st.none().map(lambda v: ('data_non_dict', {'ok': 1, 'data': v})),
    st.dictionaries(_filler_key, st.integers(), max_size=2).map(
        lambda d: ('no_job_id', {'ok': 1, 'data': d})),
    _job_id_values.map(lambda j: ('with_job_id', {'ok': 1, 'data': {'edit_job_id': j,
                                                                     'status': 'RUNNING'}})),
)


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(case=_fury_responses)
def test_property_extract_job_id_matches_oracle(collaborators, case: Any) -> None:
    """edit_job_id is returned unchanged iff it is a non-blank str; otherwise FURY001.

    **Validates: Requirements 9.4, 9.7**
    """
    # Feature: edit-ad-variant-image-use-case, Property 6: Extracción del edit_job_id equivalente al oráculo
    collaborators.logger.reset_mock()
    shape, response = case

    # Oracle (Req 9.4, 9.7): only a str edit_job_id with content is valid.
    job_id = response['data']['edit_job_id'] if shape == 'with_job_id' else None
    is_valid = shape == 'with_job_id' and type(job_id) is str and job_id.strip() != ''

    if is_valid:
        result = _edit_image_extract_job_id(response)
        assert result is job_id
        collaborators.logger.error.assert_not_called()
    else:
        with pytest.raises(FuryException) as excinfo:
            _edit_image_extract_job_id(response)
        assert type(excinfo.value) is FuryException
        assert excinfo.value.code == 'FURY001'
        assert excinfo.value.text == _NO_JOB_ID_MSG
        assert collaborators.logger.error.call_count == 1
