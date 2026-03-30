import imaplib
import email
import re
import time
import logging
from email.header import decode_header
from src.utils.config import Config

logger = logging.getLogger("OTPHelper")

def get_otp_from_forwarded_mail(master_email, master_password, target_email, timeout_sec=None):
    """
    Tìm mã OTP cho target_email trong master mailbox.
    Refactored: Dùng (UNSEEN) để tối đa hóa tốc độ lọc mail.
    """
    timeout_sec = timeout_sec or Config.OTP_FETCH_TIMEOUT
    logger.info(f"Đang chờ mã OTP cho: {target_email}")
    
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            # Login IMAP
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(master_email, master_password)
            mail.select("inbox")

            # CHỈ TÌM EMAIL CHƯA ĐỌC (UNSEEN)
            status, messages = mail.search(None, '(UNSEEN)')
            if status != 'OK' or not messages[0]:
                mail.logout()
                time.sleep(5)
                continue

            msg_ids = messages[0].split()[::-1]
            for msg_id in msg_ids:
                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject
                        subject = ""
                        subject_header = msg.get("Subject")
                        if subject_header:
                            decoded = decode_header(subject_header)[0]
                            subject = str(decoded[0].decode(decoded[1] if decoded[1] else "utf-8", errors="ignore") if isinstance(decoded[0], bytes) else decoded[0])
                        
                        # Decode recipient
                        to_header = str(msg.get("To", "")).lower()
                        
                        body_plain = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body_plain = part.get_payload(decode=True).decode(errors="ignore")
                        else:
                            body_plain = msg.get_payload(decode=True).decode(errors="ignore")

                        # LOGIC: Kiểm tra mail Pokemon Center và chứa account target
                        is_pokemon = "ポケモン" in subject or "パスコード" in subject
                        is_account = target_email.lower() in to_header or target_email.lower() in body_plain.lower()

                        if is_pokemon and is_account:
                            # Trích xuất mã 6 số
                            otp_match = re.search(r'(\d{6})', body_plain)
                            if otp_match:
                                otp_code = otp_match.group(1)
                                logger.info(f"✅ Tìm thấy mã OTP: {otp_code} cho {target_email}")
                                
                                # Đánh dấu đã đọc
                                mail.store(msg_id, '+FLAGS', '\\Seen')
                                mail.logout()
                                return otp_code
            
            mail.logout()
        except Exception as e:
            logger.error(f"Lỗi IMAP: {e}")
        
        time.sleep(10)
    
    return None
