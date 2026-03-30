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
    WAIT_FOR_ELEMENT = 15
    OTP_FETCH_TIMEOUT = 120
    WAIT_BETWEEN_ACCOUNTS = 10
    
    # 5. Business logic flags
    INCOGNITO_DEFAULT = True
    AUTO_AGREE_POPUP = True
