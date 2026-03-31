import csv
import time
import os
import logging
import threading
import subprocess
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from src.workflow.lottery_workflow import run_lottery_workflow

# 1. Environment & Global Configuration
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s')
logger = logging.getLogger("MainScheduler")

# Global lock for thread-safe account popping
queue_lock = threading.Lock()

def list_devices():
    """Retrieves list of connected Android serial IDs via ADB."""
    try:
        output = subprocess.check_output("adb devices", shell=True).decode()
        lines = output.splitlines()
        serials = [line.split()[0] for line in lines[1:] if "device" in line and not "devices" in line]
        return serials
    except Exception as e:
        logger.error(f"ADB Error: {e}")
        return []

def worker_task(serial, account_deque):
    """Worker thread logic: One device per thread."""
    logger.info(f"💎 Initializing worker for Node [{serial}]")
    
    while True:
        # Step A: Thread-safe pop from deque
        account = None
        with queue_lock:
            if account_deque:
                account = account_deque.popleft()
        
        if not account:
            logger.info(f"🏁 Node [{serial}]: Queue cleared. Shutting down worker.")
            break

        target_email = account.get('Account_Email', 'Unknown')
        
        try:
            logger.info(f"⚡ Node [{serial}] -> Processing: {target_email}")
            
            # Step B: Execute the core business workflow
            # We pass a simple log callback to show progress in console
            def _log_cb(sn, msg): logger.info(f"[{sn}] {msg}")
            
            res = run_lottery_workflow(serial, account, log_callback=_log_cb)
            
            # Step C: Result handling
            if res['status'] == "SUCCESS":
                logger.info(f"✅ Node [{serial}] -> SUCCESS: {target_email}")
            elif res['status'] == "SKIP":
                logger.info(f"✅ Node [{serial}] -> SKIPPED: {target_email}")
            else:
                logger.error(f"❌ Node [{serial}] -> FAILED: {target_email} - Error: {res.get('message')}")
            
            # Anti-detection delay between accounts
            time.sleep(5) 
            
        except Exception as e:
            logger.error(f"💥 Node [{serial}] -> CRITICAL ERROR during {target_email}: {e}")
            # Potentially put account back or mark as error
            continue

def main():
    logger.info("🚀 Starting Pokemon Center Multi-Device Scheduler (Refactored)...")
    
    # 1. Device Discovery
    serials = list_devices()
    if not serials: 
        logger.error("No ADB devices detected. Please connect devices via USB/Network.")
        return

    logger.info(f"📱 Nodes Online ({len(serials)}): {serials}")

    # 2. Account Loading (Status: ready)
    csv_path = 'accounts_template.csv'
    if not os.path.exists(csv_path):
        logger.error(f"Target file {csv_path} not found.")
        return

    accounts_to_run = []
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            accounts_to_run = [row for row in reader if row.get('Status') == 'ready']
    except Exception as e:
        logger.error(f"CSV Read Error: {e}")
        return

    if not accounts_to_run:
        logger.warning("No 'ready' accounts found in queue.")
        return

    # Convert to thread-safe deque
    account_queue = deque(accounts_to_run)
    logger.info(f"📦 Queued {len(account_queue)} accounts for processing.")

    # 3. Parallel Execution Management
    # One thread per device to isolate execution logic
    with ThreadPoolExecutor(max_workers=len(serials), thread_name_prefix="Node") as executor:
        for serial in serials:
            executor.submit(worker_task, serial, account_queue)

    logger.info("🏁 MISSION COMPLETE: All nodes returned successfully.")

if __name__ == "__main__":
    main()
