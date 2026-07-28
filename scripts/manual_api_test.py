"""
Script thủ công gọi Photo Master Pro API (không phải pytest).

Chạy từ thư mục gốc repo (server phải đang chạy):
  python scripts/manual_api_test.py --image path/to/photo.jpg --output result.png
"""
import argparse
import base64
import json
import sys
from pathlib import Path

import requests

API_BASE = "http://localhost:8000"


def test_health():
    r = requests.get(f"{API_BASE}/health")
    print("Health:", r.status_code)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    return r.ok


def test_process(image_path: str, output_path: str, return_format: str = "file"):
    url = f"{API_BASE}/process"

    options = {
        "preset": "VN Passport (4x6)",
        "bg_mode": "Trắng",
        "face_restore": True,
        "face_restore_fidelity": 0.7,
        "skin_smooth": True,
        "skin_strength": 0.5,
        "eye_enhance": True,
        "remove_bg": True,
        "should_validate": True,
        "return_format": return_format,
    }

    with open(image_path, "rb") as f:
        files = {"file": (image_path, f, "image/jpeg")}
        data = {"options": json.dumps(options)}
        r = requests.post(url, files=files, data=data)

    print("Process status:", r.status_code)

    if r.status_code == 200:
        if return_format == "file":
            with open(output_path, "wb") as out:
                out.write(r.content)
            print(f"✅ Đã lưu ảnh: {output_path}")
        else:
            payload = r.json()
            print(json.dumps({k: v for k, v in payload.items() if k != "image_base64"}, indent=2, ensure_ascii=False))
            if payload.get("image_base64"):
                img_bytes = base64.b64decode(payload["image_base64"])
                with open(output_path, "wb") as out:
                    out.write(img_bytes)
                print(f"✅ Đã lưu ảnh từ base64: {output_path}")
    elif r.status_code == 422:
        print("❌ Validation failed:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    else:
        print("❌ Lỗi:", r.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Đường dẫn ảnh đầu vào")
    parser.add_argument("--output", default="result.png", help="Đường dẫn ảnh đầu ra")
    parser.add_argument("--format", default="file", choices=["file", "base64"])
    args = parser.parse_args()

    if not Path(args.image).is_file():
        print(f"Không tìm thấy file ảnh: {args.image}", file=sys.stderr)
        sys.exit(1)

    if test_health():
        test_process(args.image, args.output, args.format)
    else:
        print("Health check thất bại — kiểm tra server đã chạy chưa.")
        sys.exit(1)
