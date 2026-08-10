"""Load About content without putting product copy in the UI code."""
import json
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_nachance_about(path: Optional[Path] = None) -> Dict[str, str]:
    path = Path(path) if path else PROJECT_ROOT / "config" / "about.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[About] Không đọc được {path}: {exc}")
        return {
            "title": "Giới thiệu NaChance",
            "tagline": "",
            "description": "",
            "workshops_intro": "",
        }


def load_workshop_about(workshop) -> str:
    """Read the ABOUT file declared by a discovered Workshop."""
    path = getattr(workshop, "about_path", None)
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as exc:
        print(f"[About] Không đọc được About của Workshop {workshop.workshop_id}: {exc}")
        return ""
