#!/usr/bin/env python3
import os
import time
import json
import smtplib
import requests
from email.message import EmailMessage
from dotenv import load_dotenv

# ─── Load .env (if you’re using one) ───────────────────────────────────────
load_dotenv()
# ────────────────────────────────────────────────────────────────────────────

# ─── CONFIG ────────────────────────────────────────────────────────────────
TERM       = "202550"  # Summer 1 2025
COURSES    = [
    ("CSYE", "7374", "53300"),  # AI Agent Infrastructure
    ("INFO", "7374", "53309"),  # Managing Op Risk
]
POLL_EVERY = 180  # seconds between emails
# ────────────────────────────────────────────────────────────────────────────

# ─── Your browser cookies (from Chrome DevTools) ──────────────────────────
JSESSIONID      = os.getenv("JSESSIONID")
NUBANNER_COOKIE = os.getenv("NUBANNER_COOKIE")
# ────────────────────────────────────────────────────────────────────────────

# ─── SMTP settings (env or .env) ──────────────────────────────────────────
SMTP_USER  = os.getenv("SMTP_USER")
SMTP_PASS  = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO   = os.getenv("EMAIL_TO", SMTP_USER)
# ────────────────────────────────────────────────────────────────────────────

def send_email(body: str):
    msg = EmailMessage()
    msg["Subject"] = "NU Banner Seat/Waitlist Status"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)

def build_session():
    sess = requests.Session()
    sess.cookies.set("JSESSIONID",      JSESSIONID,
                     domain="nubanner.neu.edu", path="/StudentRegistrationSsb")
    sess.cookies.set("nubanner-cookie", NUBANNER_COOKIE,
                     domain="nubanner.neu.edu", path="/")
    return sess

def fetch_for(session, subj, num, crn):
    uid = str(int(time.time() * 1000))
    url = (
        "https://nubanner.neu.edu/StudentRegistrationSsb/ssb/searchResults/searchResults"
        f"?txt_subject={subj}"
        f"&txt_courseNumber={num}"
        f"&txt_term={TERM}"
        f"&startDatepicker=&endDatepicker="
        f"&uniqueSessionId={uid}"
        f"&pageOffset=0&pageMaxSize=500"
        "&sortColumn=subjectDescription&sortDirection=asc"
    )
    r = session.get(url, timeout=10)
    r.raise_for_status()
    j = r.json()
    data = j.get("data") or []
    for d in data:
        if d["courseReferenceNumber"] == crn:
            return d["seatsAvailable"], d["waitAvailable"]
    # If not found, treat as 0/0
    return 0, 0

def main():
    session = build_session()

    while True:
        lines = []
        for subj, num, crn in COURSES:
            try:
                seats, wait = fetch_for(session, subj, num, crn)
            except Exception as e:
                lines.append(f"{subj}{num}-{crn}: FETCH ERROR ({e})")
            else:
                lines.append(f"{subj}{num}-{crn}: {seats} seat(s), {wait} wait slot(s)")

        body = "\n".join(lines)
        print("📧 Sending status update:", " | ".join(lines))
        send_email(body)

        time.sleep(POLL_EVERY)

if __name__ == "__main__":
    main()
