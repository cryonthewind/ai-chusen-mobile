import uiautomator2 as u2
import subprocess
import time
import logging
from src.utils.config import Config

# Cấu hình logging chuyên nghiệp
logger = logging.getLogger("RobotEngine")

class AdbRobot:
    """
    Lớp tương tác ADB cấp thấp (Low-level Driver).
    Refactored cho Clean Architecture Phase 3.
    """
    def __init__(self, serial):
        self.serial = serial
        try:
            self.d = u2.connect(serial)
            logger.info(f"[{serial}] Engine kết nối thành công.")
        except Exception as e:
            logger.error(f"[{serial}] Lỗi kết nối thiết bị qua uiautomator2: {e}")
            raise e

    def wait_for_element(self, text=None, rid=None, timeout=None):
        """Đợi cho đến khi phần tử xuất hiện (Thay thế cho sleep)."""
        timeout = timeout or Config.WAIT_FOR_ELEMENT
        start = time.time()
        while time.time() - start < timeout:
            if text and self.d(textContains=text).exists: return True
            if rid and self.d(resourceId=rid).exists: return True
            # Tự động dọn dẹp các popup cản trở
            if Config.AUTO_AGREE_POPUP:
                self.d(textContains="同意").click_exists(timeout=0.1)
            time.sleep(0.5)
        return False

    def type_smart(self, value, selectors, fallback_index=None):
        """Logic điền text thông minh, đã được tối ưu cho Chrome UI."""
        # Chờ ít nhất 1 ô EditText xuất hiện sau khi trang bắt đầu load
        if not self.wait_for_element(rid="dwfrm_login_username", timeout=7): # Thử chờ ID đặc trưng
             if not self.d(className="android.widget.EditText").exists(timeout=3):
                 logger.error(f"[{self.serial}] Không tìm thấy ô nhập liệu nào.")
                 return False

        inputs = self.d(className="android.widget.EditText")
        valid_fields = []
        # Danh sách ID hệ thống và search bar cần bỏ qua (Chrome & System)
        system_ids = [
            "url_bar", "omnibox", "search_box", "search_src_text", 
            "query_box", "location_bar", "search_bar", "text_bar"
        ]
        
        for f in inputs:
            try:
                info = f.info
                rid = (info.get('resourceName') or "").lower()
                # 1. Bỏ qua nếu ID nằm trong danh sách hệ thống
                if any(k in rid for k in system_ids): continue
                
                # 2. Bỏ qua nếu nằm quá cao (thường là thanh địa chỉ ở top màn hình)
                bounds = info.get('bounds')
                if bounds and bounds['top'] < 250: continue 
                
                valid_fields.append(f)
            except: continue

        if not valid_fields: 
            logger.error(f"[{self.serial}] Không tìm thấy ô nhập liệu hợp lệ (đã lọc bỏ System UI).")
            return False

        # 1. Khớp từ khóa (Text/Hint/Desc)
        for f in valid_fields:
            try:
                info = f.info
                txt, hint, desc = (info.get('text') or "").lower(), (info.get('hint') or "").lower(), (info.get('contentDescription') or "").lower()
                if any(k.lower() in txt or k.lower() in hint or k.lower() in desc for k in selectors):
                    f.set_text(value)
                    return True
            except: continue

        # 2. Cơ chế Fallback duy nhất 1 ô
        if len(valid_fields) == 1:
            valid_fields[0].set_text(value)
            return True

        # 3. Fallback theo index
        if fallback_index is not None and len(valid_fields) > fallback_index:
            valid_fields[fallback_index].set_text(value)
            return True
        
        return False

    def click_smart(self, selectors_id=None, selectors_text=None, use_coordinates=True):
        """Click thông minh (ID, Text, Tọa độ)."""
        target = None
        if selectors_id:
            for rid in selectors_id:
                if self.d(resourceId=rid).exists: target = self.d(resourceId=rid); break
        if not target and selectors_text:
            for txt in selectors_text:
                if self.d(textContains=txt).exists: target = self.d(textContains=txt); break
        
        if target:
            if use_coordinates:
                bounds = target.info.get('bounds')
                if bounds:
                    cx, cy = (bounds['left'] + bounds['right']) // 2, (bounds['top'] + bounds['bottom']) // 2
                    self.d.click(cx, cy)
                    return True
            target.click()
            return True
        return False

    def swipe_up(self, scale=0.4):
        self.d.swipe_ext("up", scale=scale)
        time.sleep(0.5)

    def force_stop_app(self, package=None):
        package = package or Config.CHROME_PACKAGE
        subprocess.run(f"adb -s {self.serial} shell am force-stop {package}", shell=True)

    def open_url(self, url, incognito=None):
        """Mở URL Chrome ẩn danh tiêu chuẩn."""
        incognito = incognito if incognito is not None else Config.INCOGNITO_DEFAULT
        if incognito:
            cmd = f'adb -s {self.serial} shell am start -n {Config.CHROME_PACKAGE}/{Config.CHROME_ACTIVITY} -d "{url}" --ez "com.google.android.apps.chrome.EXTRA_IS_INCOGNITO" true'
        else:
            cmd = f'adb -s {self.serial} shell am start -n {Config.CHROME_PACKAGE}/{Config.CHROME_ACTIVITY} -a android.intent.action.VIEW -d "{url}"'
        subprocess.run(cmd, shell=True)

    def click_if_exists(self, text=None, rid=None):
        if text: self.d(textContains=text).click_exists(timeout=0.2)
        if rid: self.d(resourceId=rid).click_exists(timeout=0.2)

    def toggle_airplane_mode(self):
        """Bật rồi tắt chế độ máy bay để đổi IP mạng 4G."""
        logger.info(f"[{self.serial}] ✈️ Đang thực hiện Reset IP (Airplane Mode)...")
        # Bật
        subprocess.run(f"adb -s {self.serial} shell settings put global airplane_mode_on 1", shell=True)
        subprocess.run(f"adb -s {self.serial} shell am broadcast -a android.intent.action.AIRPLANE_MODE", shell=True)
        time.sleep(3)
        # Tắt
        subprocess.run(f"adb -s {self.serial} shell settings put global airplane_mode_on 0", shell=True)
        subprocess.run(f"adb -s {self.serial} shell am broadcast -a android.intent.action.AIRPLANE_MODE", shell=True)
        time.sleep(5) # Đợi mạng hồi phục
        logger.info(f"[{self.serial}] ✅ Đã Reset IP thành công.")
