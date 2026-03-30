import time
import logging
from src.core.robot import AdbRobot
from src.core.ui_map import PokeCenterUiMap
from src.utils.config import Config

logger = logging.getLogger("SystemController")

class PokeCenterController:
    """
    Lớp điều khiển Logic (Brain/Controller).
    Sử dụng Robot để thực hiện các bước của Pokemon Center theo luồng.
    """
    def __init__(self, serial):
        self.serial = serial
        self.robot = AdbRobot(serial)
        self.ui = PokeCenterUiMap()

    def setup_browser(self):
        """Khởi động Chrome sạch và vượt qua các màn hình chào mừng."""
        logger.info(f"[{self.serial}] Đang chuẩn bị trình duyệt...")
        self.robot.force_stop_app()
        time.sleep(1)
        self.robot.open_url(self.ui.LOGIN_URL, incognito=Config.INCOGNITO_DEFAULT)
        
        # Vòng lặp chờ trang login hoặc xử lý onboarding/navigation
        start_time = time.time()
        while time.time() - start_time < Config.WAIT_FOR_ELEMENT:
            # 1. Kiểm tra nếu ĐÃ ở trang Login (Thấy ô nhập Email/Pass)
            if self.robot.d(className="android.widget.EditText").exists:
                # Nếu thấy nhiều hơn 1 ô EditText (thường là Email và Pass) thì DONE.
                if self.robot.d(className="android.widget.EditText").count >= 1:
                    logger.info(f"[{self.serial}] Đã vào được trang Login (Thấy ô Input).")
                    return True
            
            # 2. Thử click nút "Login / Hội viên" từ trang chủ (Navigaton)
            for nav_txt in self.ui.NAVIGATION_LOGIN_TEXTS:
                if self.robot.d(textContains=nav_txt).exists:
                    self.robot.click_smart(selectors_text=[nav_txt])
                    logger.info(f"[{self.serial}] Clicked navigation to Login: {nav_txt}")
                    time.sleep(2)
                    break
                
            # 3. Thử click các nút "vượt rào" của Chrome (Onboarding)
            found_skip = False
            for txt in self.ui.CHROME_SKIP_TEXTS:
                if self.robot.d(textContains=txt).exists:
                    self.robot.d(textContains=txt).click()
                    logger.info(f"[{self.serial}] Clicked skip button: {txt}")
                    found_skip = True
                    break
            
            # 4. Thử click theo Resource ID
            for rid in [self.ui.CHROME_ACCEPT_RID, self.ui.CHROME_POSITIVE_RID, self.ui.CHROME_NEGATIVE_RID]:
                if self.robot.d(resourceId=rid).exists:
                    self.robot.d(resourceId=rid).click()
                    found_skip = True

            if not found_skip:
                time.sleep(0.5)
        
        logger.warning(f"[{self.serial}] Hết thời gian chờ Login. Chuyển sang bước tiếp theo...")
        return False
        
    def login(self, email, password):
        """Thực hiện chuỗi đăng nhập. Trả về Structured Result."""
        logger.info(f"[{self.serial}] Đang thực hiện Login cho {email}...")
        
        # 1. Điền thông tin
        if not self.robot.type_smart(email, self.ui.EMAIL_KEYWORDS, fallback_index=0):
            return {"status": "FAIL", "error": "PAGE_NOT_LOADED", "message": "Không tìm thấy ô nhập Email."}
        if not self.robot.type_smart(password, self.ui.PASSWORD_KEYWORDS, fallback_index=1):
            return {"status": "FAIL", "error": "PASSWORD_ERROR", "message": "Không tìm thấy ô nhập Password."}
        
        # 2. Click Login
        for i in range(3):
            self.robot.swipe_up(scale=0.3)
            self.robot.click_smart(self.ui.LOGIN_BTN_IDS, self.ui.LOGIN_BTN_TEXTS)
            
            # Đợi OTP Page xuất hiện
            if self.robot.wait_for_element(text="パスコード", timeout=7):
                logger.info(f"[{self.serial}] Đã chuyển sang màn hình OTP.")
                return {"status": "SUCCESS", "message": "Đã tới màn hình OTP."}
            
            # Kiểm tra xem Login button đã mất chưa
            if not self.robot.d(resourceId="form1Button").exists:
                return {"status": "SUCCESS", "message": "Chuyển màn hình OTP (theo ID)."}
            
            logger.warning(f"[{self.serial}] Login thất bại lần {i+1}. Đang thử lại...")
        
        return {"status": "FAIL", "error": "LOGIN_TIMEOUT", "message": "Hết thời gian chờ Login."}

    def wait_for_otp_screen(self, timeout=15):
        """Chờ cho đến khi màn hình OTP xuất hiện."""
        logger.info(f"[{self.serial}] Đang chờ màn hình nhập OTP (tối đa {timeout}s)...")
        # Chờ xuất hiện chữ "パスコード" (Passcode) hoặc "確認コード" (Confirm code)
        for keyword in ["パスコード", "確認コード", "コードを入力"]:
            if self.robot.wait_for_element(text_contains=keyword, timeout=timeout):
                logger.info(f"[{self.serial}] Đã thấy màn hình OTP.")
                return True
        return False

    def verify_otp(self, code):
        """Xác thực mã OTP."""
        logger.info(f"[{self.serial}] Đang điền OTP: {code}")
        time.sleep(2) 
        
        if not self.robot.type_smart(code, self.ui.OTP_KEYWORDS):
            # Fallback nếu chỉ có 1 ô EditText
            if self.robot.d(className="android.widget.EditText").count == 1:
                self.robot.d(className="android.widget.EditText").set_text(code)
            else:
                return {"status": "FAIL", "error": "OTP_INPUT_NOT_FOUND", "message": "Không tìm thấy ô nhập mã OTP."}
            
        for i in range(2):
            self.robot.swipe_up(scale=0.2)
            self.robot.click_smart(self.ui.VERIFY_BTN_IDS, self.ui.VERIFY_BTN_TEXTS)
            time.sleep(3) # Đợi điều hướng nhẹ
            
            # Chỉ cần click được nút xác thực là coi như xong phần input, 
            # chúng ta sẽ check login thật sự ở bước mở link Chusen.
            logger.info(f"[{self.serial}] Đã bấm nút xác thực OTP.")
            return {"status": "SUCCESS", "message": "Đã bấm xác thực OTP."}
        
        return {"status": "FAIL", "error": "VERIFY_TIMEOUT", "message": "Không bấm được nút xác thực OTP."}

    def lottery_apply(self):
        """Thực hiện nhảy thẳng vào link Chusen và đăng ký."""
        logger.info(f"[{self.serial}] Nhảy thẳng vào trang Chusen: {self.ui.LOTTERY_URL}")
        
        # Mở trực tiếp link trang Lottery list
        self.robot.open_url(self.ui.LOTTERY_URL, incognito=False)
        time.sleep(4)
        
        # 1. Tìm mục Reception (受付中)
        found_item = False
        for _ in range(5):
            if self.robot.d(textContains=self.ui.LOTTERY_STATUS_READY).exists:
                found_item = True; break
            self.robot.swipe_up()
        
        if not found_item:
            return {"status": "SKIP", "message": "Không thấy mặt hàng nào đang '受付中'."}

        # 2. Click Details (詳細を見る)
        self.robot.click_smart(selectors_text=[self.ui.LOTTERY_DETAILS_BTN])
        time.sleep(2)
        
        # 3. Radio & Checkbox
        if self.robot.d(className="android.widget.RadioButton").exists:
            self.robot.d(className="android.widget.RadioButton").click()
        if self.robot.d(className="android.widget.CheckBox").exists:
            self.robot.d(className="android.widget.CheckBox").click()
        
        # 4. Submit Modal
        self.robot.swipe_up()
        self.robot.click_smart(selectors_text=[self.ui.LOTTERY_SUBMIT_MODAL_BTN])
        time.sleep(2)
        
        # 5. Confirm Final
        for _ in range(4):
            if self.robot.click_smart(self.ui.CONFIRM_BTN_IDS, self.ui.CONFIRM_BTN_TEXTS):
                logger.info(f"[{self.serial}] 🎉 Đăng ký Chusen cho tài khoản này THÀNH CÔNG!")
                return {"status": "SUCCESS", "message": "Đã ứng tuyển Chusen thành công."}
            self.robot.swipe_up(scale=0.2)
            
        return {"status": "FAIL", "error": "CONFIRM_FAIL", "message": "Lỗi xác nhận ở bước cuối cùng."}
