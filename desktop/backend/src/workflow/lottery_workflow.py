import time
import logging
from src.utils.config import Config
from src.services.imap_service import get_otp_from_forwarded_mail
from src.core.controller import PokeCenterController

logger = logging.getLogger("LotteryWorkflow")

def run_lottery_workflow(serial, account_info, log_callback=None, stop_check=None):
    """
    Main Business Logic Flow.
    Maintains Business Behavior (Login -> OTP -> Apply).
    Optimized for short-retry (UI) and long-retry (System).
    """
    def _log(msg):
        logger.info(f"[{serial}] {msg}")
        if log_callback: log_callback(serial, msg)

    target_email = account_info['Account_Email']
    password = account_info['Password']
    controller = PokeCenterController(serial)
    
    # Execution Tracking
    for attempt in range(1, Config.MAX_RETRIES + 1):
        # 0. Instant Stop Control
        if stop_check and stop_check():
             _log("🛑 STOP SIGNAL RECEIVED: Aborting workflow.")
             return {"status": "STOPPED", "message": "Manual stop requested"}
             
        # Snapshot current time to avoid picking up old OTPs
        workflow_start_time = time.time()
        
        try:
            _log(f"🚀 --- START FLOW: {target_email} (Attempt {attempt}) ---")
            
            # STEP 1: Launch Browser
            _log("Step 1: Starting browser...")
            if not controller.setup_browser():
                raise Exception("UiError: Browser setup timeout")

            # STEP 2: Login Credentials
            _log("Step 2: Entering credentials...")
            login_res = controller.login(target_email, password)
            if login_res['status'] != "SUCCESS":
                raise Exception(f"LoginError: {login_res['message']}")

            # STEP 3: Wait for OTP Transition
            _log("Step 3: Waiting for OTP screen to load...")
            if not controller.wait_for_otp_screen(timeout=15):
                 raise Exception("UiError: OTP screen didn't appear")

            # STEP 4: Fetch OTP (Explicit parameter passing)
            _log("Step 4: Fetching OTP from master email service...")
            otp_code = get_otp_from_forwarded_mail(
                Config.MASTER_EMAIL, 
                Config.MASTER_PASSWORD, 
                target_email, 
                since_time=workflow_start_time
            )
            if not otp_code:
                raise Exception(f"MailError: OTP not found (Timeout: {Config.OTP_FETCH_TIMEOUT}s)")

            # STEP 5: Verify OTP
            _log(f"Step 5: Code received: {otp_code}. Verifying...")
            otp_res = controller.verify_otp(otp_code)
            if otp_res['status'] != "SUCCESS":
                raise Exception(f"VerifyError: {otp_res['message']}")

            # STEP 6: Execute Apply Flow
            _log("Step 6: Navigating to Chusen registration page...")
            apply_res = controller.lottery_apply()
            
            # STEP 7: Finalize Result
            if apply_res['status'] == "SUCCESS":
                _log("Step 7: 🎉 COMPLETED successfully!")
            elif apply_res['status'] == "SKIP":
                _log("Step 7: ✅ SKIPPED (No matching reception items found)")
            else:
                raise Exception(f"ApplyError: {apply_res['message']}")
                
            return apply_res # SUCCESS: Return to dashboard

        except Exception as e:
            err_msg = str(e)
            _log(f"⚠️ ERROR at Attempt {attempt}: {err_msg}")
            
            # Smart Retry Triggering
            if attempt < Config.MAX_RETRIES:
                # Differentiate sleep based on error type
                if "UiError" in err_msg:
                    wait_time = 2 
                elif "MailError" in err_msg:
                    wait_time = 5
                else: # Default Backoff
                    wait_time = Config.RETRY_DELAY_BASE ** attempt
                
                _log(f"🟠 Retry Triggered: Backoff {wait_time}s...")
                time.sleep(wait_time)
            else:
                _log(f"❌ FAIL: Exhausted {Config.MAX_RETRIES} attempts.")
                return {"status": "FAIL", "message": err_msg, "error": "MAX_RETRY_REACHED"}
    
    return {"status": "FAIL", "message": "Unknown termination", "error": "UNKNOWN"}
