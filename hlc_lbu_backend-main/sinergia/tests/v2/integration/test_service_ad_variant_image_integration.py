"""Integration tests for the ServiceAdVariantImage endpoint.

Exercises GET /api/v2/service/hiluca/brand/.../variant/<id>/image/<id> through
the Flask test client with the real v2 blueprint (routing, Service_Auth and
errorhandlers). GetAdVariantImageUseCase is mocked, so no request reaches
Strapi or Image_Library. The service key is a test-only value injected into
the config read by Service_Auth; no real secret is used.

Validates: Requirements 1.3, 1.4, 1.5, 1.6, 1.7
"""
from types import SimpleNamespace

import pytest
from flask import Flask

import app.tools.service_auth as service_auth
from app.exceptions.base import DataNotFoundException
from app.v2 import v2_blueprint

TEST_SERVICE_KEY = 'test-service-key'
BASE_PATH = '/api/v2/service/hiluca/brand/1/campaign/2/ad/3/channel/4/variant/5/image/img-abc'


@pytest.fixture(scope='module')
def flask_app() -> Flask:
    # Minimal app: only the v2 blueprint, without DB/Redis/Mongo/Celery init.
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.register_blueprint(v2_blueprint, url_prefix='/api/v2')
    return test_app


@pytest.fixture
def client(flask_app, monkeypatch):
    # Inject a test-only service key into the config that Service_Auth reads.
    monkeypatch.setattr(
        service_auth,
        'config',
        {service_auth.config_type: SimpleNamespace(FURY_SERVICE_API_KEY=TEST_SERVICE_KEY)},
    )
    return flask_app.test_client()


@pytest.fixture
def use_case_cls(mocker):
    return mocker.patch('app.v2.resources.service.GetAdVariantImageUseCase')


def test_missing_header_is_rejected_without_calling_use_case(client, use_case_cls) -> None:
    response = client.get(BASE_PATH)

    assert response.status_code == 401
    assert response.get_json() == {
        'ok': False,
        'message': {'code': 'ESVC002', 'text': 'Unauthorized service call'},
    }
    use_case_cls.assert_not_called()
    use_case_cls.return_value.execute.assert_not_called()


def test_wrong_key_is_rejected_without_calling_use_case(client, use_case_cls) -> None:
    response = client.get(BASE_PATH, headers={'X-Service-API-Key': 'wrong-key'})

    assert response.status_code == 401
    assert response.get_json()['message']['code'] == 'ESVC002'
    use_case_cls.assert_not_called()


def test_negative_segment_returns_404_without_calling_use_case(client, use_case_cls) -> None:
    path = '/api/v2/service/hiluca/brand/1/campaign/2/ad/3/channel/4/variant/-1/image/img-abc'

    response = client.get(path, headers={'X-Service-API-Key': TEST_SERVICE_KEY})

    assert response.status_code == 404
    assert response.get_json()['message']['code'] == 'E404'
    use_case_cls.assert_not_called()


def test_success_returns_200_with_success_envelope(client, use_case_cls) -> None:
    data = {'id': 'img-abc', 'url': 'https://img.example/x.png', 'prompt': 'a red car'}
    use_case_cls.return_value.execute.return_value = data

    response = client.get(BASE_PATH, headers={'X-Service-API-Key': TEST_SERVICE_KEY})

    assert response.status_code == 200
    assert response.get_json() == {'ok': True, 'data': data}
    use_case_cls.assert_called_once_with()
    use_case_cls.return_value.execute.assert_called_once_with(1, 2, 3, 4, 5, 'img-abc')


def test_data_not_found_returns_400_with_error_envelope(client, use_case_cls) -> None:
    use_case_cls.return_value.execute.side_effect = DataNotFoundException('Ad variant not found')

    response = client.get(BASE_PATH, headers={'X-Service-API-Key': TEST_SERVICE_KEY})

    assert response.status_code == 400
    assert response.get_json() == {
        'ok': 0,
        'message': {'code': 'DAT001', 'text': 'Ad variant not found'},
    }
    use_case_cls.return_value.execute.assert_called_once_with(1, 2, 3, 4, 5, 'img-abc')
