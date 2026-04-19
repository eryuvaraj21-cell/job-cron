"""
OTP Fetcher - retrieves OTP codes from a Gmail inbox via IMAP.
"""

import email
import imaplib
import logging
import re
import time
from email.header import decode_header
from typing import Optional


logger = logging.getLogger(__name__)


def _decode(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    parts = decode_header(value)
    out = []
    for txt, enc in parts:
        if isinstance(txt, bytes):
            out.append(txt.decode(enc or "utf-8", errors="ignore"))
        else:
            out.append(txt)
    return "".join(out)


def _extract_body(msg) -> str:
    bodies = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in ("text/plain", "text/html"):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        bodies.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                bodies.append(payload.decode(msg.get_content_charset() or "utf-8", errors="ignore"))
        except Exception:
            pass
    return "\n".join(bodies)


def fetch_otp(
    imap_host: str,
    imap_port: int,
    email_user: str,
    email_password: str,
    sender_filters: list,
    subject_keywords: list,
    timeout_seconds: int = 120,
    poll_interval: int = 5,
) -> Optional[str]:
    """
    Poll the inbox until an OTP is found in a recent unread message that matches
    sender or subject filters. Returns the OTP code as a string, or None on timeout.
    """
    deadline = time.time() + timeout_seconds
    last_uid_seen = None

    while time.time() < deadline:
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            mail.login(email_user, email_password)
            mail.select("INBOX")

            # Search recent unseen messages
            status, data = mail.search(None, "UNSEEN")
            if status != "OK":
                mail.logout()
                time.sleep(poll_interval)
                continue

            uids = data[0].split()
            # Newest first
            for uid in reversed(uids[-20:]):
                if uid == last_uid_seen:
                    continue
                last_uid_seen = uid

                status, msg_data = mail.fetch(uid, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = _decode(msg.get("Subject", ""))
                from_addr = _decode(msg.get("From", "")).lower()

                sender_match = (
                    not sender_filters
                    or any(s.lower() in from_addr for s in sender_filters)
                )
                subject_match = (
                    not subject_keywords
                    or any(k.lower() in subject.lower() for k in subject_keywords)
                )
                if not (sender_match or subject_match):
                    continue

                body = _extract_body(msg)
                # Common OTP patterns: 4-8 digit code
                candidates = re.findall(r"(?<!\d)(\d{4,8})(?!\d)", subject + "\n" + body)
                # Prefer 6-digit (most common for OTPs)
                for length in (6, 5, 4, 7, 8):
                    for c in candidates:
                        if len(c) == length:
                            logger.info(f"[OTP] Retrieved OTP from email subject='{subject}'")
                            try:
                                mail.logout()
                            except Exception:
                                pass
                            return c

            try:
                mail.logout()
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"[OTP] IMAP error: {e}")

        time.sleep(poll_interval)

    logger.warning("[OTP] Timed out waiting for OTP email")
    return None
