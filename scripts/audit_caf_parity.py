from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

from workshops.layout.print_layout import caf_process
from workshops.frame_finishing.sample_worker import CAFSpec, CropSpec, RenderConfig, render_one


def main() -> None:
    cases = {
        "landscape": Image.new("RGB", (1600, 900), (220, 80, 60)),
        "portrait": Image.new("RGB", (900, 1600), (60, 100, 220)),
    }
    for name, source in cases.items():
        layout_long = caf_process(source, 10, 15, 0, 300)
        layout_hybrid = caf_process(source, 10, 15, 2, 300)
        frame_long = render_one(
            source,
            RenderConfig(1181, 1772, crop=CropSpec(mode="long_side"), caf=CAFSpec(fill_kind="solid", color="ffffff")),
        )
        frame_short = render_one(
            source,
            RenderConfig(1181, 1772, crop=CropSpec(mode="short_side", caf_enabled=False, anchor_x=0.5, anchor_y=0.5)),
        )
        print(name)
        print({
            "source": source.size,
            "layout_fit_long": layout_long.size,
            "layout_hybrid": layout_hybrid.size,
            "frame_long": frame_long.size,
            "frame_short": frame_short.size,
        })


if __name__ == "__main__":
    main()
