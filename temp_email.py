import requests
import time
import re
import random
import string
from bs4 import BeautifulSoup
import html.parser as html


BASE_URL = "https://api.mail.tm"

def get_valid_domain():
    """Fetch a valid domain from mail.tm"""
    res = requests.get(f"{BASE_URL}/domains")
    res.raise_for_status()
    domains = res.json()["hydra:member"]
    if not domains:
        raise Exception("No domains available from mail.tm")
    return domains[0]["domain"]

def generate_random_credentials():
    """Generate random username and password"""
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    password = "TempPass123!"
    return username, password

def create_account():
    """Create a new temp mail.tm account and return email + token"""
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
    """Login to the mail.tm account and return token"""
    res = requests.post(f"{BASE_URL}/token", json={"address": email, "password": password})
    res.raise_for_status()
    return res.json()["token"]

def get_messages(token):
    """List all received messages"""
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/messages", headers=headers)
    res.raise_for_status()
    return res.json()["hydra:member"]

def read_message(token, msg_id):
    """Read a specific message by ID"""
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/messages/{msg_id}", headers=headers)
    res.raise_for_status()
    return res.json()

def extract_first_link(text):
    """Extract the first verification link (not an image or logo)"""
    # Decode HTML entities (e.g. %40 -> @)
    text = html.unescape(text)

    # First, try regex to match a link that looks like the confirmation one
    verification_links = re.findall(r'https://etherscan\.io/confirmemail\?[^"\s<>]+', text)
    if verification_links:
        return verification_links[0]

    # Then fallback to BeautifulSoup (in case the regex missed it)
    try:
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag['href']
            if href.startswith("https://etherscan.io/confirmemail?"):
                return href
    except Exception as e:
        print(f"⚠️ HTML parsing error: {e}")

    return None


def wait_for_email_with_link(token, timeout=10, interval=5):
    """Poll inbox until a message arrives or timeout hits"""
    elapsed = 0
    while elapsed < timeout:
        try:
            messages = get_messages(token)
            if messages:
                message = read_message(token, messages[0]["id"])
                link = extract_first_link(message.get("text", "") or message.get("html", ""))
                return {
                    "subject": message.get("subject"),
                    "link": link,
                    "raw": message
                }
        except Exception as e:
            print(f"⚠️ Error while checking mail: {e}")

        print(f"📬 Checking inbox... {elapsed}/{timeout} seconds elapsed")
        time.sleep(interval)
        elapsed += interval

    print("⏱️ Timeout reached. No email received.")
    return None

