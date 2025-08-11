import requests
import time
import re
import random
import string
from bs4 import BeautifulSoup
import html.parser as html

BASE_URL = "https://api.mail.tm"

def get_valid_domain():
    res = requests.get(f"{BASE_URL}/domains")
    res.raise_for_status()
    domains = res.json()["hydra:member"]
    if not domains:
        raise Exception("No domains available from mail.tm")
    return domains[0]["domain"]

def generate_random_credentials():
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    password = "TempPass123!"
    return username, password

def create_account():
    username, password = generate_random_credentials()
    domain = get_valid_domain()
    email = f"{username}@{domain}"

    res = requests.post(f"{BASE_URL}/accounts", json={"address": email, "password": password})
    if res.status_code == 201:
        token = login(email, password)
        return email, token
    else:
        raise Exception(f"Could not create mail.tm account: {res.text}")

def login(email, password):
    res = requests.post(f"{BASE_URL}/token", json={"address": email, "password": password})
    res.raise_for_status()
    return res.json()["token"]

def get_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/messages", headers=headers)
    res.raise_for_status()
    return res.json()["hydra:member"]

def read_message(token, msg_id):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/messages/{msg_id}", headers=headers)
    res.raise_for_status()
    return res.json()

def wait_for_verification_code(
    token,
    expected_sender="noreply@seitrace.com",
    expected_subject="Seitrace register",
    regex_pattern=r"code is (\d{6})",
    timeout: int = 20,
    interval: int = 5
) -> str:
    """Poll inbox and extract a 6-digit verification code from the message body"""
    elapsed = 0
    while elapsed < timeout:
        try:
            messages = get_messages(token)
            for msg in messages:
                sender = msg.get("from", {}).get("address", "")
                subject = msg.get("subject", "")
                if expected_sender in sender and expected_subject in subject:
                    full = read_message(token, msg["id"])
                    content = full.get("text", "") or full.get("html", "")
                    content = html.unescape(content)

                    # 🔍 Debug output to see what the email content looks like
                    print("📨 RAW EMAIL CONTENT:\n", content)
                    print("🔎 Subject:", subject)
                    print("🔎 From:", sender)

                    match = re.search(regex_pattern, content)
                    if match:
                        code = match.group(1)
                        print(f"✅ Found Seitrace verification code: {code}")
                        return code
                    else:
                        print("⚠️ Email matched but no code found in content.")
        except Exception as e:
            print(f"⚠️ Error while checking mail: {e}")

        print(f"📬 Waiting for verification email... {elapsed}/{timeout} seconds elapsed")
        time.sleep(interval)
        elapsed += interval

    raise TimeoutError("⏱️ Timeout reached. Verification email not received or code not found.")

