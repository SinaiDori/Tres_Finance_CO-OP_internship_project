# import requests
# import time
# import re
# import random
# import string
# from bs4 import BeautifulSoup
# import html.parser as html

# BASE_URL = "https://api.mail.tm"


# def get_valid_domain():
#     res = requests.get(f"{BASE_URL}/domains")
#     res.raise_for_status()
#     domains = res.json()["hydra:member"]
#     if not domains:
#         raise Exception("No domains available from mail.tm")
#     return domains[0]["domain"]


# def generate_random_credentials():
#     username = ''.join(random.choices(
#         string.ascii_lowercase + string.digits, k=10))
#     password = "TempPass123!"
#     return username, password


# def create_account():
#     username, password = generate_random_credentials()
#     domain = get_valid_domain()
#     email = f"{username}@{domain}"

#     res = requests.post(f"{BASE_URL}/accounts",
#                         json={"address": email, "password": password})
#     if res.status_code == 201:
#         token = login(email, password)
#         return email, token
#     else:
#         raise Exception(f"Could not create mail.tm account: {res.text}")


# def login(email, password):
#     res = requests.post(f"{BASE_URL}/token",
#                         json={"address": email, "password": password})
#     res.raise_for_status()
#     return res.json()["token"]


# def get_messages(token):
#     headers = {"Authorization": f"Bearer {token}"}
#     res = requests.get(f"{BASE_URL}/messages", headers=headers)
#     res.raise_for_status()
#     return res.json()["hydra:member"]


# def read_message(token, msg_id):
#     headers = {"Authorization": f"Bearer {token}"}
#     res = requests.get(f"{BASE_URL}/messages/{msg_id}", headers=headers)
#     res.raise_for_status()
#     return res.json()


# def wait_for_verification_code(
#     token,
#     expected_sender="noreply@seitrace.com",
#     expected_subject="Seitrace register",
#     regex_pattern=r"code is (\d{6})",
#     timeout: int = 20,
#     interval: int = 5
# ) -> str:
#     """Poll inbox and extract a 6-digit verification code from the message body"""
#     elapsed = 0
#     while elapsed < timeout:
#         try:
#             messages = get_messages(token)
#             for msg in messages:
#                 sender = msg.get("from", {}).get("address", "")
#                 subject = msg.get("subject", "")
#                 if expected_sender in sender and expected_subject in subject:
#                     full = read_message(token, msg["id"])
#                     content = full.get("text", "") or full.get("html", "")
#                     content = html.unescape(content)

#                     # 🔍 Debug output to see what the email content looks like
#                     print("📨 RAW EMAIL CONTENT:\n", content)
#                     print("🔎 Subject:", subject)
#                     print("🔎 From:", sender)

#                     match = re.search(regex_pattern, content)
#                     if match:
#                         code = match.group(1)
#                         print(f"✅ Found Seitrace verification code: {code}")
#                         return code
#                     else:
#                         print("⚠️ Email matched but no code found in content.")
#         except Exception as e:
#             print(f"⚠️ Error while checking mail: {e}")

#         print(
#             f"📬 Waiting for verification email... {elapsed}/{timeout} seconds elapsed")
#         time.sleep(interval)
#         elapsed += interval

#     raise TimeoutError(
#         "⏱️ Timeout reached. Verification email not received or code not found.")

import os
import re
import time
import uuid
import imaplib
import email
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import Tuple, Optional, List

# Optional: load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# =============================
# Public API (kept stable)
# - create_account() -> (email, token)
# - wait_for_verification_code(token, expected_sender, expected_subject, regex_pattern, timeout, interval) -> code
# Back-compat stubs: login(), generate_random_credentials(), get_messages(), read_message()
# =============================


def _env(name: str, default: Optional[str] = None) -> str:
    val = os.environ.get(name, default)
    if val is None or val == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def _now_ms() -> int:
    return int(time.time() * 1000)


def generate_random_credentials():
    """Compatibility stub. Not needed for AnonAddy."""
    return None, None


def create_account() -> Tuple[str, str]:
    """
    Create a unique AnonAddy standard alias for this run and return:
      (alias_email, token)
    'token' encodes alias + start time for filtering.
    Requires:
      ANONADDY_SUBDOMAIN (e.g., 'sinai')
      ANONADDY_TLD (optional, default 'anonaddy.com')
    """
    sub = _env("ANONADDY_SUBDOMAIN")
    tld = os.environ.get("ANONADDY_TLD", "anonaddy.com")
    local = f"seitrace-{uuid.uuid4().hex[:10]}"
    alias = f"{local}@{sub}.{tld}"
    token = f"{alias}|{_now_ms()}"
    return alias, token


def login(email_addr, password):
    """Compatibility stub. Not used with AnonAddy+IMAP."""
    return None


def get_messages(_inbox_id):
    """Compatibility stub. Not used with AnonAddy+IMAP."""
    return []


def read_message(_inbox_id, _email_id):
    """Compatibility stub. Not used with AnonAddy+IMAP."""
    return {}


def _connect_imap():
    host = _env("IMAP_HOST", "imap.gmail.com")
    port = int(os.environ.get("IMAP_PORT", "993"))
    user = _env("IMAP_USER")
    pw = _env("IMAP_PASS")  # Gmail App Password
    M = imaplib.IMAP4_SSL(host, port)
    M.login(user, pw)
    M.select("INBOX")
    return M


def _alias_in_headers(envelope: email.message.Message, alias: str) -> bool:
    """Strict check: alias must appear in recipient-related headers."""
    candidate_headers = [
        "To", "Cc", "Delivered-To", "X-Original-To",
        "X-Forwarded-To", "Envelope-To", "Apparently-To",
    ]
    for h in candidate_headers:
        v = envelope.get(h) or ""
        if alias.lower() in v.lower():
            return True
    # last resort: scan all headers
    for k, v in envelope.items():
        if alias.lower() in f"{k}: {v}".lower():
            return True
    return False


def _internaldate_ts(M, msg_id: bytes) -> Optional[int]:
    """
    Get the IMAP INTERNALDATE for msg_id and return epoch ms.
    INTERNALDATE is set by the server upon receipt; more reliable than Date header.
    """
    try:
        typ, data = M.fetch(msg_id, "(INTERNALDATE)")
        if typ != "OK" or not data or not data[0]:
            return None
        raw = data[0][1].decode("utf-8", errors="ignore")
        import re as _re
        m = _re.search(r'INTERNALDATE "([^"]+)"', raw)
        if not m:
            return None
        dt_str = m.group(1)  # e.g., 11-Sep-2025 10:48:37 +0000
        dt = datetime.strptime(dt_str, "%d-%b-%Y %H:%M:%S %z")
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def _fetch_candidates(M, alias: str, since_day: str) -> List[tuple[bytes, email.message.Message, Optional[int]]]:
    """
    Return (msg_id, envelope, internaldate_ms) for messages SINCE since_day
    that reference the alias in headers. Sorted newest-first by INTERNALDATE.
    """
    # Try UNSEEN first to minimize noise, then fall back to all SINCE today.
    def _search(*terms) -> List[tuple[bytes, email.message.Message, Optional[int]]]:
        typ, data = M.search(None, *terms)
        if typ != "OK" or not data or not data[0]:
            return []
        ids = data[0].split()
        out: List[tuple[bytes, email.message.Message, Optional[int]]] = []
        for msg_id in ids:
            typ2, msg = M.fetch(msg_id, "(RFC822)")
            if typ2 != "OK" or not msg or not msg[0]:
                continue
            raw = msg[0][1]
            em = email.message_from_bytes(raw)
            if _alias_in_headers(em, alias):
                out.append((msg_id, em, _internaldate_ts(M, msg_id)))
        out.sort(key=lambda t: (t[2] or 0, int(t[0])), reverse=True)
        return out

    candidates = _search("UNSEEN", "SINCE", since_day)
    return candidates or _search("SINCE", since_day)


def _body_text(envelope: email.message.Message) -> str:
    """Extract combined text from text/plain + text/html parts, decoding safely."""
    if envelope.is_multipart():
        parts = []
        for part in envelope.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype in ("text/plain", "text/html"):
                try:
                    parts.append(
                        part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="ignore"
                        )
                    )
                except Exception:
                    try:
                        parts.append(part.get_payload())
                    except Exception:
                        pass
        return "\n".join(p for p in parts if p)
    else:
        try:
            return envelope.get_payload(decode=True).decode(
                envelope.get_content_charset() or "utf-8", errors="ignore"
            )
        except Exception:
            payload = envelope.get_payload()
            return payload if isinstance(payload, str) else ""


def wait_for_verification_code(
    token: str,
    expected_sender: Optional[str] = None,
    expected_subject: Optional[str] = None,
    regex_pattern: str = r"\b(\d{6})\b",
    timeout: int = 60,
    interval: int = 5,
) -> str:
    """
    Poll IMAP until a *fresh* email to this run's alias arrives (and matches optional filters),
    then extract the verification code using regex_pattern.

    'Fresh' means INTERNALDATE >= the timestamp embedded in 'token'.
    This avoids accidentally grabbing an older code if more than one email exists.
    Note: AnonAddy can rewrite 'From:' — if expected_sender doesn't match headers,
    we also check for that string in the body.
    """
    alias, start_ms_s = token.split("|", 1)
    start_ms = int(start_ms_s)
    deadline = time.time() + timeout
    since_day = datetime.now().strftime("%d-%b-%Y")

    M = _connect_imap()
    try:
        while time.time() < deadline:
            candidates = _fetch_candidates(M, alias, since_day)
            for msg_id, em, ts in candidates:
                # enforce freshness vs create_account() time (allow small skew)
                if ts is not None and ts < (start_ms - 120000):
                    continue

                frm = (em.get("From") or "")
                subj = (em.get("Subject") or "")
                body = _body_text(em)

                # Subject filter (robust)
                if expected_subject and expected_subject.lower() not in subj.lower():
                    continue

                # Sender filter (header OR body, to handle AnonAddy rewriting)
                if expected_sender:
                    if (expected_sender.lower() not in frm.lower()) and (expected_sender.lower() not in (body or "").lower()):
                        continue

                # Try body first, then subject as a fallback
                m = re.search(regex_pattern, body or "")
                if not m:
                    m = re.search(regex_pattern, subj or "")

                if m:
                    return m.group(1)

            time.sleep(interval)

        raise TimeoutError("Timeout waiting for verification email.")
    finally:
        try:
            M.close()
        except Exception:
            pass
        try:
            M.logout()
        except Exception:
            pass
