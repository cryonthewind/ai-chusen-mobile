import csv
import time
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from src.core.robot import AdbRobot
from src.workflow.lottery_workflow import run_lottery_workflow as run_workflow_for_account
import subprocess

# Cấu hình biến môi trường
load_dotenv()

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s')
logger = logging.getLogger("MainScheduler")

def list_devices():
    """Lấy danh sách các serial ID của thiết bị Android đang kết nối."""
    try:
        output = subprocess.check_output("adb devices", shell=True).decode()
        lines = output.splitlines()
        serials = []
        for line in lines[1:]:
            if "device" in line and not "devices" in line:
                serials.append(line.split()[0])
        return serials
    except:
        return []

def worker_task(serial, account_queue):
    """Function cho 1 Thread quản lý 1 Device."""
    while account_queue:
        try:
            # Lấy account từ queue (Pop đầu tiên)
            account = account_queue.pop(0)
            target_email = account['Account_Email']
            
            logger.info(f"💎 Device [{serial}] đang bắt đầu xử lý: {target_email}")
            
            # Thực thi workflow
            res = run_workflow_for_account(serial, account)
            
            # Kết quả: Bạn có thể cập nhật CSV ở đây nếu cần tập trung
            if res['status'] == "SUCCESS":
                logger.info(f"✅ Device [{serial}] hoàn tất THÀNH CÔNG: {target_email}")
            else:
                logger.error(f"❌ Device [{serial}] THẤT BẠI cho {target_email}: {res['message']}")
            
            # Nghỉ ngắn giữa các acc để tránh bot detection
            time.sleep(10)
        except IndexError:
            break
        except Exception as e:
            logger.error(f"💥 Lỗi nghiêm trọng tại worker [{serial}]: {e}")
            break

def main():
    logger.info("🚀 Đang khởi động Pokemon Center Multi-Device Scheduler...")
    
    # 1. Quét thiết bị
    serials = list_devices()
    if not serials: 
        logger.error("Không tìm thấy thiết bị Android nào đang kết nối ADB.")
        return

    logger.info(f"📱 Tìm thấy {len(serials)} thiết bị: {serials}")

    # 2. Load danh sách tài khoản hợp lệ (Status = ready)
    if not os.path.exists('accounts_template.csv'):
        logger.error("Không tìm thấy file accounts_template.csv")
        return

    accounts_to_run = []
    with open('accounts_template.csv', mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Status') == 'ready':
                accounts_to_run.append(row)

    if not accounts_to_run:
        logger.warning("Không có tài khoản nào có trạng thái 'ready' để chạy.")
        return

    logger.info(f"📦 Đang xếp hàng {len(accounts_to_run)} tài khoản vào Queue.")

    # 3. Khởi chạy luồng song song (Mỗi device dùng 1 Thread)
    # Dùng ThreadPoolExecutor với max_workers = số lượng device
    with ThreadPoolExecutor(max_workers=len(serials), thread_name_prefix="Worker") as executor:
        for serial in serials:
            executor.submit(worker_task, serial, accounts_to_run)

    logger.info("🏁 TẤT CẢ CÔNG VIỆC ĐÃ HOÀN TẤT.")

if __name__ == "__main__":
    main()
