"""Shared Template_Definition fixtures for the adset-creative-diversity tests (not a
test module; same convention as `_*_fakes.py`, importable with
`python -m tests.<module>` and with pytest).

Contents:
    TEMPLATE_1BB5C1AD_ID   id of the Abyssale template `1bb5c1ad`
    TEMPLATE_1BB5C1AD      its Template_Definition (the `template` field returned by
                           `get_a_template_definition` when `ok` is true), Req 12.29:
                           `root` container, `image_0` image, `degradado_bottom`
                           image, `degradado_top` image, `hook` text, `tagline` text
                           and `logo_0` logo, each with `layout["instagram-portrait"]`,
                           plus `formats`. No top-level `preview_url` (same shape as
                           `_MOCK_TEMPLATES`) and no signed URLs (no query strings).
    template_1bb5c1ad()    deep copy of TEMPLATE_1BB5C1AD, for tests that mutate it
    template_1bb5c1ad_response()
                           `{"ok": True, "template": template_1bb5c1ad()}`, the shape
                           of `get_a_template_definition(template_id)`

Expected Image_Elements with the default Decorative_Image_Patterns (P15, D23):
`["image_0"]` (`degradado_*` are decorative; `hook`/`tagline`/`logo_0`/`root` are not
`image`). `image_0` has `instagram-portrait` dimensions 1080x1350.
"""

from __future__ import annotations

import copy
from typing import Any

TEMPLATE_1BB5C1AD_ID = "1bb5c1ad"

_ASSETS = f"https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/{TEMPLATE_1BB5C1AD_ID}"
_PREVIEWS = f"https://production-banners.s3-eu-west-1.amazonaws.com/templates/{TEMPLATE_1BB5C1AD_ID}"

_SETTINGS = {"is_mandatory": False}


def _layout(x: int, y: int, width: int, height: int) -> dict[str, dict[str, int]]:
    return {"instagram-portrait": {"x": x, "y": y, "width": width, "height": height}}


def _values(value: str) -> dict[str, str]:
    return {"instagram-portrait": value}


def _image_attributes(file_name: str) -> list[dict[str, Any]]:
    return [{
        "id": "image_url",
        "help": "Public HTTP(s) URL of the image (i.e. https://photo.com/image.png)",
        "values": _values(f"{_ASSETS}/{file_name}"),
    }]


def _text_attributes(payload: str, color: str) -> list[dict[str, Any]]:
    return [
        {"id": "payload", "help": "Text content (i.e. Lorem ipsum)", "values": _values(payload)},
        {"id": "color",
         "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
         "values": _values(color)},
    ]


TEMPLATE_1BB5C1AD: dict[str, Any] = {
    "id": TEMPLATE_1BB5C1AD_ID,
    "template_id": TEMPLATE_1BB5C1AD_ID,
    "name": "Portrait hook + tagline",
    "type": "static",
    "formats": [
        {
            "id": "instagram-portrait",
            "uid": f"{TEMPLATE_1BB5C1AD_ID}-instagram-portrait",
            "width": 1080,
            "height": 1350,
            "unit": "px",
            "preview_url": f"{_PREVIEWS}/preview-instagram-portrait.png",
        },
    ],
    "elements": [
        {
            "name": "root",
            "type": "container",
            "settings": dict(_SETTINGS),
            "attributes": [{
                "id": "background_color",
                "help": "6 or 8 digits hexadecimal background color (i.e. #F3F3F3) of the banner ",
                "values": _values("#FFFFFF"),
            }],
            "layout": _layout(0, 0, 1080, 1350),
        },
        {
            "name": "image_0",
            "type": "image",
            "settings": dict(_SETTINGS),
            "attributes": _image_attributes("image_0.png"),
            "layout": _layout(0, 0, 1080, 1350),
        },
        {
            "name": "degradado_bottom",
            "type": "image",
            "settings": dict(_SETTINGS),
            "attributes": _image_attributes("degradado_bottom.png"),
            "layout": _layout(0, 810, 1080, 540),
        },
        {
            "name": "degradado_top",
            "type": "image",
            "settings": dict(_SETTINGS),
            "attributes": _image_attributes("degradado_top.png"),
            "layout": _layout(0, 0, 1080, 405),
        },
        {
            "name": "hook",
            "type": "text",
            "settings": dict(_SETTINGS),
            "attributes": _text_attributes("Hook... Max Char. 40", "#FFFFFF"),
            "layout": _layout(90, 1010, 900, 120),
        },
        {
            "name": "tagline",
            "type": "text",
            "settings": dict(_SETTINGS),
            "attributes": _text_attributes("Tagline... Max Char. 60", "#FFFFFF"),
            "layout": _layout(90, 1150, 900, 70),
        },
        {
            "name": "logo_0",
            "type": "logo",
            "settings": dict(_SETTINGS),
            "attributes": _image_attributes("logo_0.png"),
            "layout": _layout(390, 70, 300, 90),
        },
    ],
}


def template_1bb5c1ad() -> dict[str, Any]:
    """Deep copy of `TEMPLATE_1BB5C1AD`."""
    return copy.deepcopy(TEMPLATE_1BB5C1AD)


def template_1bb5c1ad_response() -> dict[str, Any]:
    """`get_a_template_definition("1bb5c1ad")` success shape with a deep copy."""
    return {"ok": True, "template": template_1bb5c1ad()}
