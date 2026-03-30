# Central Selectors for Pokemon Center Online
# Phase 3 Clean Architecture

class PokeCenterUiMap:
    # 1. Login Page & Navigation
    LOGIN_URL = "https://www.pokemoncenter-online.com/login/"
    EMAIL_KEYWORDS = ["email", "mail", "ユーザーID", "ログインID"]
    PASSWORD_KEYWORDS = ["password", "pass", "パスワード"]
    LOGIN_BTN_IDS = ["form1Button"]
    LOGIN_BTN_TEXTS = ["ログイン", "Login", "ログインする"]
    NAVIGATION_LOGIN_TEXTS = ["ログイン / 新규登録", "Login / Register", "ログイン/会員登録"]

    # 2. OTP Page
    OTP_KEYWORDS = ["otp", "code", "mã", "認証番号", "パスコード", "verification", "auth", "数字", "passcode", "authCode", "_ _ _ _ _ _"]
    VERIFY_BTN_IDS = ["authBtn", "verifyBtn", "submitBtn"]
    VERIFY_BTN_TEXTS = ["認証する", "Verify", "OK", "次へ", "送信"]
    OTP_PAGE_INDICATOR = ["認証番号", "OTP", "6桁", "パスコード"]

    # 3. Lottery / Chusen Flow
    LOTTERY_URL = "https://www.pokemoncenter-online.com/lottery/apply.html"
    LOTTERY_PROCEED_BTN = "抽選応募に進む"
    LOTTERY_STATUS_READY = "受付中"
    LOTTERY_DETAILS_BTN = "詳細を見る"
    LOTTERY_SUBMIT_MODAL_BTN = "次へ進む"
    CONFIRM_BTN_IDS = ["submitBtn"]
    CONFIRM_BTN_TEXTS = ["応募する", "Confirm", "Submit"]
    LOGOUT_TEXT = "ログアウト"

    # 4. Browser Onboarding
    CHROME_SKIP_TEXTS = [
        "No thanks", "Không, cảm ơn", "利用しない", "Don't sign in", 
        "Accept & continue", "Chấp nhận và tiếp tục", "同意して続行", "Next", "Tiếp theo", "Continue", "Tiếp tục",
        "Yes, I'm in", "Tôi đồng ý", "はい", "Turn on sync", "Got it", "Hiểu rồi", "了解しました"
    ]
    CHROME_ACCEPT_RID = "com.android.chrome:id/terms_accept"
    CHROME_POSITIVE_RID = "com.android.chrome:id/positive_button"
    CHROME_NEGATIVE_RID = "com.android.chrome:id/negative_button"
