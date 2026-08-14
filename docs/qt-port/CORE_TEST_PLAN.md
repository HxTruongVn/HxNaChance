# Core Test Plan

## Phạm vi

Bộ test của NaChance Core chỉ chứng minh rằng Core có thể tiếp nhận, mô tả, xác thực và vận hành một Workshop theo contract. Core không kiểm thử nghiệp vụ riêng của Photo hoặc Layout, không kiểm thử chất lượng ảnh, preset, preview nghiệp vụ hay thuật toán AI của Workshop.

> Một Workshop được coi là đủ điều kiện để Core tiếp nhận khi manifest, resource, capability, runtime và entry point của nó đáp ứng contract; các test nghiệp vụ sâu hơn thuộc về repository của chính Workshop.

## Cây thư mục chuẩn

```text
tests/
├── core/
│   ├── test_runtime_manager.py
│   ├── test_workshop_registry.py
│   ├── test_manifest.py
│   ├── test_resources.py
│   ├── test_capabilities.py
│   └── test_runtime_service.py
├── integration/
│   ├── test_core_bootstrap.py
│   ├── test_core_discovery.py
│   └── test_core_runtime.py
├── smoke/
│   └── test_startup.py
└── contract/
    ├── test_manifest_contract.py
    ├── test_workshop_contract.py
    └── test_runtime_contract.py
```

## Phân định trách nhiệm

| Nhóm | Trách nhiệm | Không kiểm thử |
|---|---|---|
| `core/` | Logic thuần của RuntimeManager, registry, manifest, resource, capability và runtime service | UI, Photo/Layout business logic, model quality |
| `integration/` | Nối các thành phần Core với nhau trong bootstrap, discovery và runtime | Chi tiết giao diện Workshop |
| `smoke/` | Khởi động tối thiểu, Core thiếu dependency phải bị chặn đúng | Tính năng AI hoặc output ảnh |
| `contract/` | Quy tắc mà Workshop bên ngoài phải đáp ứng để được Core tiếp nhận | Nội dung nghiệp vụ riêng của từng Workshop |
| Repository Workshop | Test thuật toán, preset, preview, output và UI của Workshop | Không thay thế contract test của Core |

## Quy tắc chạy

Lệnh kiểm tra contract/Core là `python -m pytest tests/core tests/integration tests/smoke tests/contract`. Bộ test Qt và test nghiệp vụ Workshop được chạy riêng, không dùng để quyết định Core contract có hợp lệ hay không.

## Quy tắc tương thích

Các alias legacy chỉ được kiểm tra trong `contract/test_runtime_contract.py` hoặc test compatibility riêng. Test mới không được import trực tiếp alias legacy nếu có API canonical tương ứng. Core phải không phụ thuộc vào việc Photo hoặc Layout tồn tại trong cây thư mục.
