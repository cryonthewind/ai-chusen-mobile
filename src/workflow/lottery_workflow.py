import time
import logging
from src.utils.config import Config
from src.services.imap_service import get_otp_from_forwarded_mail
from src.core.controller import PokeCenterController

# Cấu hình logging chuyên nghiệp
logger = logging.getLogger("LotteryWorkflow")

def run_lottery_workflow(serial, account_info, log_callback=None, stop_check=None):
    """
    Kịch bản nghiệp vụ Đăng ký Chusen với cơ chế TỰ ĐỘNG THỬ LẠI (Phase 4).
    """
    def _log(msg):
        logger.info(f"[{serial}] {msg}")
        if log_callback: log_callback(serial, msg)

    target_email = account_info['Account_Email']
    password = account_info['Password']
    controller = PokeCenterController(serial)
    
    # --- Vòng lặp RETRY chuẩn DevOps ---
    for attempt in range(1, Config.MAX_RETRIES + 1):
        if stop_check and stop_check():
             _log("🛑 HỆ THỐNG YÊU CẦU DỪNG. Đang ngắt tiến trình...")
             return {"status": "STOPPED", "message": "Manual stop requested"}
             
        workflow_start_time = time.time() # Cập nhật mốc thời gian cho mỗi lần thử
        try:
            _log(f"🚀 --- START FLOW: {target_email} (Lần thử {attempt}) ---")
            
            # STEP 1: Khởi động Chrome
            _log("Step 1: Đang khởi động trình duyệt Chrome...")
            if not controller.setup_browser():
                raise Exception("Không vào được trang Login.")

            # STEP 2: Điền thông tin Login
            _log("Step 2: Đang điền Email & Mật khẩu...")
            login_res = controller.login(target_email, password)
            if login_res['status'] != "SUCCESS":
                raise Exception(login_res['message'])

            # STEP 3: Chờ chuyển sang trang OTP
            _log("Step 3: Đang đợi màn hình mã OTP xuất hiện...")
            if not controller.wait_for_otp_screen(timeout=15):
                 raise Exception("Không thấy màn hình nhập mã OTP (Login có thể đã thất bại hoặc mạng chậm).")

            # STEP 4: Lấy OTP từ Email
            _log("Step 4: Đang quét Email Master để lấy mã OTP...")
            otp_code = get_otp_from_forwarded_mail(Config.MASTER_EMAIL, Config.MASTER_PASSWORD, target_email, since_time=workflow_start_time)
            if not otp_code:
                raise Exception("Không lấy được mã OTP từ Email.")

            # STEP 5: Xác thực OTP
            _log(f"Step 5: Đã lấy mã {otp_code}. Đang tiến hành xác thực...")
            otp_res = controller.verify_otp(otp_code)
            if otp_res['status'] != "SUCCESS":
                raise Exception(otp_res['message'])

            # STEP 6: Vào trang đăng ký (Lottery)
            _log("Step 6: Đang thực hiện đăng ký Chusen (apply.html)...")
            apply_res = controller.lottery_apply()
            
            # STEP 7: Hoàn tất chốt đơn
            if apply_res['status'] == "SUCCESS":
                _log("Step 7: 🎉 HOÀN TẤT: Đăng ký thành công!")
            elif apply_res['status'] == "SKIP":
                _log("Step 7: ✅ SKIP: Không có mặt hàng '受付中'.")
            else:
                raise Exception(apply_res['message'])
                
            return apply_res # Thành công thì thoát luôn

        except Exception as e:
            _log(f"⚠️ LỖI tại lần thử {attempt}: {e}")
            if attempt < Config.MAX_RETRIES:
                wait_time = Config.RETRY_DELAY_BASE ** attempt
                _log(f"🟠 Đang tiến hành Backoff ({wait_time}s) để thử lại...")
                time.sleep(wait_time)
            else:
                _log(f"❌ THẤT BẠI sau {Config.MAX_RETRIES} lần thử.")
                return {"status": "FAIL", "message": str(e), "error": "MAX_RETRY_REACHED"}
    
    return {"status": "FAIL", "message": "Unknown error", "error": "UNKNOWN"}
