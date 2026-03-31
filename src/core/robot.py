import uiautomator2 as u2
import subprocess
import time
import logging
import re
from src.utils.config import Config

logger = logging.getLogger("RobotEngine")

class AdbRobot:
    """
    Low-level ADB Interaction Layer.
    Refactored for maximum speed and stability (Phase 5).
    """
    def __init__(self, serial):
        self.serial = serial
        try:
            self.d = u2.connect(serial)
            # Set shorter default wait for internal u2 operations to speed up .exists
            self.d.wait_timeout = 3.0 
            logger.info(f"[{serial}] Engine connected successfully.")
        except Exception as e:
            logger.error(f"[{serial}] Connection failed: {e}")
            raise e

    def dismiss_popups(self):
        """Quickly dismiss common obstructing popups including Chrome's Save Password."""
        popups = ["同意", "OK", "Chấp nhận", "Accept", "次へ", "Close", "Never", "No thanks", "Không bao giờ", "Lưu mật khẩu"]
        for text in popups:
            target = self.d(textContains=text)
            if target.exists:
                target.click()
                return True
        return False

    def wait_for_element(self, text=None, rid=None, timeout=None, text_contains=None):
        """Wait for search targets with periodic popup dismissal."""
        timeout = timeout or Config.WAIT_FOR_ELEMENT
        start = time.time()
        while time.time() - start < timeout:
            if int(time.time() - start) % 3 == 0:
                self.dismiss_popups()
            if text and self.d(text=text).exists: return True
            if text_contains and self.d(textContains=text_contains).exists: return True
            if rid and self.d(resourceId=rid).exists: return True
            time.sleep(0.3)
        return False

    def wait_for_any(self, selectors, timeout=10):
        """Wait for the first match among multiple selectors."""
        start = time.time()
        while time.time() - start < timeout:
            for s in selectors:
                if 'text' in s and self.d(text=s['text']).exists: return s
                if 'textContains' in s and self.d(textContains=s['textContains']).exists: return s
                if 'rid' in s and self.d(resourceId=s['rid']).exists: return s
            time.sleep(0.5)
        return None

    def get_edit_text_candidates(self):
        """Retrieve EditText inputs, strictly excluding the Top 20% (URL Bar area)."""
        if not self.d(className="android.widget.EditText").exists(timeout=10): 
            return []
            
        inputs = self.d(className="android.widget.EditText")
        candidates = []
        
        # Lấy kích thước màn hình để tính toán vùng chặn
        display = self.d.info
        screen_height = display.get('displayHeight', 2000)
        top_boundary = int(screen_height * 0.15) # Chặn 15% trên cùng (vùng URL)
        if top_boundary < 200: top_boundary = 200

        for i in range(inputs.count):
            try:
                info = inputs[i].info
                bounds = info.get('bounds', {})
                
                # BẮT BUỘC: Loại bỏ bất kỳ thứ gì ở vùng thanh địa chỉ
                if bounds.get('top', 0) < top_boundary: continue
                
                # Lọc ô tàng hình
                width = bounds.get('right', 0) - bounds.get('left', 0)
                height = bounds.get('bottom', 0) - bounds.get('top', 0)
                if width < 10 or height < 10: continue
                
                candidates.append({
                    'x': (bounds['left'] + bounds['right']) // 2,
                    'y': (bounds['top'] + bounds['bottom']) // 2,
                    'obj': inputs[i],
                    'info': info
                })
            except: continue
        return candidates

    def type_smart(self, value, keywords, preferred_ids=None):
        """Clean and Robust Input using FastInput IME and ADB Shell."""
        # Bật bộ gõ siêu tốc để triệt tiêu bàn phím/autofill tự động
        try: self.d.set_fastinput_ime(True)
        except: pass

        def _deep_clear_and_type(x, y, text):
            # 1. Click to focus
            self.d.click(x, y)
            time.sleep(0.3)
            # 2. Triple Clear (Select all + Delete)
            # Move to end, then select all and delete to be 100% clean
            self.d.shell("input keyevent 277") # MOVE_END
            self.d.shell("input keyevent --longpress 67") # Long DEL
            time.sleep(0.2)
            # 3. Direct ADB Input
            # adb input doesn't like special chars well, so prioritize sending characters safely
            self.d.shell(f"input text {text}")
            return True

        # Try match candidates
        candidates = self.get_edit_text_candidates()
        target = None
        
        for item in candidates:
            if preferred_ids and item['info'].get('resourceName') in preferred_ids:
                target = item; break
            search_blob = f"{item['info'].get('text','')} {item['info'].get('hint','')} {item['info'].get('resourceName','')}".lower()
            if any(k.lower() in search_blob for k in keywords):
                target = item; break
        
        if not target and candidates:
            idx = 0 if any(k in ["email", "user", "id"] for k in keywords) else 1
            target = candidates[idx] if len(candidates) > idx else candidates[0]

        if target:
            success = False
            try:
                # Use standard set_text with fast IME
                target['obj'].set_text(value)
                success = True
            except:
                # Last resort fallback if RPC fails
                success = _deep_clear_and_type(target['x'], target['y'], value)
            
            # CRITICAL: Always turn OFF fast input to restore normal UI/Button detection
            try: self.d.set_fastinput_ime(False)
            except: pass
            
            return success
                
        # If no target found, turn off IME anyway
        try: self.d.set_fastinput_ime(False)
        except: pass
        return False

    def click_smart(self, ids=None, texts=None):
        """Directly click with short-circuit logic."""
        if ids:
            for rid in ids:
                target = self.d(resourceId=rid)
                if target.exists:
                    target.click()
                    return True
        if texts:
            for txt in texts:
                target = self.d(textContains=txt)
                if target.exists:
                    target.click()
                    return True
        return False

    def swipe_up(self, scale=0.4):
        self.d.swipe_ext("up", scale=scale)
        time.sleep(0.3)

    def force_stop_app(self, package=None):
        package = package or Config.CHROME_PACKAGE
        subprocess.run(f"adb -s {self.serial} shell am force-stop {package}", shell=True)

    def open_url(self, url, incognito=True):
        """Starts Chrome with direct URL."""
        if incognito:
            cmd = f'adb -s {self.serial} shell am start -n {Config.CHROME_PACKAGE}/{Config.CHROME_ACTIVITY} -d "{url}" --ez "com.google.android.apps.chrome.EXTRA_IS_INCOGNITO" true'
        else:
            cmd = f'adb -s {self.serial} shell am start -n {Config.CHROME_PACKAGE}/{Config.CHROME_ACTIVITY} -a android.intent.action.VIEW -d "{url}"'
        subprocess.run(cmd, shell=True)

    def toggle_airplane_mode(self, log_callback=None):
        """Robust IP reset: Airplane Mode with guaranteed recovery and svc fallback."""
        def _log(msg):
            logger.info(f"[{self.serial}] {msg}")
            if log_callback:
                log_callback(self.serial, msg)

        def _run_cmd(cmd):
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return res.returncode == 0, res.stderr.strip() if res.stderr else res.stdout.strip()

        _log("⚡ Starting IP Reset (Airplane Toggle Strategy)...")
        
        try:
            # 1. ATTEMPT ON
            _log("Step 1: Turning Airplane Mode ON...")
            _run_cmd(f"adb -s {self.serial} shell settings put global airplane_mode_on 1")
            success_on, _ = _run_cmd(f"adb -s {self.serial} shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true")
            
            _log("   > Waiting 3s for signal drop...")
            time.sleep(3)
            
            # 2. ATTEMPT OFF (Always run this)
            _log("Step 2: Turning Airplane Mode OFF...")
            _run_cmd(f"adb -s {self.serial} shell settings put global airplane_mode_on 0")
            success_off, err = _run_cmd(f"adb -s {self.serial} shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false")
            
            # 3. VERIFY & FALLBACK
            if not success_on or not success_off:
                _log("⚠️ Broadcast restricted. Radio might not toggle correctly. Triggering 'svc' backup...")
                _log("Step 3: Cycling Mobile Data (svc)...")
                _run_cmd(f"adb -s {self.serial} shell svc data disable")
                time.sleep(2)
                _run_cmd(f"adb -s {self.serial} shell svc data enable")
            
            _log("Step 4: Cooling down for network stabilization...")
            time.sleep(4)
            _log("✅ IP Reset Sequence Finished.")
            
        except Exception as e:
            _log(f"❌ IP Reset Error: {str(e)}")
            # Safety exit: ensure we try to turn off airplane mode one last time
            _run_cmd(f"adb -s {self.serial} shell settings put global airplane_mode_on 0")




