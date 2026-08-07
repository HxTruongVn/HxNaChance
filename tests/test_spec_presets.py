"""Preset loading — needs numpy + opencv (same as engine import)."""

from workshops.photo import DEFAULT_PRESET_NAME, SPEC_PRESETS, PhotoSpec


def test_spec_presets_loaded():
    assert len(SPEC_PRESETS) >= 1
    assert DEFAULT_PRESET_NAME in SPEC_PRESETS


def test_vn_passport_preset_fields():
    key = "VN Passport (4x6)"
    if key not in SPEC_PRESETS:
        return
    spec = SPEC_PRESETS[key]
    assert isinstance(spec, PhotoSpec)
    assert spec.w == 1200
    assert spec.h == 1800
    assert spec.dpi == 300
