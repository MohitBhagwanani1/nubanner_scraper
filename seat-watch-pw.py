#!/usr/bin/env python3
import os
import time
import json
import smtplib
import requests
from email.message import EmailMessage
from dotenv import load_dotenv

# ─── Load .env ────────────────────────────────────────────────────────────────
load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────
TERM       = "202550"  # Summer 1 2025
COURSES    = [
    ("CSYE", "7374", "53300"),  # CSYE 7374, 02
    ("CSYE", "7374", "53789"),  # CSYE 7374, 03
]
POLL_EVERY = 180  # seconds between emails
# ────────────────────────────────────────────────────────────────────────────

# ─── Your browser cookies ────────────────────────────────────────────────────
JSESSIONID      = os.getenv("JSESSIONID")
NUBANNER_COOKIE = os.getenv("NUBANNER_COOKIE")
# ────────────────────────────────────────────────────────────────────────────

# ─── SMTP settings ───────────────────────────────────────────────────────────
SMTP_USER  = os.getenv("SMTP_USER")
SMTP_PASS  = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO   = os.getenv("EMAIL_TO", SMTP_USER)
# ────────────────────────────────────────────────────────────────────────────

def send_email(body: str):
    msg = EmailMessage()
    msg["Subject"] = "Course Waitlist Status Update"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.set_content(body)
    print("body", body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)

def build_session():
    sess = requests.Session()
    # Banner’s session cookie:
    sess.cookies.set("JSESSIONID",      JSESSIONID,
                     domain="nubanner.neu.edu", path="/StudentRegistrationSsb")
    # Banner’s authorization cookie:
    sess.cookies.set("nubanner-cookie", NUBANNER_COOKIE,
                     domain="nubanner.neu.edu", path="/")
    return sess

def authorize_term(sess):
    """
    Tells Banner which term we want. Must do this once per session
    or /searchResults will always return zeros.
    """
    url = "https://nubanner.neu.edu/StudentRegistrationSsb/ssb/term/search?mode=search"
    payload = {
        "term": TERM,
        "studyPath": "",
        "studyPathText": "",
        "startDatepicker": "",
        "endDatepicker": ""
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    r = sess.post(url, data=payload, headers=headers, timeout=10)
    r.raise_for_status()

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
    if not j.get("success", True):
        raise RuntimeError(f"Search API returned success=false: {j!r}")
    for d in j.get("data", []):
        if d["courseReferenceNumber"] == crn:
            return d["seatsAvailable"], d["waitAvailable"], d["waitListPosition"]
    return 0, 0, None  # If not found, return 0 seats, 0 waitlist, and None for position

def main():
    session = build_session()

    try:
        authorize_term(session)
    except Exception as e:
        print("❌ Failed to authorize term:", e)
        return

    lines = []
    for subj, num, crn in COURSES:
        try:
            seats, wait, wait_position = fetch_for(session, subj, num, crn)
            waitlist_status = f"Waitlist Position: {wait_position}" if wait_position else "No waitlist"
        except Exception as e:
            lines.append(f"{subj}{num}-{crn}: FETCH ERROR ({e})")
        else:
            lines.append(f"{seats} seat(s), {wait} wait slot(s), {waitlist_status}")

    body = "\n".join(lines)
    print("📧 Sending status update:", " | ".join(lines))
    send_email(body)

if __name__ == "__main__":
    main()
