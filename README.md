# 🧬 AI CHUSEN - MATRIX MONITORING SYSTEM

**Hệ thống tự động hóa đăng ký xổ số (Chusen) Pokemon Center với giao diện Matrix Cyberpunk.**

Hệ thống được thiết kế theo kiến trúc **Hybrid (Electron + Python)**, kết hợp sức mạnh xử lý của Python `uiautomator2` và giao diện Dashboard hiện đại của Electron/Streamlit.

---

## ✨ Tính năng nổi bật

- **Tự động hóa 100%**: Xử lý từ Đăng nhập -> Vượt OTP -> Chọn Vật phẩm -> Hoàn tất đơn hàng.
- **Matrix Dashboard**: Theo dõi log thời gian thực của từng thiết bị đồng thời trên một màn hình duy nhất.
- **Quản lý thiết bị thông minh**: Hỗ trợ quét Node (Phone), Xem màn hình (VIEW), và Reset IP (Airplane Mode) tự động.
- **Cấu hình mạnh mẽ**: Tự động lấy mã OTP từ Mail Master, khớp chính xác từng tài khoản đang chạy.
- **An toàn & Riêng tư**: Chạy Chrome ở chế độ ẩn danh (Incognito) cho mỗi tài khoản, dọn dẹp cache sau mỗi lần chạy.

---

## 🚀 Cách vận hành (Cho người sử dụng)

1. **Cài đặt**: 
   - Truy cập thư mục `desktop/dist/`.
   - Mở file `AI CHUSEN-1.0.0-arm64.dmg` và cài đặt ứng dụng vào thư mục **Applications**.
2. **Khởi chạy**: 
   - Mở ứng dụng **AI CHUSEN** từ Launchpad (Lần đầu mở hãy Chuột phải -> Open).
   - Đảm bảo điện thoại Android đã bật gỡ lỗi USB và kết nối với máy tính.
3. **Thao tác**: 
   - Nhấn **🔭 SCAN FOR NEW NODES** để nhận diện điện thoại.
   - Nhấn **▶ RUN** trên thiết bị mong muốn để bắt đầu quy trình tự động.

---

## 🛠 Hướng dẫn cho Lập trình viên (Development)

### 1. Cấu trúc thư mục
- `desktop/`: Chứa mã nguồn Electron (Frontend).
- `desktop/backend/`: Chứa mã nguồn Python, Streamlit UI và môi trường ảo `py_env`.
- `desktop/assets/`: Chứa icon và hình ảnh ứng dụng.

### 2. Chế độ Phát triển (Dev Mode)
Để chạy thử nghiệm và sửa lỗi nhanh:
```bash
cd desktop
npm install
npm start
```

### 3. Đóng gói ứng dụng (Build)
Để tạo ra file cài đặt `.dmg` mới:
```bash
cd desktop
npm run dist
```

---

## ⚙️ Cấu hình hệ thống

Dữ liệu được quản lý trong thư mục `desktop/backend/`:
- **`.env`**: Điền thông tin `MASTER_EMAIL` và `MASTER_PASSWORD` để nhận mã OTP.
- **`accounts_template.csv`**: Danh sách tài khoản cần Chusen.

---

## ⚠️ Lưu ý kỹ thuật

- **ADB (Android Debug Bridge)**: Đảm bảo máy tính đã cài đặt ADB. Ứng dụng sẽ tự động tìm kiếm ADB tại các đường dẫn mặc định trên macOS.
- **Quyền bảo mật**: Do ứng dụng chưa được ký chứng chỉ Apple chính thức, hãy luôn dùng **Chuột phải (Right-click) -> Open** khi mở app lần đầu tiên.

---
*Phát triển và tối ưu bởi Matrix Dev Group & Antigravity AI.*
