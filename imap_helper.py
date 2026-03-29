import imaplib
import email
import re
import time
from email.header import decode_header

def get_otp_from_forwarded_mail(master_email, master_password, target_email, timeout_sec=120):
    """
    Polling Gmail master mailbox to find OTP for the target_email.
    Lấy mã 6 số từ email có chủ đề hoặc nội dung liên quan đến Pokemon Center.
    """
    print(f"[OTP Central] Tìm mã OTP cho {target_email} trong {master_email}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            # Connect to IMAP
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(master_email, master_password)
            mail.select("inbox")

            # Tìm các email liên quan đến Pokemon trong vòng 1-2 ngày qua cho nhanh
            # Hoặc dùng ALL để bao quát hơn (trong trường hợp mail bị đánh dấu read rồi)
            status, messages = mail.search(None, 'ALL')
            if status != 'OK' or not messages[0]:
                mail.logout()
                time.sleep(5)
                continue

            # Duyệt từ mới nhất đến cũ nhất
            msg_ids = messages[0].split()[::-1][:20] # Chỉ lấy 20 email gần nhất để tối ưu
            for msg_id in msg_ids:
                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject
                        subject_header = msg.get("Subject")
                        if subject_header:
                            subject, encoding = decode_header(subject_header)[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                        else:
                            subject = ""
                        
                        # Decode recipient
                        to_header = str(msg.get("To", "")).lower()
                        
                        body_plain = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body_plain = part.get_payload(decode=True).decode(errors="ignore")
                        else:
                            body_plain = msg.get_payload(decode=True).decode(errors="ignore")

                        # LOG: Kiểm tra xem email có liên quan ko (Pokemon và đúng account)
                        is_pokemon = "ポケモン" in subject or "パスコード" in subject
                        target_short = target_email.split('@')[0].lower()
                        
                        # Match nếu target_email nằm trong To header HOẶC Body
                        is_correct_account = (
                            target_email.lower() in to_header or 
                            target_email.lower() in body_plain.lower() or 
                            target_short in body_plain.lower()
                        )

                        if is_pokemon:
                            # Tìm mã 6 chữ số
                            otp_match = re.search(r'(\d{6})', body_plain)
                            if otp_match:
                                if is_correct_account:
                                    print(f"[OTP Central] ✅ Found match for {target_email} (Matched in To: {to_header if target_email in to_header else 'Body'})")
                                    mail.logout()
                                    return otp_match.group(1)
                                else:
                                    print(f"[OTP Central] ⚠️ Mail Pokemon detect (OTP {otp_match.group(1)}) nhưng ko match account '{target_email}'. Skiping...")
            
            mail.logout()
        except Exception as e:
            print(f"[OTP Central] Connection Error: {e}")
        
        time.sleep(10)
    
    print(f"[OTP Central] ❌ Timeout: Không tìm thấy OTP cho {target_email} sau {timeout_sec}s.")
    return None
