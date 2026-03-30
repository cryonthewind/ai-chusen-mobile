import time
import logging
from src.utils.config import Config
from src.services.imap_service import get_otp_from_forwarded_mail
from src.core.controller import PokeCenterController

# Cấu hình logging chuyên nghiệp
logger = logging.getLogger("LotteryWorkflow")

def run_lottery_workflow(serial, account_info, log_callback=None):
    """
    Kịch bản nghiệp vụ Đăng ký Chusen (Lottery) với 7 bước chi tiết.
    """
    def _log(msg):
        logger.info(f"[{serial}] {msg}")
        if log_callback: log_callback(serial, msg)

    target_email = account_info['Account_Email']
    password = account_info['Password']
    controller = PokeCenterController(serial)
    
    _log(f"🚀 --- START FLOW: {target_email} ---")
    
    # STEP 1: Khởi động Chrome
    _log("Step 1: Đang khởi động trình duyệt Chrome...")
    if not controller.setup_browser():
        return {"status": "FAIL", "error": "SETUP_FAIL", "message": "Không vào được trang Login."}

    # STEP 2: Điền thông tin Login
    _log("Step 2: Đang điền Email & Mật khẩu...")
    login_res = controller.login(target_email, password)
    if login_res['status'] != "SUCCESS":
        _log(f"Step 2: ❌ LỖI: {login_res['message']}")
        return login_res

    # STEP 3: Chờ chuyển sang trang OTP
    _log("Step 3: Đang đợi màn hình mã OTP xuất hiện...")
    time.sleep(2)

    # STEP 4: Lấy OTP từ Email
    _log("Step 4: Đang quét Email Master để lấy mã OTP...")
    otp_code = get_otp_from_forwarded_mail(Config.MASTER_EMAIL, Config.MASTER_PASSWORD, target_email)
    if not otp_code:
        _log("Step 4: ❌ LỖI: Không lấy được OTP.")
        return {"status": "FAIL", "error": "OTP_NOT_FOUND", "message": "Không tìm thấy OTP trong Email."}

    # STEP 5: Xác thực OTP
    _log(f"Step 5: Đã lấy mã {otp_code}. Đang tiến hành xác thực...")
    otp_res = controller.verify_otp(otp_code)
    if otp_res['status'] != "SUCCESS":
        _log(f"Step 5: ❌ LỖI: {otp_res['message']}")
        return otp_res

    # STEP 6: Vào trang đăng ký (Lottery)
    _log("Step 6: Đang tìm và truy cập mục ứng tuyển Chusen...")
    # Thêm logic click nút ứng tuyển nếu chưa ở trang này
    apply_res = controller.lottery_apply()
    
    # STEP 7: Hoàn tất chốt đơn
    if apply_res['status'] == "SUCCESS":
        _log("Step 7: 🎉 HOÀN TẤT: Đăng ký Chusen thành công!")
    elif apply_res['status'] == "SKIP":
        _log("Step 7: ✅ SKIP: Tạm thời không có mặt hàng nào '受付中'.")
    else:
        _log(f"Step 7: ❌ LỖI: {apply_res['message']}")
        
    return apply_res
