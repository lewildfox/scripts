import imaplib
import email
from email.message import Message
import requests
import datetime


# =====================
# CONFIGURATION
# =====================

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
MAILBOX = "u2020alert"

GMAIL_USER = "pomessenger@gmail.com"
GMAIL_PASSWORD = "eqxewqxcxyhodpid"

SENDER_EMAIL = "u2020@telin.net"

TELEGRAM_TOKEN = "1246959217:AAGXaQacKWpOy-9FnxtcWb0sbRQrgm3LWnw"

"""old chatIDs
CHAT_ID_DIALOG = "-4195541246"
CHAT_ID_TRUNK = "-586549031"
CHAT_ID_CAC = "-437435143"
CHAT_ID_SYSTEM = "-352485171"
"""

CHAT_ID_DIALOG = "-4195541246"
CHAT_ID_OM = "-5073340200"
CHAT_ID_TRUNK_CAC = "-586549031"
CHAT_ID_SYSTEM = "-5029590520"

# Toggle debug logging (set False to reduce output)
DEBUG = True

# =====================
# GMAIL FUNCTIONS
# =====================

def login_to_gmail():
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(GMAIL_USER, GMAIL_PASSWORD)
        typ, data = imap.select(MAILBOX)
        if typ != 'OK':
            if DEBUG:
                print(f"❌ Failed to select mailbox {MAILBOX}: {typ} {data}")
            return None
        if DEBUG:
            print("✅ Logged in to Gmail successfully (mailbox selected)")
        return imap
    except Exception as e:
        if DEBUG:
            print("❌ Gmail login failed:", e)
        return None

def filter_alarm_fields(content: str) -> str:
    """
    Always return all alarm fields, even if empty
    """
    fields = [
        "NE Name:",
        "NE Type:",
        "Severity:",
        "Category:",
        "Occurrence Time:",
        "Clearance Time:",
        "Location Information:",
        "Alarm Name:",
        "Alarm Explanation:",
    ]

    lines = content.splitlines()
    result = []

    for field in fields:
        value = ""
        for line in lines:
            if line.strip().startswith(field):
                value = line.strip()[len(field):].strip()
                break
        result.append(f"{field}  {value}")

    return "\n".join(result)

def extract_email_body(msg: Message) -> str:
    """Extract plain text body from email"""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
        # fallback: try text/html and strip tags
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode(errors="ignore")
                import re
                text = re.sub(r"<[^>]+>", "", html)
                return text
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")

    return ""


def normalize_content(content: str) -> str:
    start_index = content.find("++++++")
    if start_index != -1:
        content = content[start_index + len("++++++"):]
        content = content.replace("\r\n        ", "\r\n")
    return content


def search_emails(imap):
    try:
        if DEBUG:
            print("🔍 Searching for unseen emails...")
        typ, data = imap.search(None, f'(UNSEEN FROM "{SENDER_EMAIL}")')
        if DEBUG:
            print(f"Search response: {typ}")

        if typ != 'OK' or not data or not data[0]:
            if DEBUG:
                print("✅ Email search completed (no matches)")
            return

        ids = data[0].split()
        if DEBUG:
            print(f"Found {len(ids)} matching message(s)")

        for num in ids:
            typ, msg_data = imap.fetch(num, "(RFC822)")
            if typ != 'OK':
                if DEBUG:
                    print(f"❌ Failed to fetch message {num}: {typ}")
                continue
            msg = email.message_from_bytes(msg_data[0][1])

            # debug headers
            from_hdr = msg.get('From')
            subj = msg.get('Subject')
            if DEBUG:
                print(f"Message {num} From: {from_hdr} Subject: {subj}")

            content = extract_email_body(msg)
            content = normalize_content(content)
            content = filter_alarm_fields(content)

            if DEBUG:
                print(f"Routing message {num}...")
            route_email(content)

            # mark seen
            try:
                imap.store(num, '+FLAGS', '\\Seen')
            except Exception:
                pass

        if DEBUG:
            print("✅ Email search completed")

    except Exception as e:
        print("❌ Error searching emails:", e)


# =====================
# ROUTING LOGIC
# =====================

def route_email(content: str):
    if DEBUG:
        print("Routing decision for content snippet:", (content or '')[:120].replace('\n', ' '))
    if "GSDIA" in content:
        if DEBUG:
            print("Matched: GSDIA -> DIALOG TRUNK")
        send_email_via_telegram(content, "DIALOG TRUNK", CHAT_ID_DIALOG)

    elif "ADJ_ODINE" in content:
        send_email_via_telegram(content, "ODINE TRUNK GROUP", CHAT_ID_SYSTEM)

    elif "SG1" in content:
        send_email_via_telegram(content, "SG1 BACKUP DC ALARMS", CHAT_ID_OM)

    elif "HK1" in content:
        send_email_via_telegram(content, "HK1 BACKUP DC ALARMS", CHAT_ID_OM)

    elif "Alarm Name:  Trunk Group Fault" in content:
        send_email_via_telegram(content, "TRUNK GROUP", CHAT_ID_TRUNK_CAC)

    elif "Connection Admission Control" in content:
        send_email_via_telegram(content, "CAC LIMIT", CHAT_ID_TRUNK_CAC)

    else:
        if DEBUG:
            print("Matched: default -> SYSTEM RELATED")
        send_email_via_telegram(content, "SYSTEM RELATED", CHAT_ID_SYSTEM)


# =====================
# TELEGRAM
# =====================

def send_email_via_telegram(content: str, alarm_type: str, chat_id: str):
    try:
        if "Category:  Alarm" in content:
            message = (
                "🔥 {type} ALARM ❗\n"
                "Please check urgently!!!\n"
                "=========\n{body}"
            ).format(type=alarm_type, body=content)
        else:
            message = (
                "🏄 {type} ALARM CLEARED 🏄\n"
                "=========\n{body}"
            ).format(type=alarm_type, body=content)

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        r = requests.post(url, json=payload, timeout=10)
        if r.ok:
            if DEBUG:
                print(f"📨 Sent Telegram alert: {alarm_type} (ok)")
        else:
            print(f"❌ Telegram API responded {r.status_code}: {r.text}")

    except Exception as e:
        print("❌ Telegram send failed:", e)


# =====================
# MAIN
# =====================

def main():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("⏱ Alarm checkpoint:", timestamp)

    imap = login_to_gmail()
    if not imap:
        return

    search_emails(imap)
    imap.logout()


if __name__ == "__main__":
    main()
