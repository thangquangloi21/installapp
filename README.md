# AutoInstall

🔧 **AutoInstall** là một tiện ích nhỏ giúp phục vụ và tải về một file ZIP, giải nén nó, và tạo shortcut trên Desktop trỏ tới file thực thi được giải nén (ví dụ: `testapp.exe`).

---

## 🔎 Tổng quan

- `sever.py` — một server Flask nhỏ để phục vụ file cho việc tải xuống (các endpoint `/app` và `/zip`).
- `client.py` — tải file ZIP từ URL, hỗ trợ resume và kiểm tra SHA256, giải nén an toàn (ngăn path traversal), và có thể tạo shortcut trên Desktop Windows tới file thực thi được giải nén.

---

## ⚙️ Yêu cầu

- Python 3.10+ (đã test với 3.12)
- Windows (việc tạo shortcut trên Desktop sử dụng PowerShell / COM của Windows)
- Tuỳ chọn: cài `tqdm` để hiển thị progress bar

Có một virtual environment nhẹ trong `_autoinstall/` nếu bạn muốn dùng lại.

---

## 🚀 Hướng dẫn nhanh

1. Khởi động server (phục vụ `files/app.zip` và `files/KHSX_LOG.exe`):

```bash
python sever.py
```

Server mặc định chạy trên http://localhost:5000.

2. Chạy client để tải và giải nén:

```bash
python client.py
```

Mặc định, client sẽ:
- tải `http://localhost:5000/zip` → lưu `downloads/sample.zip`
- giải nén vào thư mục `extracted/`
- nếu tìm thấy `testapp.exe` trong nội dung giải nén, sẽ tạo shortcut trên Desktop trỏ tới file đó (chỉ trên Windows)

---

## 📝 Hành vi & Ghi chú

- Hỗ trợ resume: `client.download_zip` cố gắng resume download nếu server hỗ trợ (sử dụng file tạm `.part`).
- Ghi đè nguyên tử: trên Windows dùng `os.replace` để ghi đè file đích một cách nguyên tử khi hoàn tất tải.
- Giải nén an toàn: `client.extract_zip` kiểm tra các member trong zip để ngăn chặn path traversal.
- Shortcut trên Desktop: `client.create_desktop_shortcut` tạo file `.lnk` trên Desktop của user hiện tại bằng PowerShell + COM `WScript.Shell`.
- Nếu cài `tqdm`, sẽ hiển thị progress bar khi tải.

---

## 🧪 Cách kiểm thử nhanh

Bạn có thể kiểm thử giải nén / tạo shortcut nhanh bằng cách tạo một file `testapp.exe` giả trong thư mục tạm và gọi `create_desktop_shortcut` từ Python:

```py
from pathlib import Path
import client

# chuẩn bị file giả
Path('extracted_test').mkdir(exist_ok=True)
with open('extracted_test/testapp.exe', 'wb') as f:
    f.write(b'dummy')

# tạo shortcut
client.create_desktop_shortcut(Path('extracted_test/testapp.exe'), name='testapp')
```

Lúc này sẽ có `testapp.lnk` trên Desktop của bạn.

---

## ✅ Khắc phục sự cố

- Lỗi FileExistsError khi rename: đã được xử lý bằng cách dùng `os.replace` để ghi đè file đích khi đổi tên từ `.part` sang file cuối.
- Nếu tạo shortcut thất bại, client sẽ in ra exception; hãy kiểm tra PowerShell có sẵn và bạn đang chạy trên Windows.

---

## 🧩 Cải tiến đề xuất

- Thêm tuỳ chọn CLI (`--target`, `--overwrite`, `--url`, `--create-shortcut`) qua `argparse` để dễ tự động hoá.
- Thêm unit tests cho `extract_zip` và kiểm tra an toàn đường dẫn.
- Thêm logging và cấu hình retry/backoff.

---

## Giấy phép & Liên hệ

Sử dụng theo phong cách MIT đơn giản — chỉnh sửa tuỳ ý.

Nếu bạn muốn, tôi có thể thêm giao diện dòng lệnh hoặc flow cài đặt tự động tiếp theo.