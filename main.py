import csv
import time
import os
from dotenv import load_dotenv
from adb_helper import SmartAdbDevice, list_devices
from imap_helper import get_otp_from_forwarded_mail

# Cấu hình biến môi trường
load_dotenv()

MASTER_EMAIL = os.getenv("MASTER_EMAIL", "tranquoctoan31892@gmail.com")
MASTER_PASSWORD = os.getenv("MASTER_PASSWORD", "")

# URLs quan trọng
LOGIN_URL = "https://www.pokemoncenter-online.com/login/"
LOTTERY_URL = "https://www.pokemoncenter-online.com/lottery/apply.html"

def process_account_smart(device, account):
    serial = device.serial
    target_email = account['Account_Email']
    password = account['Password']

    print(f"\n[{serial}] 🚀 --- BẮT ĐẦU CHẠY TÀI KHOẢN: {target_email} ---")

    # 1. Mở trang đăng nhập & Vượt qua welcome screen
    print(f"[{serial}] Step 1: Mở trang đăng nhập...")
    device.launch_chrome_incognito(LOGIN_URL)
    time.sleep(8)

    # 3. Điền thông tin cực nhanh
    print(f"[{serial}] Step 2: Điền Email và Password...")
    if not device.find_and_type_smart(target_email, is_password=False):
        print(f"[{serial}] ❌ Thất bại: Không tìm thấy ô Email.")
        return False
    
    if not device.find_and_type_smart(password, is_password=True):
        print(f"[{serial}] ❌ Thất bại: Không tìm thấy ô Password.")
        return False

    # 4. Bấm Login
    print(f"[{serial}] Step 3: Bấm nút Login (form1Button)...")
    if not device.click_login_smart():
        print(f"[{serial}] ❌ Thất bại: Không bấm được Login.")
        return False
    
    # 4. Lấy OTP
    print(f"[{serial}] Step 4: Kiểm tra OTP...")
    otp_code = get_otp_from_forwarded_mail(MASTER_EMAIL, MASTER_PASSWORD, target_email)

    if otp_code:
        print(f"[{serial}] Step 5: Đã lấy mã {otp_code}. Đang nhập...")
        # Sử dụng is_otp=True để đảm bảo ko điền nhầm vào ô email
        if not device.find_and_type_smart(otp_code, is_otp=True):
            print(f"[{serial}] ❌ Thất bại: Không tìm thấy ô nhập OTP.")
            return False
            
        if not device.click_verify_otp_smart():
            print(f"[{serial}] ❌ Thất bại: Không bấm được Verify OTP.")
            return False
        
        print(f"[{serial}] ✅ Login thành công. Đang giữ trình duyệt để chuyển sang CHUSEN...")
        time.sleep(5) # Chờ redirect sau login thành công

        # --- BƯỚC QUAN TRỌNG: THỰC HIỆN CHUSEN THEO SCRIPT ---
        
        # Step 6: Truy cập trang Chusen trực tiếp
        print(f"[{serial}] Step 6: Truy cập trang Chusen (Apply Page)...")
        device.open_chrome_incognito(LOTTERY_URL)
        time.sleep(8) # Chờ load List Page

        # Step 7: Chọn Item, Radio, Checkbox và bấm '応募する'
        print(f"[{serial}] Step 7: Đang điền form đăng ký (Radio/Checkbox)...")
        if not device.lottery_select_item_and_apply():
            print(f"[{serial}] ❌ Thất bại: Không chọn được item hoặc ko bấm được '応募する'.")
            return False
            
        time.sleep(3) # Chờ hiện Modal xác nhận

        # Step 8: Bấm nút xác nhận cuối cùng (#applyBtn)
        print(f"[{serial}] Step 8: Nhấn xác nhận đơn (#applyBtn)...")
        if not device.lottery_confirm_final():
            print(f"[{serial}] ❌ Thất bại: Không bấm được nút xác nhận cuối cùng.")
            return False

        # Step 9: Kiểm tra thành công
        print(f"[{serial}] Step 9: Đang chờ trang xác thực thành công...")
        time.sleep(8)
        success_keywords = ["完了", "受け付けました", "登録済み", "応募済み", "Success"]
        for kw in success_keywords:
            if device.d(textContains=kw).exists(timeout=2):
                print(f"[{serial}] 🎉 CHÚC MỪNG: Đã chốt đơn thành công cho {target_email}!")
                time.sleep(5) 
                return True
        
        print(f"[{serial}] ⚠️ Cảnh báo: Đã chạy hết các bước nhưng chưa thấy chữ 'Hoàn tất'.")
        return True # Giả thiết thành công nếu đã bấm hết nút
    else:
        print(f"[{serial}] ❌ Lỗi: Không nhận được OTP.")
        return False

def main():
    serials = list_devices()
    if not serials: return

    # Giả lập load file accounts.csv
    with open('accounts_template.csv', mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Status'] == 'ready':
                device = SmartAdbDevice(serials[0])
                process_account_smart(device, row)
                # Xong 1 acc hãy xoay máy bay nến muốn đổi IP
                # device.airplane_mode_rotate() 

if __name__ == "__main__":
    main()
