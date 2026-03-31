import imaplib
import email
import re
import time
import logging
from datetime import datetime
from email.header import decode_header
from src.utils.config import Config

logger = logging.getLogger("ImapService")

def get_otp_from_forwarded_mail(master_email, master_password, target_email, timeout_sec=None, since_time=None):
    """
    Restored Working Logic with Read-Mail Support:
    1. Restore original simple UNSEEN-based logic style.
    2. Change UNSEEN to ALL to avoid 'Already Read' trap.
    3. Proper character decoding for Subject and Body.
    """
    timeout_sec = timeout_sec or Config.OTP_FETCH_TIMEOUT
    start_time = time.time()
    logger.info(f"🚀 [RESTORED] Waiting for OTP: {target_email} in {master_email}...")

    while time.time() - start_time < timeout_sec:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(master_email, master_password)
            mail.select("inbox")

            # Tìm 20 mail mới nhất (không phân biệt Đã đọc hay chưa để tránh kẹt)
            status, messages = mail.search(None, "ALL")
            if status != "OK" or not messages[0]:
                mail.logout()
                time.sleep(3)
                continue

            msg_ids = messages[0].split()[-20:][::-1] # 20 cái mới nhất, đảo ngược thứ tự
            
            for msg_id in msg_ids:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK": continue
                
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # A. Decode Subject
                subject_header = msg.get("Subject")
                subject = ""
                if subject_header:
                    decoded = decode_header(subject_header)[0]
                    subject = str(decoded[0].decode(decoded[1] if decoded[1] else "utf-8", errors="ignore") if isinstance(decoded[0], bytes) else decoded[0])
                
                # B. Extract Content
                to_header = str(msg.get("To", "")).lower()
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() in ["text/plain", "text/html"]:
                            try:
                                body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            except:
                                body += part.get_payload(decode=True).decode('iso-2022-jp', errors='ignore')
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        body = msg.get_payload(decode=True).decode('iso-2022-jp', errors='ignore')

                # C. Check Pokemon & Account Match
                is_pokemon = "ポケモン" in subject or "パスコード" in subject
                is_account = target_email.lower() in to_header or target_email.lower() in body.lower()

                if is_pokemon and is_account:
                    otp_match = re.search(r'(\d{6})', body)
                    if otp_match:
                        otp_code = otp_match.group(1)
                        logger.info(f"✅ FOUND OTP: {otp_code} for {target_email} (ID: {msg_id})")
                        mail.logout()
                        return otp_code

            mail.logout()
        except Exception as e:
            logger.error(f"IMAP_SVC_ERROR: {e}")
            
        time.sleep(3) # Retry after 3s
        
    return None
