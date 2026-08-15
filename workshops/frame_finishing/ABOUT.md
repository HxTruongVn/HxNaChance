# Frame/Finishing Workshop

Workshop nhẹ để đóng khung một ảnh hoặc một thư mục ảnh trước khi chuyển output sang Layout.

## Trạng thái scaffold

Bản scaffold hiện cung cấp manifest, Qt entrypoint, preset metadata và resource declaration để NaChance Core discovery nhận diện khi khởi động. Renderer/batch worker tham khảo nằm ở `workshops/frame_finishing/sample_worker.py`.

## Nguyên tắc

Workshop không sở hữu kho weights. Core quản lý orientation service, resource registry, SHA-256 và output manifest. Layout chỉ nhận image/asset collection đã hoàn thiện.
