"""
TEMPORARY EMAIL UTILITY FOR SEITRACE AUTOMATION
This utility module provides sophisticated temporary email handling specifically for SeiTrace 
API key generation using IMAP-based email access. It supports two modes: custom catchall 
domains or Gmail/Googlemail addresses with intelligent dot variations to create unique aliases 
while bypassing service restrictions. The module implements robust email polling with timestamp-
based freshness checks, advanced filtering by sender/subject, and regex-based OTP code extraction
from email content. It handles complex IMAP operations including message parsing, header analysis,
and multi-part content decoding to reliably extract verification codes during automated account 
registration processes.
"""


import os
import re
import time
import uuid
import imaplib
import email
from datetime import datetime
from typing import Tuple, Optional, List

# Optional: load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


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


def _dot_variant(local: str, salt_hex: str) -> str:
    """
    Insert dots between characters using bits from salt (no adjacent dots).
    Guarantees at least one dot. Gmail ignores dots; services see uniqueness.
    """
    n = len(local)
    bits = int(salt_hex, 16)
    positions = []  # indices 1..n-1 where we insert a dot BEFORE char at i
    for i in range(1, n):
        take = bool(bits & 1)
        bits >>= 1
        if take and (not positions or i - positions[-1] > 1):
            positions.append(i)
    if not positions:
        positions = [max(1, n // 2)]
    out = []
    for i, ch in enumerate(local):
        if i in positions:
            out.append(".")
        out.append(ch)
    return "".join(out)


def create_account() -> Tuple[str, str]:
    """
    Return a fresh address for this run and a token:
      - If CATCHALL_DOMAIN is set -> seitrace-<id>@<domain>
      - Else: rotate each run between dotted @gmail.com and dotted @googlemail.com
              (no '+' so Seitrace doesn't block the trial)
    """
    domain = os.environ.get("CATCHALL_DOMAIN", "").strip()

    if domain:
        local_id = f"seitrace-{uuid.uuid4().hex[:10]}"
        alias = f"{local_id}@{domain}"
    else:
        user = _env("IMAP_USER")                  # e.g., sinai1775@gmail.com
        base_local, _base_host = user.split("@", 1)
        salt = uuid.uuid4().hex                   # per-run randomness
        dotted = _dot_variant(base_local, salt)   # unique dot pattern

        # rotate host per run using the last hex nibble
        use_googlemail = (int(salt[-1], 16) % 2) == 1
        host = "googlemail.com" if use_googlemail else "gmail.com"
        alias = f"{dotted}@{host}"

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
    Return INTERNALDATE (epoch ms). Handles both tuple and bytes responses.
    """
    try:
        typ, data = M.fetch(msg_id, "(INTERNALDATE)")
        if typ != "OK" or not data:
            return None

        # data can be:
        #   [(b'1 (INTERNALDATE "11-Sep-2025 10:48:37 +0000")', b'')]
        # or [b'1 (INTERNALDATE "11-Sep-2025 10:48:37 +0000")']
        if isinstance(data[0], tuple):
            line = data[0][0].decode("utf-8", errors="ignore")
        else:
            line = data[0].decode("utf-8", errors="ignore")

        import re as _re
        m = _re.search(r'INTERNALDATE "([^"]+)"', line)
        if m:
            dt = datetime.strptime(m.group(1), "%d-%b-%Y %H:%M:%S %z")
            return int(dt.timestamp() * 1000)

        # Fallback: use imaplib helper if format differs
        try:
            tup = imaplib.Internaldate2tuple(line.encode("utf-8"))
            if tup:
                return int(time.mktime(tup)) * 1000
        except Exception:
            pass
        return None
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
