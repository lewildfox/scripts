#!/usr/bin/env python
#
import sys
import imaplib
import getpass
import email
import email.header
import datetime
import telegram
import re
from telegram import Bot

EMAIL_ACCOUNT = "pomessenger@gmail.com"
# Use 'INBOX' to read inbox.  Note that whatever folder is specified,
# after successfully running this script all emails in that folder
# will be marked as read.
#EMAIL_FOLDER = "burhan@telin.net/Ticketing-HighCritical"
EMAIL_FOLDER = "TicketPO"

teletoken = '1246959217:AAGXaQacKWpOy-9FnxtcWb0sbRQrgm3LWnw'
chatid = '-1002702698072'

def sendtele(msg, chat_id, token):
    bot = Bot(token=token)
    bot.sendMessage(chat_id=chat_id, text=msg, parse_mode='HTML')


def get_decoded_email_body(message_body):
    """ Decode email body.
    Detect character set if the header is not set.
    We try to get text/plain, but if there is not one then fallback to text/html.
    :param message_body: Raw 7-bit message body input e.g. from imaplib. Double encoded in quoted-printable and latin-1
    :return: Message body as unicode string
    """

    msg = email.message_from_string(message_body)

    #!/usr/bin/env python3
    import sys
    import imaplib
    import email
    import email.header
    import datetime
    import re
    import requests

    EMAIL_ACCOUNT = "pomessenger@gmail.com"
    EMAIL_FOLDER = "TicketPO"

    # Telegram bot token and chat id (update as needed)
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
        """Decode email bytes to a unicode string.

        Prefer text/plain part; fall back to text/html. Silently ignores
        unknown encodings.
        """
        msg = email.message_from_bytes(message_bytes)

        if msg.is_multipart():
            text = None
            html = None
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == 'text/plain' and text is None:
                    try:
                        text = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'ignore')
                    except Exception:
                        text = part.get_payload(decode=True).decode('utf-8', 'ignore')
                elif ctype == 'text/html' and html is None:
                    try:
                        html = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'ignore')
                    except Exception:
                        html = part.get_payload(decode=True).decode('utf-8', 'ignore')
            return (text or html or '').strip()
        else:
            payload = msg.get_payload(decode=True)
            if not payload:
                return ''
            return payload.decode(msg.get_content_charset() or 'utf-8', 'ignore').strip()


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
            hdr = email.header.make_header(email.header.decode_header(msg.get('Subject', '')))
            subject = str(hdr).replace('Fwd:', '')

            if 'NORMAL' in subject:
                title = '\U0001F3E4 <b> Ticket Dispatched to PO </b>'
            else:
                title = '\U0001F525 <b>Ticket Dispatched to PO</b> \u274C'

            date_tuple = email.utils.parsedate_tz(msg.get('Date'))
            if date_tuple:
                local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))

            body = get_decoded_email_body(raw_email)

            message = f"{title}\n=========\n{subject}\n\n{body}"
            send_telegram(message, CHAT_ID, TELEGRAM_TOKEN)
            print("Alert sent to Telegram.")


    def main() -> None:
        print(datetime.datetime.now())
        M = imaplib.IMAP4_SSL('imap.gmail.com')

        try:
            rv, data = M.login(EMAIL_ACCOUNT, 'vmyzpxjjdwbhebbe')
        except imaplib.IMAP4.error:
            print("LOGIN FAILED!!!")
            sys.exit(1)

        rv, data = M.select(EMAIL_FOLDER)
        if rv == 'OK':
            print("Processing mailbox...")
            process_mailbox(M)
            M.close()
        else:
            print("ERROR: Unable to open mailbox", rv)

        M.logout()


    if __name__ == '__main__':
        main()