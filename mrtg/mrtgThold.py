#!/usr/bin/env python
#
#!/usr/bin/env python3
import sys
import imaplib
import email
import email.header
import email.utils
import datetime
import requests
import json
import socket
import logging
import re

# Configuration
EMAIL_ACCOUNT = "pomessenger@gmail.com"
EMAIL_PASSWORD = "vmyzpxjjdwbhebbe"
EMAIL_FOLDER = "cactialert"

TELEGRAM_TOKEN = "7714200473:AAEBj9Bc00eDmipBsXQc4G3o168cVJQ3bvk"
TELEGRAM_CHAT_ID = "-5094237861"

FLUENTBIT_HOST = "192.168.117.64"
FLUENTBIT_PORT = 5140

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def tidy_subject(subject: str, maxlen: int = 250) -> str:
    if not subject:
        return ''
    # Remove common prefixes and Fwd/RE
    subject = re.sub(r'^(Fwd:|FW:|Re:|RE:|\s)+', '', subject)
    # Collapse whitespace
    subject = re.sub(r'\s+', ' ', subject).strip()
    # Remove control chars
    subject = ''.join(ch for ch in subject if ord(ch) >= 32)
    # Truncate
    if len(subject) > maxlen:
        subject = subject[:maxlen-3] + '...'
    return subject


def send_telegram_http(message: str, chat_id: str, token: str, parse_mode: str = 'HTML') -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": parse_mode}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            logging.error("Telegram API error %s: %s", r.status_code, r.text)
            return False
        return True
    except Exception:
        logging.exception("Telegram send failed")
        return False


def send_fluentbit(subject: str, timestamp: str):
    event = {"tag": "raw-cacti-event", "subject": subject, "timestamp": timestamp}
    data = json.dumps(event)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(data.encode('utf-8'), (FLUENTBIT_HOST, FLUENTBIT_PORT))
        return True
    except Exception:
        logging.exception("FluentBit UDP send failed")
        return False
    finally:
        sock.close()


def process_mailbox(M):
    rv, data = M.search(None, '(UNSEEN)')
    if rv != 'OK':
        logging.info('No unseen messages')
        return

    for num in data[0].split():
        rv, fetched = M.fetch(num, '(RFC822)')
        if rv != 'OK':
            logging.error('Failed to fetch message %s', num)
            continue

        raw_email = fetched[0][1]
        msg = email.message_from_bytes(raw_email)

        # decode subject
        hdr = email.header.make_header(email.header.decode_header(msg.get('Subject', '')))
        subject = str(hdr)
        tidy = tidy_subject(subject)

        # title selection
        up = subject.upper()
        if 'NORMAL' in up:
            title = '\U0001F3E4 <b>MRTG Threshold Alert Cleared</b>'
        elif 'IEPL' in up:
            title = '\U0001F3E4 \U0001F4F6 <b>MRTG Threshold Alert -- IEPL</b>'
        else:
            title = '\U0001F525 <b>MRTG Threshold Alert</b>'

        # timestamp
        date_tuple = email.utils.parsedate_tz(msg.get('Date'))
        if date_tuple:
            ts = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple)).isoformat()
        else:
            ts = datetime.datetime.now().isoformat()

        # send telegram
        tele_msg = f"{title}\n=========\n{tidy}\n"
        ok = send_telegram_http(tele_msg, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)
        if ok:
            logging.info('Sent Telegram alert: %s', tidy)
        else:
            logging.error('Failed to send Telegram alert for: %s', tidy)

        # send fluentbit
        if send_fluentbit(tidy, ts):
            logging.info('Sent subject to Fluent Bit')
        else:
            logging.error('Failed to send subject to Fluent Bit')

        # mark message seen
        try:
            M.store(num, '+FLAGS', '\\Seen')
        except Exception:
            pass


def main():
    logging.info('Starting MRTG threshold checker')
    M = imaplib.IMAP4_SSL('imap.gmail.com')
    try:
        rv, data = M.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    except imaplib.IMAP4.error:
        logging.error('LOGIN FAILED')
        sys.exit(1)

    rv, data = M.select(EMAIL_FOLDER)
    if rv != 'OK':
        logging.error('Unable to open mailbox: %s', rv)
        M.logout()
        sys.exit(1)

    process_mailbox(M)
    try:
        M.close()
    except Exception:
        pass
    M.logout()


if __name__ == '__main__':
    main()
