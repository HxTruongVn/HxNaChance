# Hướng dẫn khởi động NaChance

## Nguyên tắc dependency

NaChance Core chỉ cần các package trong `setup/core_requirements.txt` để mở shell và các Workshop nhẹ. Dependency AI nặng của Photo Workshop nằm riêng trong `workshops/photo/requirements.txt`; thiếu chúng không được phép làm Core thoát ngay từ đầu. Photo sẽ hiển thị capability tương ứng ở trạng thái unavailable cho đến khi đủ package và model.

## Windows

Hãy dùng Python 3.10 trở lên được cài kèm tùy chọn **tcl/tk**. Từ thư mục gốc repo, chạy:

```text
python -m pip install -r setup/core_requirements.txt
python NaChance.py
```

Nếu muốn dùng Photo Workshop đầy đủ, cài thêm dependency riêng của nó:

```text
python -m pip install -r workshops/photo/requirements.txt
```

Stack Photo có thể nặng và không bắt buộc để mở Layout hoặc Repo Intake.

## Linux

Ngoài package Python, hệ thống cần Tkinter, thường cài bằng package manager của hệ điều hành, ví dụ Debian/Ubuntu:

```text
sudo apt install python3-tk
python3 -m pip install -r setup/core_requirements.txt
python3 NaChance.py
```

Môi trường không có display đồ họa vẫn có thể chạy Runtime smoke check nhưng không thể mở cửa sổ CustomTkinter.

## Diễn giải lỗi

Nếu log chỉ liệt kê `photo::torch`, `photo::rembg` hoặc các package AI khác, đó là cảnh báo Workshop Photo và Core vẫn phải tiếp tục mở. Nếu log có `core::customtkinter`, cần cài Core UI dependency. Nếu traceback ghi `No module named tkinter`, cần bổ sung Tcl/Tk của Python/hệ điều hành; đây không phải package pip của Photo Workshop.
