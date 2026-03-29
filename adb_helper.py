import uiautomator2 as u2
import subprocess
import time

def list_devices():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    devices = [line.split("\t")[0] for line in lines if line.strip() and "\tdevice" in line]
    return devices

class SmartAdbDevice:
    def __init__(self, serial):
        self.serial = serial
        self.d = u2.connect(serial)
        print(f"[{serial}] Connected Smart Device.")

    def skip_chrome_onboarding(self):
        """Vượt qua tất cả các màn hình chào mừng của Chrome (Anh, Việt, Nhật)."""
        # Kiểm tra nhanh xem có màn hình onboarding không bằng cách tìm nút 'No thanks' hoặc 'Accept'
        # Nếu không có, thoát sớm để tiết kiệm thời gian
        onboarding_indicator = [
            "No thanks", "Không, cảm ơn", "利用しない", 
            "Accept & continue", "Chấp nhận và tiếp tục", "同意して続行"
        ]
        
        found = False
        for word in onboarding_indicator:
            if self.d(text=word).exists(timeout=1):
                found = True
                break
        
        if not found:
            return

        print(f"[{self.serial}] Phát hiện màn hình Onboarding Chrome. Đang bỏ qua...")
        # Bộ từ khóa các nút cần bấm
        skip_keywords = [
            "No thanks", "Không, cảm ơn", "利用しない", 
            "Don't sign in", "Không đăng nhập", "ログインしない",
            "Accept & continue", "Chấp nhận và tiếp tục", "同意して続行",
            "Next", "Tiếp theo", "次へ",
            "Continue", "Tiếp tục"
        ]
        
        for _ in range(3):
            for word in skip_keywords:
                btn = self.d(text=word)
                if btn.exists(timeout=0.5):
                    btn.click()
            self.d(resourceId="com.android.chrome:id/terms_accept").click_exists(timeout=0.5)
            self.d(resourceId="com.android.chrome:id/next_button").click_exists(timeout=0.5)
            self.d(resourceId="com.android.chrome:id/negative_button").click_exists(timeout=0.5)
            self.d(resourceId="com.android.chrome:id/signin_fre_dismiss_button").click_exists(timeout=0.5)
            time.sleep(1)

    def open_chrome_incognito(self, url):
        """Mở URL trong trình duyệt ẩn danh. Nếu Chrome đang chạy, nó sẽ KHÔNG đóng mà chỉ điều hướng."""
        # Chỉ đóng Chrome nếu nó chưa ở chế độ incognito hoặc chưa có cửa sổ nào
        # Nhưng để đơn giản, ta dùng flag -d trực tiếp
        cmd = f"adb -s {self.serial} shell am start -n com.android.chrome/com.google.android.apps.chrome.Main -d '{url}' --ez 'com.google.android.apps.chrome.EXTRA_IS_INCOGNITO' true"
        subprocess.run(cmd, shell=True)

    def launch_chrome_incognito(self, url):
        """Khởi động mới trình duyệt ẩn danh (đóng bản cũ nếu cần)."""
        self.close_chrome()
        time.sleep(1)
        self.open_chrome_incognito(url)
        # Chờ load màn fre ngắn hơn
        time.sleep(3) 
        self.skip_chrome_onboarding()

    def find_and_type_smart(self, value, is_password=False, is_otp=False):
        """Tự động tìm và điền text dựa trên hint/text của field."""
        inputs = self.d(className="android.widget.EditText")
        if not inputs.exists(timeout=2):
            return False

        for input_field in inputs:
            txt = (input_field.info.get('text') or "").lower()
            hint = (input_field.info.get('hint') or "").lower()
            desc = (input_field.info.get('contentDescription') or "").lower()
            
            # Keyboards theo chế độ
            if is_password:
                ks = ["password", "mật khẩu", "パスワード"]
            elif is_otp:
                ks = ["otp", "code", "mã", "パスコード"]
            else: # Email
                ks = ["email", "mail", "メール"]

            if any(k in txt or k in hint or k in desc for k in ks):
                input_field.clear_text()
                time.sleep(0.5)
                input_field.set_text(value)
                return True

        # Fallback về index nếu không tìm thấy keywords
        # Nếu có 1 ô duy nhất trên màn (VD: màn OTP), cứ hốt đại
        if inputs.count == 1:
            inputs[0].clear_text()
            inputs[0].set_text(value)
            return True
            
        # Fallback cổ điển
        idx = 1 if is_password else 0
        if inputs.count > idx:
            inputs[idx].clear_text()
            inputs[idx].set_text(value)
            return True
        return False

    def click_login_smart(self):
        if self.d(resourceId="form1Button").exists(timeout=2):
            self.d(resourceId="form1Button").click()
            return True
        return False

    def click_verify_otp_smart(self):
        if self.d(resourceId="authBtn").exists(timeout=2):
            self.d(resourceId="authBtn").click()
            return True
        return False

    # --- LOTTERY SPECIALIZED METHODS ---
    def lottery_click_proceed(self):
        """Bấm '抽選へ進む' trên trang Landing Page."""
        btn = self.d(text="抽選へ進む")
        if btn.exists(timeout=5):
            btn.click()
            return True
        return False

    def lottery_select_item_and_apply(self):
        """
        Thực hiện tổ hợp: 
        1. Tìm item '受付中'
        2. Mở '詳しく見る' nếu cần
        3. Chọn Radio
        4. Tích Checkbox đồng ý
        5. Bấm '応募する' để hiện Modal xác nhận
        """
        # 1. Tìm khu vực có chữ '受付中'
        # Trong u2, có thể tìm cha của text '受付中'
        item = self.d(text="受付中")
        if not item.exists(timeout=5):
            print("Không tìm thấy mục nào đang '受付中'")
            return False

        # 2. Click '詳しく見る' (nếu có và chưa mở)
        # Thường là click vào chính vùng đó hoặc nút lân cận
        details_btn = self.d(textContains="詳しく見る")
        if details_btn.exists(timeout=2):
            details_btn.click()
            time.sleep(1)

        # 3. Chọn Radio Button
        radio = self.d(className="android.widget.RadioButton")
        if radio.exists(timeout=2):
            radio.click()
            time.sleep(1)

        # 4. Tích Checkbox đồng ý (Thường có id hoặc text liên quan đến đồng ý)
        # Dựa trên script: .agreementArea
        checkbox = self.d(className="android.widget.CheckBox")
        if checkbox.exists(timeout=2):
            if not checkbox.info.get('checked'):
                checkbox.click()
                time.sleep(1)

        # 5. Bấm '応募する' (Nút mở Modal)
        apply_modal_btn = self.d(text="応募する")
        if apply_modal_btn.exists(timeout=2):
            apply_modal_btn.click()
            return True
        
        return False

    def lottery_confirm_final(self):
        """Bấm nút xác nhận cuối cùng trong Modal (#applyBtn)."""
        # Thử tìm theo ID 'applyBtn' như trong script
        final_btn = self.d(resourceId="applyBtn")
        if not final_btn.exists(timeout=3):
            # Thử tìm theo text nếu ID không ăn
            final_btn = self.d(text="応募する") # Trong modal có thể vẫn là text này
        
        if final_btn.exists(timeout=3):
            final_btn.click()
            return True
        return False

    def clear_chrome(self) :
        # Chỉ dùng khi thật sự cần reset triệt để
        subprocess.run(f"adb -s {self.serial} shell pm clear com.android.chrome", shell=True)
        time.sleep(2)

    def airplane_mode_rotate(self, delay=5):
        subprocess.run(f"adb -s {self.serial} shell settings put global airplane_mode_on 1", shell=True)
        time.sleep(delay)
        subprocess.run(f"adb -s {self.serial} shell settings put global airplane_mode_on 0", shell=True)
        time.sleep(delay)

    def close_chrome(self):
        subprocess.run(f"adb -s {self.serial} shell am force-stop com.android.chrome", shell=True)
        time.sleep(0.5)
