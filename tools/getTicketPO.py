#!/usr/bin/env python3
import sys
import imaplib
import email
import email.header
import datetime
import requests
import re

# Configuration
EMAIL_SERVER = 'imap.gmail.com'
EMAIL_ACCOUNT = "pomessenger@gmail.com"
EMAIL_PASSWORD = 'vmyzpxjjdwbhebbe'
EMAIL_FOLDER = "TicketPO"

# Telegram Configuration
TELEGRAM_TOKEN = '1246959217:AAGXaQacKWpOy-9FnxtcWb0sbRQrgm3LWnw'
CHAT_ID = '-1002702698072'

def send_telegram(message: str, chat_id: str, token: str) -> None:
    """Send a message to Telegram using HTTP requests."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Failed to send Telegram message: {exc}")

def get_decoded_email_body(message_bytes: bytes) -> str:
    """Decode email bytes to a unicode string, prefer text/plain."""
    msg = email.message_from_bytes(message_bytes)
    text = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisposition = str(part.get('Content-Disposition'))

            if ctype == 'text/plain' and 'attachment' not in cdisposition:
                try:
                    text = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'ignore')
                    break 
                except Exception:
                    continue
        # Fallback to html if no plain text found
        if not text:
             for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == 'text/html':
                    try:
                        text = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'ignore')
                        break
                    except Exception:
                         continue
    else:
        try:
            text = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', 'ignore')
        except Exception:
            text = ""
            
    return text.strip()

def clean_subject(subject_raw: str) -> str:
    """Clean and format subject string."""
    # Decode header
    hdr = email.header.make_header(email.header.decode_header(subject_raw))
    subject = str(hdr)
    
    # Remove Fwd:, Re: etc. at the start (case insensitive)
    subject = re.sub(r'^\s*(?:Fwd|Re|Aw|FW):\s*', '', subject, flags=re.IGNORECASE)
    
    # Remove multiple spaces/newlines
    subject = ' '.join(subject.split())
    return subject

def process_mailbox(M: imaplib.IMAP4_SSL) -> None:
    """Process unseen messages in the selected mailbox and send alerts."""
    rv, data = M.search(None, '(UNSEEN)')
    if rv != 'OK':
        print("No messages found!")
        return

    for num in data[0].split():
        rv, fetched = M.fetch(num, '(RFC822)')
        if rv != 'OK':
            print(f"ERROR getting message {num}")
            continue

        raw_email = fetched[0][1]
        msg = email.message_from_bytes(raw_email)
        
        raw_subject = msg.get('Subject', '')
        subject = clean_subject(raw_subject)

        # Determine urgency/icon based on subject content
        if 'NORMAL' in subject.upper():
            title = '\U0001F3E4 <b>Ticket Dispatched to PO</b>'
        else:
            title = '\U0001F525 <b>Ticket Dispatched to PO</b> \u274C'

        body = get_decoded_email_body(raw_email)
        
        # Format the final message
        # Use HTML formatting for the subject to make it clear
        message = f"{title}\n=========\n<b>{subject}</b>\n\n{body}"
        
        send_telegram(message, CHAT_ID, TELEGRAM_TOKEN)
        print("Alert sent to Telegram.")

def main() -> None:
    print(f"Job started at: {datetime.datetime.now()}")
    M = imaplib.IMAP4_SSL(EMAIL_SERVER)

    try:
        M.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    except imaplib.IMAP4.error as e:
        print(f"LOGIN FAILED: {e}")
        sys.exit(1)

    rv, data = M.select(EMAIL_FOLDER)
    if rv == 'OK':
        print(f"Processing mailbox '{EMAIL_FOLDER}'...")
        process_mailbox(M)
        M.close()
    else:
        print(f"ERROR: Unable to open mailbox '{EMAIL_FOLDER}': {rv}")

    M.logout()

if __name__ == '__main__':
    main()