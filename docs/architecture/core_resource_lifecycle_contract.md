# Core Resource Lifecycle Contract

## Nguyên tắc phân tầng

NaChance có hai loại readiness độc lập.

| Tầng | Nội dung | Thời điểm bắt buộc |
|---|---|---|
| Core/Qt environment | Python, Core packages, PySide6, cấu hình runtime tối thiểu và khả năng tạo Qt shell | Phải `READY` trước khi tạo UI |
| Workshop resources | Weight, model, binary, optional data và các package đặc thù của Workshop | Có thể `MISSING` khi Qt Lite mở; Core provision nền sau đó |

Thiếu Workshop resource không được làm Core/Qt startup thất bại. Ngược lại, thiếu Core/Qt environment không được phép mở UI để rồi mới sửa sau.

## Startup contract

```text
NaChance.py
  → kiểm tra Core/Qt environment
  → nếu thiếu: Setup/Bootstrap
  → kiểm tra lại
  → nếu Core/Qt READY: tạo Qt UI
  → Qt hiển thị Lite/Compatibility nếu Workshop resource chưa đủ
```

`RuntimeReport.core_ready` là gate duy nhất cho việc tạo UI. `can_run_lite` chỉ là compatibility projection và không được dùng để bỏ qua Core/Qt setup.

## Resource provisioning contract

Sau khi Qt shell đã mở, Core chạy provisioning nền thông qua `CoreWeightManager` và `ResourceTestGate`. Core phải:

1. đọc resource declaration từ Workshop;
2. kiểm tra inventory và canonical `<project-root>/weights/`;
3. nếu đã có file hợp lệ cùng SHA-256 thì không tải lại;
4. nếu thiếu thì tải vào intake/quarantine;
5. kiểm SHA-256, test và approve;
6. materialize vào kho Core dùng chung;
7. phát sự kiện hoặc refresh runtime report;
8. cập nhật Workshop readiness từ `MISSING`/`BLOCKED` sang `READY` khi resource đủ.

Workshop không tự tải weight và không sở hữu kho weight riêng. Qt chỉ trình bày trạng thái và cho phép người dùng theo dõi/cancel/retry provisioning.

## Lite Mode

Lite Mode là trạng thái tạm thời của **Workshop runtime**, không phải trạng thái thiếu môi trường Core. Người dùng có thể mở Qt khi Core/Qt đã sẵn sàng dù Photo chưa có weight hoặc package AI. Khi resource được provision và verify thành công, hệ thống cập nhật trạng thái Workshop trong phiên hiện tại; không cần cài lại Core và không cần khởi động lại toàn bộ app trừ khi dependency Python của Workshop thay đổi.

## Phân biệt package và resource

Package/environment dependency của Workshop vẫn phải được xử lý theo policy cài đặt riêng. Weight/model/binary là resource có thể tải nền. Vì vậy `can_run_full_ai=False` không tự động có nghĩa phải chạy lại setup Core; UI phải phân biệt `missing workshop package` với `missing workshop resource`.

## Gap cần triển khai

Code hiện tại đã có Core gate, downloader và Qt worker, nhưng refresh sau khi provisioning mới chủ yếu cập nhật đường dẫn resource và status text. Cần bổ sung một resource state refresh/event contract để `RuntimeReport`, Workshop readiness và UI cùng phản ánh kết quả sau mỗi lần approve, đồng thời giữ provisioning độc lập với việc Workshop tự tải.
