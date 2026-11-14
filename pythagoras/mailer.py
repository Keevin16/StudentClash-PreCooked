"""Invitation email. Without SMTP settings the mail is written to data/outbox/ and the API returns the link instead."""
import logging
import smtplib
import time
from email.message import EmailMessage

from . import config

log = logging.getLogger("pythagoras.mail")


def configured() -> bool:
    return bool(config.SMTP_HOST)


def invite_url(token: str) -> str:
    return f"{config.PUBLIC_URL}/interview/{token}"


def send_invite(to: str, name: str, assignment: str, token: str) -> bool:
    """True if the email was handed to the SMTP server."""
    url = invite_url(token)
    msg = EmailMessage()
    msg["Subject"] = f"Your Pythagoras interview for {assignment}"
    msg["From"], msg["To"] = config.SMTP_FROM, to
    msg.set_content(
        f"Hi {name},\n\nThanks for submitting your deliverable for \"{assignment}\".\n\n"
        f"Pythagoras will have a short spoken conversation with you (about {config.DURATION_S // 60} minutes) about "
        f"your project. Open this link when you are in a quiet place, with a microphone:\n\n{url}\n\n"
        "Pythagoras does not grade you: your professor receives a summary to prepare your oral exam.\n\n- Pythagoras\n")
    if not configured():
        outbox = config.DATA_DIR / "outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        (outbox / f"{int(time.time())}-{to}.eml").write_bytes(bytes(msg))
        log.info("SMTP not configured; invite for %s: %s", to, url)
        return False
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
            s.starttls()
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException) as e:
        log.error("sending invite to %s failed: %s", to, e)
        return False
