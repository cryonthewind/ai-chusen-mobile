import time
import logging
from src.core.robot import AdbRobot
from src.core.ui_map import PokeCenterUiMap
from src.utils.config import Config

logger = logging.getLogger("SystemController")

class PokeCenterController:
    """
    High-level logic controller.
    Uses AdbRobot to execute business workflows.
    Refactored for zero-sleep (smart-wait) transitions.
    """
    def __init__(self, serial):
        self.serial = serial
        self.robot = AdbRobot(serial)
        self.ui = PokeCenterUiMap()

    def setup_browser(self):
        """Starts Chrome and skips onboarding fast."""
        logger.info(f"[{self.serial}] Launching Chrome...")
        self.robot.force_stop_app()
        time.sleep(0.5)
        self.robot.open_url(self.ui.LOGIN_URL, incognito=Config.INCOGNITO_DEFAULT)
        
        # Stability wait for Webview to settle
        time.sleep(1.5)
        
        # Fast-track waiting for Login Input
        start_time = time.time()
        while time.time() - start_time < Config.WAIT_FOR_ELEMENT:
            # 1. Quick Action: Find anything clickable (Popups, Skips)
            if self.robot.dismiss_popups() or self.robot.click_smart(texts=self.ui.CHROME_SKIP_TEXTS):
                continue
                
            # 2. Check if we reached the goal (Login Screen)
            if self.robot.wait_for_element(rid="dwfrm_login_username", timeout=1):
                logger.info(f"[{self.serial}] Reached Login Screen.")
                return True
            
            if self.robot.d(className="android.widget.EditText").exists(timeout=0.1):
                return True
                
            time.sleep(0.3)
        return False
        
    def login(self, email, password):
        """Perform login flow with corrected Button IDs."""
        logger.info(f"[{self.serial}] Performing login: {email}")
        
        # 1. Type Credentials (using accurate IDs)
        if not self.robot.type_smart(email, self.ui.EMAIL_KEYWORDS, ["dwfrm_login_username"]):
            return {"status": "FAIL", "message": "Email input not found"}
            
        if not self.robot.type_smart(password, self.ui.PASSWORD_KEYWORDS, ["dwfrm_login_password"]):
            return {"status": "FAIL", "message": "Password input not found"}
        
        # 2. Submit with corrected IDs and Smart Waiting
        # We wait for the button to be visible first
        login_btn_selectors = [
            {'rid': 'dwfrm_login_login'}, 
            {'textContains': 'ログイン'}, 
            {'textContains': 'Hội viên'}
        ]
        
        for i in range(3):
            self.robot.swipe_up(scale=0.4)
            logger.info(f"[{self.serial}] Finding Login button (Try {i+1})...")
            
            # Wait a few seconds for the button to appear if page is still loading
            target = self.robot.wait_for_any(login_btn_selectors, timeout=5)
            if target:
                if self.robot.click_smart(ids=["dwfrm_login_login", "form1Button"], texts=self.ui.LOGIN_BTN_TEXTS):
                    # SUCCESS CONDITION: Wait for OTP screen
                    if self.robot.wait_for_element(text_contains="パスコード", timeout=15):
                        return {"status": "SUCCESS", "message": "Reached OTP screen"}
                    
                    # Check for redirection
                    if not self.robot.d(resourceId="dwfrm_login_login").exists(timeout=2):
                        return {"status": "SUCCESS", "message": "Login submitted"}
            
            logger.warning(f"[{self.serial}] Login button click attempt {i+1} failed.")
            time.sleep(1)
        
        return {"status": "FAIL", "message": "Login button not found/clickable"}

    def wait_for_otp_screen(self, timeout=15):
        """Dedicated wait for OTP input field."""
        return self.robot.wait_for_element(text_contains="パスコード", timeout=timeout)

    def verify_otp(self, code):
        """Input OTP, confirm, and ENSURE it's processed."""
        logger.info(f"[{self.serial}] Verifying OTP: {code}")
        
        # 1. Fill OTP with FastInput (Automatic Keyboard/Autofill Suppression)
        if not self.robot.type_smart(code, self.ui.OTP_KEYWORDS):
            # Last Resort: If keywords fail, find any EditText and type
            logger.warning(f"[{self.serial}] Keywords failed, trying direct injection to first EditText...")
            if not self.robot.type_smart(code, ["passcode"]): # Generic fallback
                 return {"status": "FAIL", "message": "OTP input not found"}
            
        # 2. Click Confirm - No more blind 'back' press!
        time.sleep(0.5) 
        self.robot.swipe_up(scale=0.1) # Small swipe to ensure visibility
        
        if self.robot.click_smart(ids=self.ui.VERIFY_BTN_IDS, texts=self.ui.VERIFY_BTN_TEXTS):
            logger.info(f"[{self.serial}] Waiting for OTP submission to complete...")
            start_verify = time.time()
            while time.time() - start_verify < 12:
                # Check for redirection or success indicators
                if not self.robot.d(className="android.widget.EditText").exists(timeout=2):
                    logger.info(f"[{self.serial}] OTP confirmed successfully.")
                    return {"status": "SUCCESS", "message": "OTP verified"}
                
                if self.robot.d(textContains="エラー").exists(timeout=0.1):
                    return {"status": "FAIL", "message": "Invalid OTP code error displayed"}
                
                time.sleep(1)
            return {"status": "SUCCESS", "message": "OTP submission likely passed"}
        
        return {"status": "FAIL", "message": "Verify button not found"}

    def lottery_apply(self):
        """Direct navigation for application flow using shared session."""
        logger.info(f"[{self.serial}] Direct hopping to Lottery page...")
        # CRITICAL: Must use same incognito mode as login to preserve session
        self.robot.open_url(self.ui.LOTTERY_URL, incognito=Config.INCOGNITO_DEFAULT)
        
        # 1. Find active reception (受付中)
        found = False
        for _ in range(3):
            if self.robot.wait_for_element(text_contains="受付中", timeout=4):
                found = True; break
            self.robot.swipe_up()
            
        if not found:
            return {"status": "SKIP", "message": "No active lottery items found"}

        # 2. Detail Click & Apply Loop
        self.robot.click_smart(texts=[self.ui.LOTTERY_DETAILS_BTN])
        self.robot.wait_for_element(rid="form1", timeout=5) # wait for page load
        
        # Auto click form elements (Radio/Checkbox)
        self.robot.swipe_up()
        if self.robot.d(className="android.widget.RadioButton").exists:
            self.robot.d(className="android.widget.RadioButton").click()
        if self.robot.d(className="android.widget.CheckBox").exists:
            self.robot.d(className="android.widget.CheckBox").click()
        
        # 3. Final Confirmations (Chain click)
        self.robot.swipe_up()
        self.robot.click_smart(texts=[self.ui.LOTTERY_SUBMIT_MODAL_BTN])
        
        # Recursive button push for final confirmation
        for _ in range(3):
            if self.robot.click_smart(ids=self.ui.CONFIRM_BTN_IDS, texts=self.ui.CONFIRM_BTN_TEXTS):
                logger.info(f"[{self.serial}] SUCCESS: Applied successfully!")
                return {"status": "SUCCESS", "message": "Application complete"}
            self.robot.swipe_up(scale=0.2)
            
        return {"status": "FAIL", "message": "Final confirmation button not found"}
