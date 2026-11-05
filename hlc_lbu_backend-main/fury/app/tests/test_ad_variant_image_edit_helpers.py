"""Unit tests for the Variation_Image_Name helper (Req 9.5, 9.12, 9.13, 13.31).

Target: `services.job_runner_service._variation_image_name` and
`_IMAGE_NAME_EXTENSIONS` (D17). No Hypothesis — plain examples only.
"""
import mimetypes

from services.job_runner_service import _IMAGE_NAME_EXTENSIONS, _variation_image_name


def test_variation_image_name_examples():
    """Req 9.5, 9.12, 9.13 — at most one known extension stripped, `_{index}` appended."""
    cases = [
        (("banner.png", 1), "banner_1"),
        (("banner.JPG", 2), "banner_2"),
        (("banner", 3), "banner_3"),
        (("promo v1.2", 1), "promo v1.2_1"),
        (("photo.tar.png", 1), "photo.tar_1"),
        ((".png", 1), ".png_1"),
    ]
    for (name, index), expected in cases:
        assert _variation_image_name(name, index) == expected, (name, index)


def test_image_name_extensions_exact_set():
    """Req 9.12 — exactly the 5 Image_Name_Extensions."""
    assert len(_IMAGE_NAME_EXTENSIONS) == 5
    assert set(_IMAGE_NAME_EXTENSIONS) == {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def test_extension_stripping_is_case_insensitive():
    """Req 9.12 — lower, upper and mixed case give the same result."""
    for ext in _IMAGE_NAME_EXTENSIONS:
        mixed = "".join(c.upper() if i % 2 else c for i, c in enumerate(ext))
        for variant in (ext.lower(), ext.upper(), mixed):
            assert _variation_image_name(f"banner{variant}", 1) == "banner_1", variant


def test_no_double_extension_extension_follows_real_content():
    """Req 9.13, 13.31 — final name gets only the extension of the real MIME type."""
    png_ext = mimetypes.guess_extension("image/png")
    for name in ("banner.png", "banner.jpg"):
        assert _variation_image_name(name, 1) + png_ext == "banner_1.png", name


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant image-edit helper tests passed")
