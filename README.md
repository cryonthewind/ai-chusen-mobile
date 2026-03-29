# AI Chusen - Hệ thống Tự động hóa Phone Sync (Hướng dẫn)

Hệ thống này giúp bạn điều khiển nhiều điện thoại Android để tự động đăng nhập vào Pokemon Center Online, lấy mã OTP từ Email trung tâm (Forwarding) và thực hiện các bước đăng ký/chăm sóc tài khoản.

---

### 1. Chuẩn bị (Prerequisites)
- **Điện thoại:** Android thật. Cần bật **Tùy chọn nhà phát triển** -> **Gỡ lỗi USB (USB Debugging)**.
- **Máy tính:** Cài đặt ADB (Android Debug Bridge).
- **Python:** Phiên bản 3.9 trở lên.

### 2. Cài đặt (Installation)
Chạy lệnh sau tại thư mục dự án để cài đặt các thư viện cần thiết:
```bash
pip install uiautomator2 streamlit python-dotenv pandas
```

### 3. Cấu hình (Configuration)

#### Bước 3.1: File `.env` (Thông tin Mail chính)
Mở file `.env` và điền thông tin Mail nhận thư chuyển tiếp (Forwarding):
- `MASTER_EMAIL`: Địa chỉ Gmail chính.
- `MASTER_PASSWORD`: Mật khẩu ứng dụng (App Password) 16 ký tự.

#### Bước 3.2: File `accounts_template.csv` (Danh sách tài khoản)
- `Account_Email`: Email (Username) dùng để đăng nhập.
- `Password`: Mật khẩu tài khoản.
- `Device_Serial`: (Tùy chọn) Mã sê-ri điện thoại (xem trên Dashboard).

---

### 4. Cách vận hành (Operation)

**Cách 1: Sử dụng Giao diện Dashboard (Khuyên dùng)**
Chạy lệnh sau để mở Dashboard trên trình duyệt:
```bash
streamlit run app_ui.py
```
- Bấm **"Quét thiết bị"** để robot nhận diện các phone đang cắm.
- Bấm **"Bắt đầu Chusen tự động"** để chạy.

**Cách 2: Chạy trực tiếp qua Terminal**
```bash
python3 main.py
```

---

### 5. Lưu ý khi chạy lần đầu
1. **ATX Agent:** Khi chạy lần đầu, trên điện thoại có thể hiện thông báo cài đặt một ứng dụng nhỏ (ATX hoặc AdbKeyboard), bạn hãy bấm cho phép/đồng ý trên điện thoại.
2. **Tab ẩn danh:** Robot sẽ tự động mở Chrome ở chế độ ẩn danh (Incognito) để không lưu lại lịch sử sau khi xong mỗi tài khoản.
3. **Đổi IP (Airplane Mode):** Cứ sau 10 tài khoản, hệ thống sẽ tự động bật/tắt chế độ máy bay để đổi IP mạng 4G.

---
**Chúc bạn vận hành thành công!** Nếu gặp lỗi về tọa độ hoặc không lấy được OTP, hãy gửi log cho tôi để điều chỉnh.
