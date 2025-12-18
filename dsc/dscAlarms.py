#!/usr/bin/env python3
"""
dscalarm.py (cron-safe, debounced version)
"""

import requests
import logging
import socket
import json
import os
from datetime import datetime, timedelta

# -----------------------------
# CONFIG
# -----------------------------
OAM_NODES = [
    {"ip": "180.240.196.173", "oam": "DSC SOAM Singapore"},
    {"ip": "180.240.196.205", "oam": "DSC SOAM Hongkong"},
]

USERNAME = "alarmalert"
PASSWORD = "TselAlert2025%"
VERIFY_SSL = False

SEVERITY_FILTER = ["Major", "Critical"]

TELEGRAM_BOT_TOKEN = "7714200473:AAEBj9Bc00eDmipBsXQc4G3o168cVJQ3bvk"
TELEGRAM_CHAT_ID = "-5094237861"

FLUENTBIT_HOST = "192.168.117.64"
FLUENTBIT_PORT = 5140

ACTIVE_STATE_FILE = "/home/eburwic/SCRIPTS/dsctracker_active.json"

# -----------------------------
# SEVERITY COLOR CODE
# -----------------------------
SEVERITY_COLOR = {
    "Critical": "🔴 *CRITICAL*",
    "Major": "🟠 *MAJOR*",
    "Minor": "🟡 *MINOR*",
    "Warning": "🔵 *WARNING*",
    "Normal": "🟢 *NORMAL*",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
if not VERIFY_SSL:
    requests.packages.urllib3.disable_warnings()

state = {}


def load_state():
    global state
    if os.path.exists(ACTIVE_STATE_FILE):
        try:
            with open(ACTIVE_STATE_FILE, "r") as fh:
                state = json.load(fh)
        except:
            state = {}
    else:
        state = {}


def save_state():
    try:
        with open(ACTIVE_STATE_FILE, "w") as fh:
            json.dump(state, fh, indent=2)
    except Exception as e:
        logging.error("Failed to save state: %s", e)


def get_token(base_url):
    url = f"{base_url}/auth/tokens"
    payload = {"username": USERNAME, "password": PASSWORD}
    try:
        r = requests.post(url, data=payload, verify=VERIFY_SSL, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", {})
        return data.get("token"), data.get("gooduntil")
    except Exception as e:
        logging.error("Failed token from %s: %s", base_url, e)
        return None, None


def fetch_alarms(base_url, token):
    url = f"{base_url}/mon/alarms"
    headers = {"X-Auth-Token": token}
    try:
        r = requests.get(url, headers=headers, verify=VERIFY_SSL, timeout=15)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        logging.error("Fetch alarm error %s: %s", base_url, e)
        return None


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error("Telegram send failed: %s", e)


def send_fluentbit(event_obj):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(json.dumps(event_obj).encode(), (FLUENTBIT_HOST, FLUENTBIT_PORT))
        s.close()
    except Exception as e:
        logging.error("FluentBit UDP failed: %s", e)


def safe_md(s):
    return str(s or "").replace("`", "'")


def parse_gooduntil(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except:
        return None


def run_once():
    global state

    for node in OAM_NODES:
        ip = node["ip"]
        oam_name = node["oam"]
        base_url = f"https://{ip}/mmi/dsr/v4.1"
        ip_key = str(ip)

        if ip_key not in state:
            state[ip_key] = {"previous": {}, "confirmed": {}}

        prev = state[ip_key]["previous"]
        confirmed = state[ip_key]["confirmed"]

        token, gooduntil = get_token(base_url)
        if not token:
            logging.error("[%s] Token unavailable", oam_name)
            continue

        alarms = fetch_alarms(base_url, token)
        if alarms is None:
            continue

        filtered = [a for a in alarms if a.get("severity") in SEVERITY_FILTER]

        current = {}
        for a in filtered:
            idx = str(a.get("index") or a.get("seqNum"))
            current[idx] = a

        prev_idx = set(prev.keys())
        curr_idx = set(current.keys())

        first_seen = curr_idx - prev_idx
        debounced_new = prev_idx & curr_idx - set(confirmed.keys())
        cleared = set(confirmed.keys()) - curr_idx

        # -------------------------------------
        # CONFIRMED ALARM RAISE (2 checks)
        # -------------------------------------
        for idx in debounced_new:
            a = current[idx]
            inst = a.get("instance") or a.get("process") or "N/A"
            sev_label = SEVERITY_COLOR.get(a.get("severity"), safe_md(a.get("severity")))

            text = (
                f"🔥 *DSC Alarm Confirmed*\n"
                f"*Node:* {oam_name}\n"
                f"*Server:* `{safe_md(a.get('server'))}`\n"
                f"*Severity:* {sev_label}\n"
                f"*Name:* {safe_md(a.get('name'))}\n"
                f"*Instance:* `{safe_md(inst)}`\n"
                f"*Time:* {safe_md(a.get('timestamp'))}\n"
                f"*Description:*\n{safe_md(a.get('description'))}"
            )

            send_telegram(text)

            send_fluentbit({
                "status": "RAISED",
                "oam": oam_name,
                "ip": ip,
                "index": idx,
                "server": a.get("server"),
                "severity": a.get("severity"),
                "name": a.get("name"),
                "instance": inst,
                "timestamp": a.get("timestamp"),
                "description": a.get("description"),
                "errInfo": a.get("errInfo"),
            })

            confirmed[idx] = a

        # -------------------------------------
        # CLEARED ALARMS
        # -------------------------------------
        for idx in cleared:
            orig = confirmed[idx]
            inst = orig.get("instance") or orig.get("process") or "N/A"
            sev_label = SEVERITY_COLOR.get(orig.get("severity"), safe_md(orig.get("severity")))

            text = (
                f"🟢 *DSC Alarm Cleared*\n"
                f"*Node:* {oam_name}\n"
                f"*Server:* `{safe_md(orig.get('server'))}`\n"
                f"*Severity:* {sev_label}\n"
                f"*Name:* {safe_md(orig.get('name'))}\n"
                f"*Instance:* `{safe_md(inst)}`\n"
                f"*Original Time:* {safe_md(orig.get('timestamp'))}\n"
                f"*Cleared:* {datetime.now().isoformat()}\n"
                f"*Description:*\n{safe_md(orig.get('description'))}"
            )

            send_telegram(text)

            send_fluentbit({
                "status": "CLEARED",
                "oam": oam_name,
                "ip": ip,
                "index": idx,
                "server": orig.get("server"),
                "severity": orig.get("severity"),
                "name": orig.get("name"),
                "instance": inst,
                "original_timestamp": orig.get("timestamp"),
                "cleared_timestamp": datetime.now().isoformat(),
                "description": orig.get("description"),
                "errInfo": orig.get("errInfo"),
            })

            del confirmed[idx]

        state[ip_key]["previous"] = current

    save_state()


if __name__ == "__main__":
    logging.info("Running DSC Alarm Monitor (debounced cron-safe)...")
    load_state()
    run_once()
    logging.info("Completed single run.")
