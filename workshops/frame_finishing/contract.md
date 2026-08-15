# Frame/Finishing Workshop Contract

## Input

Workshop nhận một image path hoặc folder path. Folder được sắp xếp theo `natural_filename` mặc định; output batch giữ thứ tự trong manifest.

## Processing

Orientation được chuẩn hóa trước khi áp dụng semantic bottom, CropSpec, CAF, FrameSpec, CornerSpec và ShadowSpec. Fix theo cạnh dài giữ toàn bộ nội dung và cho phép CAF; fix theo cạnh ngắn crop theo anchor/zoom.

## Output

Single mode trả về một output image asset. Folder mode trả về `AssetCollection` gồm `items[]` với `order`, `source_path`, `output_path`, `width`, `height`, `orientation` và `sha256`, kèm `manifest.json`.

## Layout handoff

Layout chỉ đọc output image hoặc `AssetCollection`. Layout không cần đọc CropSpec, CAFSpec hay preview state của Workshop.
