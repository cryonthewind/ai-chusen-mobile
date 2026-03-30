import imaplib
import email
import re
import time
import logging
from email.header import decode_header
from src.utils.config import Config

logger = logging.getLogger("OTPHelper")

from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

def get_otp_from_forwarded_mail(master_email, master_password, target_email, timeout_sec=None, since_time=None):
    """
    Tìm mã OTP cho target_email trong master mailbox.
    since_time: Mốc thời gian (unix timestamp) để bỏ qua các email cũ.
    """
    timeout_sec = timeout_sec or Config.OTP_FETCH_TIMEOUT
    logger.info(f"Đang chờ mã OTP cho: {target_email} - Since: {time.ctime(since_time) if since_time else 'Any'}")
    
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
                        
                        # 1. Kiểm tra thời gian gửi (Date Header)
                        date_str = msg.get("Date")
                        if since_time and date_str:
                            email_dt = parsedate_to_datetime(date_str)
                            email_ts = email_dt.timestamp()
                            # Chấp nhận email trong vòng 2 phút trước mốc bắt đầu (đề phòng lệch giờ server)
                            if email_ts < (since_time - 120): 
                                continue

                        # 2. Decode subject
                        subject = ""
                        subject_header = msg.get("Subject")
                        if subject_header:
                            decoded = decode_header(subject_header)[0]
                            subject = str(decoded[0].decode(decoded[1] if decoded[1] else "utf-8", errors="ignore") if isinstance(decoded[0], bytes) else decoded[0])
                        
                        # 3. Recipient & Content
                        to_header = str(msg.get("To", "")).lower()
                        body_plain = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body_plain = part.get_payload(decode=True).decode(errors="ignore")
                        else:
                            body_plain = msg.get_payload(decode=True).decode(errors="ignore")

                        # LOGIC: Check Pokemon Center & Target Email
                        is_pokemon = "ポケモン" in subject or "パスコード" in subject
                        is_account = target_email.lower() in to_header or target_email.lower() in body_plain.lower()

                        if is_pokemon and is_account:
                            otp_match = re.search(r'(\d{6})', body_plain)
                            if otp_match:
                                otp_code = otp_match.group(1)
                                logger.info(f"✅ FOUND OTP: {otp_code} for {target_email}")
                                mail.store(msg_id, '+FLAGS', '\\Seen')
                                mail.logout()
                                return otp_code
            
            mail.logout()
        except Exception as e:
            logger.error(f"IMAP_SVC_ERROR: {e}")
        
        time.sleep(5) # Quét nhanh hơn
    
    return None
