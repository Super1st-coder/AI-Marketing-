"""
Tests para webhook-router.

Adaptados de reference/tests/test_webhook_handler.py y expandidos
para cubrir la lógica específica del router de HiLuca.

Corre con:
    cd webhooks/router
    pip install -r requirements-test.txt
    pytest tests/ -v

Cobertura:
    - verifiers.py  → SignatureVerifiers (hmac_sha256, sha512, stripe, none)
    - registry.py   → SERVICE_REGISTRY lookup
    - main.py       → _parse_path, _generate_idempotency_key, webhook_router endpoint
"""

import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import MagicMock, patch

import pytest

# ── Setup: asegurarse de que el path incluye el directorio del router
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verifiers import (
    verify_hmac_sha256,
    verify_hmac_sha512,
    verify_stripe,
    verify_none,
    get_verifier,
    VERIFIERS,
)
from registry import get_service_config, list_services, SERVICE_REGISTRY
from main import _parse_path, _generate_idempotency_key


# ══════════════════════════════════════════════════════════════════════════════
# VERIFIERS
# ══════════════════════════════════════════════════════════════════════════════

class TestVerifyHmacSha256:
    """Adaptado de TestSignatureVerifier del reference."""

    SECRET = "test_secret_hiluca_123"
    PAYLOAD = b'{"appsflyer_id": "af-001", "event_name": "install"}'

    def test_valid_signature(self):
        sig = hmac.new(self.SECRET.encode(), self.PAYLOAD, hashlib.sha256).hexdigest()
        assert verify_hmac_sha256(self.PAYLOAD, sig, self.SECRET) is True

    def test_invalid_signature(self):
        assert verify_hmac_sha256(self.PAYLOAD, "firma_invalida", self.SECRET) is False

    def test_tampered_payload(self):
        """Firma del payload original NO valida el payload modificado."""
        original = b'{"amount": 100}'
        tampered = b'{"amount": 99999}'
        sig = hmac.new(self.SECRET.encode(), original, hashlib.sha256).hexdigest()
        assert verify_hmac_sha256(tampered, sig, self.SECRET) is False

    def test_empty_secret_rejected(self):
        """Secret vacío siempre rechaza (previene misconfiguraciones)."""
        sig = hmac.new(self.SECRET.encode(), self.PAYLOAD, hashlib.sha256).hexdigest()
        assert verify_hmac_sha256(self.PAYLOAD, sig, "") is False

    def test_meta_sha256_prefix(self):
        """Meta envía 'sha256=<hex>' — el verifier debe quitarlo."""
        sig_raw = hmac.new(self.SECRET.encode(), self.PAYLOAD, hashlib.sha256).hexdigest()
        sig_with_prefix = f"sha256={sig_raw}"
        assert verify_hmac_sha256(self.PAYLOAD, sig_with_prefix, self.SECRET) is True

    def test_whitespace_in_signature(self):
        """Espacios extra en la firma no deben romper la verificación."""
        sig = hmac.new(self.SECRET.encode(), self.PAYLOAD, hashlib.sha256).hexdigest()
        assert verify_hmac_sha256(self.PAYLOAD, f"  {sig}  ", self.SECRET) is True


class TestVerifyHmacSha512:

    SECRET = "test_secret_512"
    PAYLOAD = b'{"event": "transfer.completed"}'

    def test_valid_signature(self):
        sig = hmac.new(self.SECRET.encode(), self.PAYLOAD, hashlib.sha512).hexdigest()
        assert verify_hmac_sha512(self.PAYLOAD, sig, self.SECRET) is True

    def test_invalid_signature(self):
        assert verify_hmac_sha512(self.PAYLOAD, "bad_sig", self.SECRET) is False

    def test_empty_secret_rejected(self):
        sig = hmac.new(self.SECRET.encode(), self.PAYLOAD, hashlib.sha512).hexdigest()
        assert verify_hmac_sha512(self.PAYLOAD, sig, "") is False


class TestVerifyStripe:
    """Adaptado de TestSignatureVerifier.test_stripe_* del reference."""

    SECRET = "whsec_test_hiluca"
    PAYLOAD = b'{"type": "payment_intent.succeeded", "id": "pi_001"}'

    def _make_stripe_header(self, payload: bytes, secret: str, timestamp: int = None) -> str:
        ts = timestamp or int(time.time())
        signed = f"{ts}.{payload.decode()}"
        sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_valid_stripe_signature(self):
        header = self._make_stripe_header(self.PAYLOAD, self.SECRET)
        assert verify_stripe(self.PAYLOAD, header, self.SECRET) is True

    def test_expired_timestamp_rejected(self):
        """Timestamps > 5 min en el pasado deben rechazarse (anti-replay)."""
        old_ts = int(time.time()) - 600  # 10 minutos atrás
        header = self._make_stripe_header(self.PAYLOAD, self.SECRET, timestamp=old_ts)
        assert verify_stripe(self.PAYLOAD, header, self.SECRET) is False

    def test_future_timestamp_rejected(self):
        """Timestamps muy en el futuro también deben rechazarse."""
        future_ts = int(time.time()) + 600
        header = self._make_stripe_header(self.PAYLOAD, self.SECRET, timestamp=future_ts)
        assert verify_stripe(self.PAYLOAD, header, self.SECRET) is False

    def test_wrong_secret(self):
        header = self._make_stripe_header(self.PAYLOAD, self.SECRET)
        assert verify_stripe(self.PAYLOAD, header, "wrong_secret") is False

    def test_malformed_header(self):
        """Header mal formado no debe causar excepción."""
        assert verify_stripe(self.PAYLOAD, "not_a_valid_stripe_header", self.SECRET) is False

    def test_empty_secret_rejected(self):
        header = self._make_stripe_header(self.PAYLOAD, self.SECRET)
        assert verify_stripe(self.PAYLOAD, header, "") is False


class TestVerifyNone:
    """verify_none siempre True — solo para entorno dev."""

    def test_always_true(self):
        assert verify_none(b"cualquier_cosa", "cualquier_firma", "cualquier_secret") is True

    def test_empty_payload(self):
        assert verify_none(b"", "", "") is True


class TestGetVerifier:

    def test_returns_correct_verifier(self):
        assert get_verifier("hmac_sha256") is verify_hmac_sha256
        assert get_verifier("hmac_sha512") is verify_hmac_sha512
        assert get_verifier("stripe") is verify_stripe
        assert get_verifier("none") is verify_none

    def test_unknown_verifier_raises(self):
        with pytest.raises(ValueError, match="Verifier desconocido"):
            get_verifier("md5_inseguro")

    def test_all_registry_types_exist(self):
        """Todos los verifier_type usados en SERVICE_REGISTRY deben existir en VERIFIERS."""
        for servicio, versions in SERVICE_REGISTRY.items():
            for version, config in versions.items():
                verifier_type = config["verifier"]
                assert verifier_type in VERIFIERS, (
                    f"{servicio}@{version} usa verifier '{verifier_type}' "
                    f"que no está en VERIFIERS"
                )


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

class TestRegistry:

    def test_appsflyer_v1_exists(self):
        config = get_service_config("appsflyer", "v1.0.0")
        assert config is not None

    def test_appsflyer_config_has_required_keys(self):
        config = get_service_config("appsflyer", "v1.0.0")
        required_keys = ["verifier", "secret_name", "signature_header", "topic_pattern"]
        for key in required_keys:
            assert key in config, f"Falta campo requerido: '{key}' en appsflyer@v1.0.0"

    def test_unknown_service_returns_none(self):
        assert get_service_config("servicio_fantasma", "v1.0.0") is None

    def test_known_service_unknown_version_returns_none(self):
        assert get_service_config("appsflyer", "v99.0.0") is None

    def test_list_services_returns_registered(self):
        services = list_services()
        assert len(services) > 0
        slugs = [s["servicio"] for s in services]
        assert "appsflyer" in slugs

    def test_topic_pattern_is_valid_format(self):
        """El topic_pattern debe poder formatearse con {entorno}."""
        config = get_service_config("appsflyer", "v1.0.0")
        topic_dev = config["topic_pattern"].format(entorno="dev")
        topic_prd = config["topic_pattern"].format(entorno="prd")
        assert topic_dev == "wh-appsflyer-dev"
        assert topic_prd == "wh-appsflyer-prd"


# ══════════════════════════════════════════════════════════════════════════════
# PATH PARSING
# ══════════════════════════════════════════════════════════════════════════════

class TestParsePath:

    def test_full_path_with_entorno(self):
        servicio, version, entorno = _parse_path("/webhook/appsflyer/v1.0.0/prd")
        assert servicio == "appsflyer"
        assert version == "v1.0.0"
        assert entorno == "prd"

    def test_path_without_entorno_defaults_to_prd(self):
        _, _, entorno = _parse_path("/webhook/appsflyer/v1.0.0")
        assert entorno == "prd"

    def test_path_with_dev_entorno(self):
        _, _, entorno = _parse_path("/webhook/appsflyer/v1.0.0/dev")
        assert entorno == "dev"

    def test_servicio_normalized_to_lowercase(self):
        servicio, _, _ = _parse_path("/webhook/AppsFlyer/v1.0.0/prd")
        assert servicio == "appsflyer"

    def test_invalid_entorno_raises(self):
        with pytest.raises(ValueError, match="Entorno inválido"):
            _parse_path("/webhook/appsflyer/v1.0.0/staging")

    def test_missing_version_raises(self):
        with pytest.raises(ValueError, match="Path inválido"):
            _parse_path("/webhook/appsflyer")

    def test_wrong_root_raises(self):
        with pytest.raises(ValueError, match="Path inválido"):
            _parse_path("/api/appsflyer/v1.0.0")

    def test_trailing_slash_handled(self):
        servicio, version, entorno = _parse_path("/webhook/appsflyer/v1.0.0/prd/")
        assert servicio == "appsflyer"
        assert entorno == "prd"


# ══════════════════════════════════════════════════════════════════════════════
# IDEMPOTENCY KEY
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateIdempotencyKey:
    """Adaptado de TestIdempotencyChecker del reference."""

    def test_key_from_specific_field(self):
        """Cuando el payload tiene el campo configurado, lo usa como key."""
        payload = {"appsflyer_id": "af-unique-001", "event_name": "install"}
        key = _generate_idempotency_key(
            "appsflyer", "v1.0.0", "prd", payload, "appsflyer_id"
        )
        assert key == "appsflyer:v1.0.0:prd:af-unique-001"

    def test_key_from_nested_field(self):
        """Soporta notación 'padre.hijo' para campos anidados."""
        payload = {"data": {"id": "nested-123"}}
        key = _generate_idempotency_key(
            "meta", "v1.0.0", "prd", payload, "data.id"
        )
        assert key == "meta:v1.0.0:prd:nested-123"

    def test_fallback_to_hash_when_field_missing(self):
        """Si el campo no existe en el payload, usa hash del payload completo."""
        payload = {"event_name": "install", "platform": "android"}
        key = _generate_idempotency_key(
            "appsflyer", "v1.0.0", "prd", payload, "appsflyer_id"
        )
        assert key.startswith("appsflyer:v1.0.0:prd:hash:")

    def test_fallback_hash_when_no_field_configured(self):
        """idempotency_field=None siempre usa hash."""
        payload = {"amount": 100}
        key = _generate_idempotency_key(
            "generic", "v1.0.0", "dev", payload, None
        )
        assert key.startswith("generic:v1.0.0:dev:hash:")

    def test_same_payload_same_key(self):
        """Payload idéntico → misma key (propiedad determinista)."""
        payload = {"appsflyer_id": "af-001", "event_name": "purchase"}
        key1 = _generate_idempotency_key("appsflyer", "v1.0.0", "prd", payload, "appsflyer_id")
        key2 = _generate_idempotency_key("appsflyer", "v1.0.0", "prd", payload, "appsflyer_id")
        assert key1 == key2

    def test_different_payloads_different_keys(self):
        """Payloads distintos → keys distintas."""
        key1 = _generate_idempotency_key("appsflyer", "v1.0.0", "prd", {"appsflyer_id": "a"}, "appsflyer_id")
        key2 = _generate_idempotency_key("appsflyer", "v1.0.0", "prd", {"appsflyer_id": "b"}, "appsflyer_id")
        assert key1 != key2

    def test_different_entornos_different_keys(self):
        """Mismo evento en dev vs prd → keys distintas."""
        payload = {"appsflyer_id": "af-001"}
        key_dev = _generate_idempotency_key("appsflyer", "v1.0.0", "dev", payload, "appsflyer_id")
        key_prd = _generate_idempotency_key("appsflyer", "v1.0.0", "prd", payload, "appsflyer_id")
        assert key_dev != key_prd

    def test_hash_key_is_stable_across_dict_ordering(self):
        """El hash no debe depender del orden de las claves del dict."""
        payload_a = {"z": 1, "a": 2, "m": 3}
        payload_b = {"a": 2, "m": 3, "z": 1}
        key_a = _generate_idempotency_key("generic", "v1.0.0", "prd", payload_a, None)
        key_b = _generate_idempotency_key("generic", "v1.0.0", "prd", payload_b, None)
        assert key_a == key_b


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT — webhook_router (integración con mocks)
# ══════════════════════════════════════════════════════════════════════════════

class TestWebhookRouterEndpoint:
    """
    Tests de integración del endpoint webhook_router.
    Se mockean: Secret Manager, Pub/Sub publisher.
    """

    def _make_request(
        self,
        path: str,
        method: str = "POST",
        body: dict = None,
        headers: dict = None,
        query_params: dict = None,
    ) -> MagicMock:
        """Crea un mock de flask.Request para functions_framework."""
        request = MagicMock()
        request.path = path
        request.method = method

        body_bytes = json.dumps(body or {}).encode()
        request.get_data.return_value = body_bytes
        request.get_json.return_value = body or {}
        request.args = query_params or {}
        request.headers = {**(headers or {})}
        return request

    @patch("main._get_secret", return_value="mi_signing_secret")
    @patch("main._get_project_id", return_value="test-project")
    @patch("main._get_publisher")
    def test_dev_request_skips_signature(self, mock_publisher, mock_pid, mock_secret):
        """En entorno dev no debe verificar firma — siempre acepta."""
        from main import webhook_router

        mock_future = MagicMock()
        mock_future.result.return_value = "msg-dev-001"
        mock_publisher.return_value.publish.return_value = mock_future
        mock_publisher.return_value.topic_path.return_value = "projects/test-project/topics/wh-appsflyer-dev"

        request = self._make_request(
            path="/webhook/appsflyer/v1.0.0/dev",
            body={"appsflyer_id": "test-001", "event_name": "install"},
            # Sin header de firma — en dev debe funcionar igual
        )

        response_body, status, _ = webhook_router(request)
        result = json.loads(response_body)

        assert status == 200
        assert result["status"] == "ok"
        assert result["entorno"] == "dev"
        # Secret Manager NO debe llamarse en dev
        mock_secret.assert_not_called()

    @patch("main._get_secret", return_value="mi_signing_secret")
    @patch("main._get_project_id", return_value="test-project")
    @patch("main._get_publisher")
    def test_prd_valid_signature_accepted(self, mock_publisher, mock_pid, mock_secret):
        """En prd con firma válida debe retornar 200 y publicar en Pub/Sub."""
        from main import webhook_router

        mock_future = MagicMock()
        mock_future.result.return_value = "msg-prd-001"
        mock_publisher.return_value.publish.return_value = mock_future
        mock_publisher.return_value.topic_path.return_value = "projects/test-project/topics/wh-appsflyer-prd"

        payload = {"appsflyer_id": "af-prd-001", "event_name": "PAYMENT_SUCCESS"}
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
        secret = "mi_signing_secret"
        sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

        request = self._make_request(
            path="/webhook/appsflyer/v1.0.0/prd",
            body=payload,
            headers={"x-signature": sig},
        )
        request.get_data.return_value = payload_bytes

        response_body, status, _ = webhook_router(request)
        result = json.loads(response_body)

        assert status == 200
        assert result["status"] == "ok"
        assert result["entorno"] == "prd"
        assert "message_id" in result
        assert "idempotency_key" in result
        mock_publisher.return_value.publish.assert_called_once()

    @patch("main._get_secret", return_value="mi_signing_secret")
    @patch("main._get_project_id", return_value="test-project")
    def test_prd_invalid_signature_rejected(self, mock_pid, mock_secret):
        """En prd con firma inválida debe retornar 401."""
        from main import webhook_router

        request = self._make_request(
            path="/webhook/appsflyer/v1.0.0/prd",
            body={"appsflyer_id": "af-001"},
            headers={"x-signature": "firma_completamente_invalida"},
        )

        response_body, status, _ = webhook_router(request)
        assert status == 401

    def test_unknown_service_returns_400(self):
        """Servicio no registrado en SERVICE_REGISTRY → 400."""
        from main import webhook_router

        request = self._make_request(
            path="/webhook/servicio_fantasma/v1.0.0/dev",
            body={"data": "test"},
        )

        response_body, status, _ = webhook_router(request)
        assert status == 400

    def test_invalid_path_returns_400(self):
        """Path malformado → 400."""
        from main import webhook_router

        request = self._make_request(path="/webhook/appsflyer")
        response_body, status, _ = webhook_router(request)
        assert status == 400

    def test_health_check_returns_200(self):
        """Health check no requiere autenticación ni cuerpo."""
        from main import webhook_router

        request = self._make_request(path="/webhook/health")
        response_body, status, _ = webhook_router(request)

        result = json.loads(response_body)
        assert status == 200
        assert result["status"] == "healthy"
        assert "services" in result

    @patch("main._get_publisher")
    @patch("main._get_project_id", return_value="test-project")
    def test_empty_body_ignored(self, mock_pid, mock_publisher):
        """Payload vacío retorna 200 con status='ignored' y NO publica."""
        from main import webhook_router

        request = self._make_request(
            path="/webhook/appsflyer/v1.0.0/dev",
        )
        request.get_data.return_value = b""
        request.get_json.return_value = {}

        response_body, status, _ = webhook_router(request)
        result = json.loads(response_body)

        assert status == 200
        assert result["status"] == "ignored"
        mock_publisher.return_value.publish.assert_not_called()

    @patch("main._get_secret", return_value="mi_signing_secret")
    @patch("main._get_project_id", return_value="test-project")
    def test_missing_signature_header_in_prd(self, mock_pid, mock_secret):
        """En prd sin header de firma debe retornar 401."""
        from main import webhook_router

        request = self._make_request(
            path="/webhook/appsflyer/v1.0.0/prd",
            body={"appsflyer_id": "af-001"},
            # Sin header x-signature
        )

        response_body, status, _ = webhook_router(request)
        assert status == 401
