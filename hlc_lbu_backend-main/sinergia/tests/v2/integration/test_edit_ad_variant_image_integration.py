"""Integration tests for the HilucaResourceAdChannelMediaImageEdit endpoint.

Exercises POST /api/v2/application/hiluca/brand/campaign/ad/channel/media/image/edit
through the Flask test client with the real v2 blueprint (routing, jwt_required,
check_access and errorhandlers). EditAdVariantImageUseCase is patched where the
resource module looks it up, so no request reaches Strapi, Redis or Fury.
The JWT is signed with a test-only secret; the Redis-backed credential cache
(checkCredentials) and the permissions lookup are replaced by in-memory stubs.

Validates: Requirements 1.3, 1.5, 1.6, 1.7
"""
import json

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

# app.v2 must be imported first: importing app.tools.permissions directly
# triggers a circular import through app.v1.
from app.v2 import v2_blueprint
import app.tools.permissions as permissions
from app import jwt
from app.exceptions.base import IncorrectValidationException
from app.v1.models.constant import ROLE_HILUCA_ADMIN, SUFFIX_PERMISSION
from app.v1.resources.base import ProxySecureResource

EDIT_PATH = '/api/v2/application/hiluca/brand/campaign/ad/channel/media/image/edit'
TEST_USERNAME = 'test@example.com'

PAYLOAD = {
    'brand_id': 1,
    'campaign_id': 2,
    'ad_id': 3,
    'channel_id': 4,
    'variant_id': 5,
    'image_name': 'hero.png',
    'image_id': 'img-abc',
    'n_variations': 2,
    'custom_prompt': 'make the sky blue',
    'expand_zoom_option': 'ZOOM_2X',
}


class _FakeRedis:
    """In-memory stand-in for the permissions lookup done by check_access."""

    def __init__(self, store):
        self._store = store

    def get(self, key):
        return self._store.get(key)


@pytest.fixture(scope='module')
def flask_app() -> Flask:
    # Minimal app: only the v2 blueprint plus JWT, without DB/Redis/Mongo/Celery init.
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['JWT_SECRET_KEY'] = 'test-only-jwt-secret'
    jwt.init_app(test_app)
    test_app.register_blueprint(v2_blueprint, url_prefix='/api/v2')
    return test_app


@pytest.fixture
def client(flask_app, monkeypatch):
    # checkCredentials normally reads the session from Redis by token jti.
    monkeypatch.setattr(
        ProxySecureResource,
        'checkCredentials',
        lambda self: {'username': TEST_USERNAME, 'person_extension_id': 1},
    )
    # Permissions granted to the test user (role HiLuca admin).
    granted = json.dumps([{'rol_long_name': ROLE_HILUCA_ADMIN, 'function_name': '', 'actions': []}])
    monkeypatch.setattr(
        permissions, 'redis_client', _FakeRedis({f'{TEST_USERNAME}{SUFFIX_PERMISSION}': granted})
    )
    return flask_app.test_client()


@pytest.fixture
def auth_headers(flask_app):
    with flask_app.app_context():
        token = create_access_token(identity=TEST_USERNAME)
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def use_case_cls(mocker):
    return mocker.patch('app.v2.resources.ad.EditAdVariantImageUseCase')


def test_missing_jwt_is_rejected_without_instantiating_use_case(client, use_case_cls) -> None:
    response = client.post(EDIT_PATH, json=PAYLOAD)

    assert response.status_code == 401
    assert response.get_json()['ok'] == 0
    use_case_cls.assert_not_called()
    use_case_cls.return_value.execute.assert_not_called()


def test_success_returns_200_with_job_id(client, auth_headers, use_case_cls) -> None:
    use_case_cls.return_value.execute.return_value = {'job_id': 'job-123'}

    response = client.post(EDIT_PATH, json=PAYLOAD, headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {'ok': 1, 'data': {'job_id': 'job-123'}}
    use_case_cls.assert_called_once_with(TEST_USERNAME)
    use_case_cls.return_value.execute.assert_called_once_with(PAYLOAD)


def test_validation_error_returns_400_with_sysval001(client, auth_headers, use_case_cls) -> None:
    use_case_cls.return_value.execute.side_effect = IncorrectValidationException('n_variations is invalid')

    response = client.post(EDIT_PATH, json=PAYLOAD, headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json() == {
        'ok': 0,
        'message': {'code': 'SYSVAL001', 'text': 'n_variations is invalid'},
    }
    use_case_cls.return_value.execute.assert_called_once_with(PAYLOAD)
