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
    username = ''.join(random.choices(
        string.ascii_lowercase + string.digits, k=10))
    password = "TempPass123!"
    return username, password


def create_account():
    """Create a new temp mail.tm account and return email + token"""
    username, password = generate_random_credentials()
    domain = get_valid_domain()
    email = f"{username}@{domain}"

    res = requests.post(f"{BASE_URL}/accounts",
                        json={"address": email, "password": password})
    if res.status_code == 201:
        token = login(email, password)
        return email, token
    else:
        raise Exception(f"Could not create mail.tm account: {res.text}")


def login(email, password):
    """Login to the mail.tm account and return token"""
    res = requests.post(f"{BASE_URL}/token",
                        json={"address": email, "password": password})
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
    """Extract the first verification link from Subscan"""
    if not text:
        return None

    # Decode HTML entities
    text = html.unescape(text)

    # Multiple patterns to catch Subscan verification links
    patterns = [
        r'https://[^"\s<>]*subscan[^"\s<>]*verify[^"\s<>]*',
        r'https://[^"\s<>]*subscan[^"\s<>]*confirm[^"\s<>]*',
        r'https://[^"\s<>]*subscan[^"\s<>]*activation[^"\s<>]*',
        r'https://pro\.subscan\.io/[^"\s<>]*verify[^"\s<>]*',
        r'https://pro\.subscan\.io/[^"\s<>]*confirm[^"\s<>]*',
        r'https://[^"\s<>]*subscan[^"\s<>]+',  # Fallback: any subscan link
    ]

    for pattern in patterns:
        verification_links = re.findall(pattern, text, re.IGNORECASE)
        if verification_links:
            print(f"🔗 Found verification link with pattern: {pattern}")
            return verification_links[0]

    # Fallback to BeautifulSoup for HTML parsing
    try:
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag['href']
            if "subscan" in href.lower() and any(keyword in href.lower() for keyword in ["verify", "confirm", "activation"]):
                print(f"🔗 Found verification link via BeautifulSoup: {href}")
                return href

        # Last resort: any subscan link
        for tag in soup.find_all("a", href=True):
            href = tag['href']
            if "subscan" in href.lower():
                print(f"🔗 Found subscan link (fallback): {href}")
                return href

    except Exception as e:
        print(f"⚠️ HTML parsing error: {e}")

    return None


def wait_for_email_with_link(token, timeout=300, interval=10) -> str:
    """Poll inbox until a message arrives or timeout hits"""
    elapsed = 0
    print(
        f"📬 Starting email check. Will check every {interval} seconds for up to {timeout} seconds.")

    while elapsed < timeout:
        try:
            messages = get_messages(token)
            print(f"📨 Found {len(messages)} messages in inbox")

            if messages:
                print("📧 Processing messages:")
                for i, msg in enumerate(messages):
                    print(
                        f"  {i+1}. Subject: {msg.get('subject', 'No subject')}")
                    print(
                        f"     From: {msg.get('from', {}).get('address', 'Unknown sender')}")
                    print(f"     Date: {msg.get('createdAt', 'Unknown date')}")

                # Read the most recent message
                message = read_message(token, messages[0]["id"])
                text_content = message.get("text", "")
                html_content = message.get("html", "")

                print("📨 Raw email text content:")
                print(
                    text_content[:500] + "..." if len(text_content) > 500 else text_content)

                # Try to extract link from both text and HTML
                link = extract_first_link(
                    text_content) or extract_first_link(html_content)

                if link:
                    print(f"✅ Found verification link: {link}")
                    return link
                else:
                    print("⚠️ No verification link found in email content")

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
