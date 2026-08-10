# Photo Workshop — Documentation Boundary

## Trạng thái

`DEFERRED` đối với đợt tái cấu trúc tài liệu Core này.

Photo Workshop tồn tại trong repo và có manifest/UI/implementation riêng.
Tuy nhiên, tài liệu `docs/architecture/` ở cấp Core **không dùng chi tiết
nội bộ của Photo Workshop để chứng minh Core đã hoàn thành kiến trúc mục tiêu**.

## Core chỉ cần biết

Ở cấp hệ thống, Core quan tâm:

- Workshop ID;
- manifest;
- UI metadata;
- capabilities;
- environment/resource declarations;
- input/output contract;
- status.

## Chưa đánh giá ở tài liệu này

- model adapters;
- processor architecture;
- model loading internals;
- shoulder alignment;
- clothing replacement;
- inpainting;
- Photo-specific pipeline.

Xem tài liệu bên trong `workshops/photo/` khi workstream Photo được mở lại.
