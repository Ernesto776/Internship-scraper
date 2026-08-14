from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import signal
import smtplib
import sqlite3
import sys
import time
from bs4 import BeautifulSoup
from db import get_connection, get_scraper_status, init_db, parse_posted_date
from dotenv import load_dotenv
import requests

load_dotenv()

# --- .env FALLBACK CONFIGURATION ---
# Gets the raw URLs and loops through them
URL_LIST = os.getenv("TARGET_URLS", "https://example.com/target-page")
TARGET_URLS = [url.strip() for url in URL_LIST.split(",") if url.strip()]

# Configure the sending and receiving email
SENDER_EMAIL = os.getenv("ALERT_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.getenv("ALERT_PASSWORD", "your_app_password")
RECEIVER_EMAIL = os.getenv("ALERT_RECEIVER", "your_email@gmail.com")

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL", "900"))

RUNNING = True

def shutdown_logic(sig, frame):
    # Handles the shutdown cleanly
    global RUNNING
    print("\nShutting down, finishing tasks to exit!")
    RUNNING = False
    print("Interships no longer automatic!")

def is_scraper_enabled():
    return get_scraper_status("scraper_status", "active") == "active"

def fetch_postings(url):
    """Fetches and parses postings from one URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko), Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        parsed_jobs = []

        # Example parsing logic: adapt based on target site HTML structure
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                # Extract the application link
                link_tag = row.find("a", href=True)
                parsed_jobs.append({
                    "company": cols[0].get_text(strip=True),
                    "title": cols[1].get_text(strip=True),
                    "location": cols[2].get_text(strip=True),
                    "date_added": parse_posted_date(cols[3].get_text(strip=True)),
                    "link": link_tag["href"]if link_tag else "#",
                    "source_url":url,
                })

        return parsed_jobs
    except Exception as e:
        print(f"Notice: Could not fetch {url}: ({e}).")
        return []

def send_email_alert(new_postings, recipient=None):
    """Sends an HTML formatted email summary of newly added job postings."""
    if not new_postings:
        return

    target_recipient = recipient if recipient else RECEIVER_EMAIL
    subject = f"{len(new_postings)} New Internship Postings Detected!"

    html_rows = "".join([
        f""" 
            <tr>
                <td><b>{job['company']}</b></td>
                <td>{job['title']}</td>
                <td>{job['location']}</td>
                <td>{job['date_added']}</td>
                <td style="text-align: center;">
                    <a href="{job['link']}" target="_blank"
                        style="background-color: #2a8a5e; color:white; padding: 6px 12px;"
                        " text-decoration: none; border-radius: 4px; font-weight: bold; "
                        "display: inline-block;">
                        Apply now
                    </a>
                </td>
            </tr>
            """
        for job in new_postings
    ])

    html_content = f"""
        <h2>New Internship Postings Added:</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color: #f2f2f2;">
                <th>Company</th>
                <th>Role Title</th>
                <th>Location</th>
                <th>Date Added</th>
                <th>Action</th>
            </tr>
            {html_rows}
        </table>
        """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = target_recipient
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, target_recipient, msg.as_string())
        print(f"Alert email successfully sent to {target_recipient}")
    except Exception as e:
        print(f"Failed to send email alert: {e}")

def process_and_notify():
    # Checks if the automation is enabled
    if not is_scraper_enabled():
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] " +
            "The automation is currently paused, skipping checks..."
        )
        return

    raw_urls = get_scraper_status("target_urls", URL_LIST)
    target_urls = [
        url.strip() for url in raw_urls.replace("\n", ",").split(",") if url.strip()
    ]
    receiver_email = get_scraper_status("receiver_email", RECEIVER_EMAIL)

    all_scraped_postings = []

    # Step 1: Gathers posts from all the URLs
    for url in target_urls:
        print(f"Checking: {url}")
        all_scraped_postings.extend(fetch_postings(url))

    if not all_scraped_postings:
        print("No postings were found during this run.")
        return

    # Step 2: Remove duplicates
    conn = get_connection()
    cursor = conn.cursor()
    new_postings = []

    for job in all_scraped_postings:
        # Check if entry already exists
        cursor.execute(
            """
                SELECT id FROM job_postings 
                WHERE company = ? AND title = ? AND location = ?
            """,
            (job["company"], job["title"], job["location"]),
        )

        if cursor.fetchone() is None:
            cursor.execute(
                """
                        INSERT INTO job_postings (company, title, location, date_added, link, source_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                (
                    job["company"],
                    job["title"],
                    job["location"],
                    job["date_added"],
                    job["link"],
                    job.get("source_url", ""),
                ),
            )
            new_postings.append(job)

    conn.commit()
    conn.close()

    # Step 3: Send an email if theres a new update
    if new_postings:
        print(
            f"Inserted {len(new_postings)} new posting(s). Triggering email..."
        )
        send_email_alert(new_postings, recipient=receiver_email)
    else:
        print("ℹNo new postings found. Everything is up to date.")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_logic)
    signal.signal(signal.SIGTERM, shutdown_logic)

    init_db()

    print("Starting the automated internship monitor!")
    print(f"checking {len(TARGET_URLS)} URL(s) every {CHECK_INTERVAL_SECONDS} seconds. \n")
    print("To stop the program press 'Ctrl + C'.\n")

    # Begin monitoring loop
    while RUNNING:
        try:
            process_and_notify()
        except Exception as e:
            print(f"An error occured during execution: {e}")

        # Interruptable sleep loop
        for _ in range(CHECK_INTERVAL_SECONDS):
            if not RUNNING:
                break
            time.sleep(1)

    print("Program stopped successfully, automation ending...")
    sys.exit(0) 