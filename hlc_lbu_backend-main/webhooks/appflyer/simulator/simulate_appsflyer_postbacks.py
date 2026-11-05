#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import hmac
import hashlib
import random
import string
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List

import requests


PLATFORMS = ["ios", "android"]
CURRENCIES = ["USD", "EUR", "MXN", "BRL", "GBP"]
MEDIA_SOURCES = ["facebook", "googleadwords_int", "organic", "tiktokglobal_int", "twitter", "snapchat_int"]
CAMPAIGNS = ["spring_sale", "black_friday", "retargeting_q3", "brand_prospecting", "lookalike_v2", "ua_latam"]

def rand_ip() -> str:
    return ".".join(str(random.randint(1, 254)) for _ in range(4))

def rand_device_id(platform: str) -> Dict[str, str]:
    if platform == "ios":
        idfa = "-".join([
            ''.join(random.choices("0123456789ABCDEF", k=8)),
            ''.join(random.choices("0123456789ABCDEF", k=4)),
            ''.join(random.choices("0123456789ABCDEF", k=4)),
            ''.join(random.choices("0123456789ABCDEF", k=4)),
            ''.join(random.choices("0123456789ABCDEF", k=12)),
        ])
        return {"idfa": idfa}
    else:
        gaid = str(uuid.uuid4())
        return {"advertising_id": gaid}

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def random_user_id() -> str:
    return "user_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

def pick_media() -> Tuple[str, str]:
    source = random.choice(MEDIA_SOURCES)
    if source == "organic":
        campaign = "(not set)"
    else:
        campaign = random.choice(CAMPAIGNS)
    return source, campaign


def event_install(app_id: str, platform: str) -> Dict[str, Any]:
    media_source, campaign = pick_media()
    dev_ids = rand_device_id(platform)

    payload = {
        "event": "install",
        "app_id": app_id,
        "platform": platform,
        "install_time": now_iso(),
        "af_attribution": {
            "media_source": media_source,
            "campaign": campaign,
            "is_retargeting": media_source != "organic" and random.random() < 0.2
        },
        "ip": rand_ip(),
        "country_code": random.choice(["US", "MX", "BR", "GB", "DE", "FR"]),
        "language": random.choice(["en", "es", "pt", "fr", "de"]),
        "sdk_version": random.choice(["6.12.0", "6.13.2", "6.14.1"]),
        "app_version": random.choice(["1.3.0", "1.4.5", "2.0.0"]),
        "af_user_id": random_user_id(),
        **dev_ids
    }
    return payload

def event_purchase(app_id: str, platform: str) -> Dict[str, Any]:
    base = event_session(app_id, platform) 
    revenue = round(random.uniform(0.99, 149.99), 2)
    currency = random.choice(CURRENCIES)
    base.update({
        "event": "purchase",
        "revenue": revenue,
        "currency": currency,
        "order_id": str(uuid.uuid4()),
        "items": [
            {
                "sku": random.choice(["coins_100", "noads", "season_pass", "bundle_gold"]),
                "price": revenue,
                "currency": currency,
                "qty": 1
            }
        ]
    })
    return base

def event_session(app_id: str, platform: str) -> Dict[str, Any]:
    media_source, campaign = pick_media()
    dev_ids = rand_device_id(platform)
    duration = int(random.expovariate(1/180)) 

    payload = {
        "event": "session",
        "app_id": app_id,
        "platform": platform,
        "session_start_time": now_iso(),
        "session_duration": duration,
        "device": {
            "os_version": random.choice(["17.5.1", "16.7.8"]) if platform == "ios" else random.choice(["14", "13"]),
            "model": random.choice(["iPhone15,2", "iPhone14,7"]) if platform == "ios" else random.choice(["SM-S921B", "Pixel 8", "M2101K9G"])
        },
        "af_attribution": {
            "media_source": media_source,
            "campaign": campaign,
            "is_retargeting": media_source != "organic" and random.random() < 0.25
        },
        "ip": rand_ip(),
        "af_user_id": random_user_id(),
        **dev_ids
    }
    return payload

GENS = {
    "install": event_install,
    "purchase": event_purchase,
    "session": event_session,
}


def sign_body(body_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

def send_event(
    url: str,
    secret: str,
    payload: Dict[str, Any],
    timeout: float = 10.0,
    max_retries: int = 3,
) -> Tuple[int, str]:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = sign_body(body, secret) if secret else None

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AppsFlyer-Postback-Simulator/1.0",
    }
    if signature:
        headers["X-AppFlyer-Signature"] = signature  

    last_status = 0
    last_text = ""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, data=body, headers=headers, timeout=timeout)
            last_status, last_text = resp.status_code, resp.text
            if 200 <= resp.status_code < 300 or resp.status_code == 429:
                return last_status, last_text
        except requests.RequestException as e:
            last_status, last_text = 0, str(e)

        sleep_s = min(2 ** attempt + random.random(), 10.0)
        time.sleep(sleep_s)

    return last_status, last_text


def main():
    parser = argparse.ArgumentParser(
        description="Simulador de postbacks de AppsFlyer (install, purchase, session) con HMAC."
    )
    parser.add_argument("--url", required=True, help="Endpoint de tu webhook (ej. https://.../webhook_entry_point)")
    parser.add_argument("--secret", default="", help="Secreto HMAC (APPSFLYER_HMAC_SECRET). Si vacío, no firma.")
    parser.add_argument("--app-id", required=True, help="ID de tu app (ej. com.tuapp.mobile)")
    parser.add_argument("--platform", choices=PLATFORMS, default="android", help="Plataforma del evento")
    parser.add_argument("--types", default="install,purchase,session",
                        help="Lista separada por comas de tipos de evento a enviar")
    parser.add_argument("--count", type=int, default=10, help="Número total de eventos a enviar")
    parser.add_argument("--min-delay-ms", type=int, default=200, help="Espera mínima entre eventos (ms)")
    parser.add_argument("--max-delay-ms", type=int, default=1200, help="Espera máxima entre eventos (ms)")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout por request (s)")

    args = parser.parse_args()

    event_types = [t.strip() for t in args.types.split(",") if t.strip() in GENS]
    if not event_types:
        raise SystemExit("Debes elegir al menos un tipo válido: install, purchase, session")

    sent = 0
    for i in range(args.count):
        etype = random.choice(event_types)
        payload = GENS[etype](args.app_id, args.platform)
        status, body = send_event(args.url, args.secret, payload, timeout=args.timeout)
        sent += 1
        print(f"[{sent}/{args.count}] {etype.upper()} -> HTTP {status} | resp={body[:200]!r}")

        delay_ms = random.randint(args.min_delay_ms, args.max_delay_ms)
        time.sleep(delay_ms / 1000.0)

if __name__ == "__main__":
    main()
