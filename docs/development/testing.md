# Testing

## Hiện trạng

Repo có unit tests cho các thành phần chính, bao gồm các nhóm liên quan đến:

- alignment;
- model registry;
- photo agent;
- runtime manager;
- smoke;
- spec/presets.

CI hiện có workflow GitHub Actions.

## Những gì test hiện tại chứng minh

Unit test chứng minh từng phần có thể hoạt động theo contract nhỏ của nó.

Smoke/import tests giúp phát hiện lỗi cấu trúc/import.

## Những gì chưa được chứng minh đầy đủ

Chưa có một integration test cấp hệ thống bao phủ trọn:

```text
Bootstrap
 → Runtime discovery
 → Workshop discovery
 → requirement analysis
 → resource state
 → Core activation
 → Pipeline persistence
```

Đây là ưu tiên để kiểm chứng **Core**, độc lập với việc xử lý nội bộ của Workshop.

## Test contract tối thiểu cho Core

### 1. Workshop discovery

Thêm một Workshop fixture có manifest.

Kỳ vọng:

```text
manifest → discovered
```

Không sửa `app/main_ui.py`.

### 2. Workshop requirement audit

Manifest + requirements + resource metadata phải được đọc đúng.

### 3. Runtime verification

Fixture khai báo requirement thiếu phải tạo trạng thái/report đúng.

### 4. Setup handoff

Bootstrap phải chuyển sang Setup khi môi trường chưa đạt và verify lại.

### 5. Pipeline persistence

Create → save → reload → compare snapshot.

### 6. Broken Workshop isolation

Manifest/UI của một Workshop lỗi không được làm Core crash toàn bộ theo
chính sách hiện tại của discovery.

## Nguyên tắc

Không coi "test import được" là bằng chứng rằng kiến trúc đã hoàn thành.

Mỗi claim kiến trúc quan trọng phải có ít nhất một test hoặc một kiểm chứng
runtime tương ứng.
