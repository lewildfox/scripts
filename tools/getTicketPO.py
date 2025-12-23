#!/usr/bin/env python3
import sys
import imaplib
import email
import email.header
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
        'parse_mode': 'Markdown'
    }
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Failed to send Telegram message: {exc}")



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
        title = '\U0001F525 *Ticket Dispatched to PO* \u274C'

        # Escape Markdown special characters in subject to prevent broken parsing
        # Legacy Markdown escapes: *, _, `, [
        safe_subject = re.sub(r'([*_`\[])', r'\\\1', subject)

        message = f"{title}\n=========\n*{safe_subject}*"
        
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