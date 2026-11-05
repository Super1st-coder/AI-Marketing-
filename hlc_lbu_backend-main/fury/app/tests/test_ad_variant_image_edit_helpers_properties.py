"""Property-based tests for the Variation_Image_Name helper (Property 22).

Target: `services.job_runner_service._variation_image_name` and
`_IMAGE_NAME_EXTENSIONS` (D17, design §11). Kept in its own module so it does
not collide with `test_ad_variant_image_edit_pipeline_properties.py`.
"""
import mimetypes

from hypothesis import given, settings
from hypothesis import strategies as st

from services.job_runner_service import _IMAGE_NAME_EXTENSIONS, _variation_image_name

_E = _IMAGE_NAME_EXTENSIONS

# Image MIME types for which mimetypes.guess_extension is defined on this host.
_IMAGE_MIMES = [
    m
    for m in (
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
        "image/svg+xml",
        "image/x-icon",
    )
    if mimetypes.guess_extension(m)
]


def _stem(s: str) -> str:
    """Reference stem(s) from design Property 22."""
    for e in _E:
        if s.lower().endswith(e) and len(s) > len(e):
            return s[: -len(e)]
    return s


def _ends_with_known_ext(s: str) -> bool:
    return any(s.lower().endswith(e) for e in _E)


# Arbitrary names: Unicode text plus a bias towards dots, spaces, image and
# non-image dotted suffixes.
_names = st.one_of(
    st.text(max_size=30),
    st.builds(
        lambda a, suffix: a + suffix,
        st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=20),
        st.sampled_from(list(_E) + [".PNG", ".Jpeg", ".tar", ".txt", ".2", ". png", ".", " ", ".pngx"]),
    ),
)

_bases = st.text(min_size=1, max_size=30).filter(lambda b: not _ends_with_known_ext(b))


@st.composite
def _cased_ext(draw):
    """An extension from _IMAGE_NAME_EXTENSIONS with random upper/lower casing."""
    ext = draw(st.sampled_from(_E))
    flags = draw(st.lists(st.booleans(), min_size=len(ext), max_size=len(ext)))
    return "".join(c.upper() if up else c for c, up in zip(ext, flags))


@st.composite
def _index_pair(draw):
    index = draw(st.integers(min_value=1, max_value=10))
    j = draw(st.integers(min_value=1, max_value=10).filter(lambda x: x != index))
    return index, j


# Feature: ad-variant-image-edit-pipeline, Property 22: Nombre de variación sin extensión de imagen
@settings(max_examples=100, deadline=None)
@given(
    s=_names,
    base=_bases,
    e=_cased_ext(),
    mime=st.sampled_from(_IMAGE_MIMES),
    indices=_index_pair(),
)
def test_property_22_variation_image_name_without_image_extension(s, base, e, mime, indices):
    """**Validates: Requirements 9.5, 9.12, 9.13, 13.31, 13.32**"""
    index, j = indices
    suffix = f"_{index}"

    # 1. Arbitrary s → stem(s) + _{index}.
    result = _variation_image_name(s, index)
    assert result == _stem(s) + suffix
    assert result.endswith(suffix)

    # 2. base + e strips exactly e; base without extension stays intact.
    with_ext = _variation_image_name(base + e, index)
    assert with_ext == _variation_image_name(base, index) == base + suffix
    assert with_ext != base + e + suffix
    assert _stem(base) == base

    # 3. Appending the real MIME extension leaves a single known extension.
    mime_ext = mimetypes.guess_extension(mime)
    final = with_ext + mime_ext
    assert final.endswith(suffix + mime_ext)
    before_mime = final[: -len(mime_ext)]
    assert not _ends_with_known_ext(before_mime)

    # 4. Empty stem (s is just an extension) → s + _{index}.
    assert _variation_image_name(e, index) == e + suffix
    if s.lower() in _E:
        assert result == s + suffix

    # 5. Distinct indices → distinct names.
    assert _variation_image_name(s, index) != _variation_image_name(s, j)
    assert _variation_image_name(base + e, index) != _variation_image_name(base + e, j)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant image-edit helper property tests passed")
