import os
from dotenv import load_dotenv

# Tải cấu hình từ .env
load_dotenv()

class Config:
    """
    Cấu hình tập trung cho toàn bộ hệ thống Pokemon Center Automation.
    """
    # 1. Credentials (MASTER)
    MASTER_EMAIL = os.getenv("MASTER_EMAIL", "tranquoctoan31892@gmail.com")
    MASTER_PASSWORD = os.getenv("MASTER_PASSWORD", "")

    # 2. Chrome / Android Settings
    CHROME_PACKAGE = "com.android.chrome"
    CHROME_ACTIVITY = "com.google.android.apps.chrome.Main"
    
    # 3. URLs
    BASE_URL = "https://www.pokemoncenter-online.com/"
    LOGIN_URL = "https://www.pokemoncenter-online.com/?main_page=login"
    
    # 4. Timeouts & Delays (Seconds)
    DEFAULT_TIMEOUT = 12
    WAIT_FOR_ELEMENT = 20
    OTP_FETCH_TIMEOUT = 120
    WAIT_BETWEEN_ACCOUNTS = 15
    
    # 5. Retry & Backoff (Phase 4)
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # sleep(base ** retry_count)
    
    # 6. Business logic flags
    INCOGNITO_DEFAULT = True
    AUTO_AGREE_POPUP = True
    AIRPLANE_MODE_EVERY = 10 # Tự động đổi IP sau mỗi 10 acc
