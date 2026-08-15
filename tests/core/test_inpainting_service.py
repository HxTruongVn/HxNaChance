from PIL import Image
import pytest

from core.inpainting import (
    InpaintRequest,
    InpaintingService,
    MaskSpec,
    SolidFillBackend,
    BackendRegistry,
    build_canvas_mask,
)


def _request(*, backend: str = "solid_fill") -> InpaintRequest:
    image = Image.new("RGBA", (100, 80), (20, 40, 60, 255))
    spec = MaskSpec(
        canvas_size=image.size,
        source_rect=(20, 15, 80, 65),
        fill_regions=((0, 0, 100, 15), (0, 65, 100, 80), (0, 15, 20, 65), (80, 15, 100, 65)),
        feather_px=0,
        dilate_px=0,
    )
    return InpaintRequest(image=image, mask=build_canvas_mask(spec), mask_spec=spec, backend=backend)


def test_mask_contract_and_solid_fill_preserve_source() -> None:
    request = _request()
    result = InpaintingService().expand(request)
    assert result.backend == "solid_fill"
    assert result.changed_bbox == (0, 0, 100, 80)
    assert result.image.getpixel((50, 40)) == (20, 40, 60, 255)
    assert result.image.getpixel((5, 5)) == (255, 255, 255, 255)
    assert result.seam_score is not None


def test_backend_registry_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unknown inpainting backend"):
        InpaintingService().expand(_request(backend="does_not_exist"))


def test_mask_spec_rejects_invalid_source_rect() -> None:
    spec = MaskSpec(canvas_size=(10, 10), source_rect=(0, 0, 11, 10))
    with pytest.raises(ValueError, match="source_rect"):
        spec.validate()


def test_explicit_backend_selection_is_deterministic() -> None:
    request = _request(backend="solid_fill")
    registry = BackendRegistry([SolidFillBackend()])
    result = InpaintingService(registry).expand(request)
    assert result.backend == "solid_fill"


def test_lazy_lama_requires_verified_resource(tmp_path) -> None:
    from hashlib import sha256
    from core.inpainting import LazyLaMaBackend

    model = tmp_path / "lama.bin"
    model.write_bytes(b"approved-model")
    digest = sha256(model.read_bytes()).hexdigest()
    calls = []

    def factory(path):
        calls.append(path)
        return lambda image, mask, seed: image

    backend = LazyLaMaBackend(model, digest, factory)
    assert backend.is_available()
    assert calls == []
    output = backend.run(_request())
    assert output.size == (100, 80)
    assert calls == [model]


def test_lazy_lama_rejects_checksum_mismatch(tmp_path) -> None:
    from core.inpainting import LazyLaMaBackend

    model = tmp_path / "lama.bin"
    model.write_bytes(b"unapproved-model")
    backend = LazyLaMaBackend(model, "0" * 64, lambda path: lambda image, mask, seed: image)
    assert not backend.is_available()


def test_stable_diffusion_is_lazy_and_unavailable_without_optional_packages(tmp_path) -> None:
    from core.inpainting import StableDiffusionInpaintBackend

    backend = StableDiffusionInpaintBackend(tmp_path / "local-model")
    # The sandbox intentionally does not install heavy neural dependencies.
    assert backend.is_available() is False
