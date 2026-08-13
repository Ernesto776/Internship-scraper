from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import re
import smtplib
import sqlite3
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests

load_dotenv()

# --- CONFIGURATION ---
TARGET_URL = os.getenv("TARGET_URL", "https://example.com/target-page")
SENDER_EMAIL = os.getenv("ALERT_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.getenv("ALERT_PASSWORD", "your_app_password")
RECEIVER_EMAIL = os.getenv("ALERT_RECEIVER", "your_email@gmail.com")

def parse_posted_date(age_str):
    # Used to convert strings like "2d ago" or "3h ago" into MM-DD-YYYY format
    if not age_str:
        return datetime.now().strftime("%b-%d-%Y")

    age_str = age_str.lower().strip()
    today = datetime.now()

    # Match days to date (2d, 10d, etc.)
    days_match = re.search(r"(\d+)\s*d", age_str)
    if days_match:
        days_ago = int(days_match.group(1))
        return (today - timedelta(days=days_ago)).strftime("%b-&d-%Y")

    # Count as today if site uses h or m 
    if "h" in age_str or "m" in age_str or "today" in age_str:
        return today.strftime("%b-%d-%Y")

    # Return the date if already formatted
    return age_str if len(age_str) > 0 else today.strftime("%b-%d-%Y")

def init_db():
    """Ensures the SQLite database and schema exist."""
    conn = sqlite3.connect("internships.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_postings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            title TEXT,
            location TEXT,
            date_added TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Ensures that the link exists since the program ran previously
    cursor.execute("PRAGMA table_info(job_postings)")
    columns = [col[1] for col in cursor.fetchall()]
    if "link" not in columns:
        cursor.execute("ALTER TABLE job_postings ADD COLUMN link TEXT")

    conn.commit()
    conn.close()

def fetch_postings(url):
    """Fetches and parses postings from the target URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko), Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        parsed_jobs = []

        # Example parsing logic: adapt based on target site HTML structure
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                company = cols[0].get_text(strip=True)
                title = cols[1].get_text(strip=True)
                location = cols[2].get_text(strip=True)
                raw_date = cols[3].get_text(strip=True)

                # Parse the age to the date
                formatted_date = parse_posted_date(raw_date)

                # Extract the application link
                link_tag = row.find("a", href=True)
                apply_link = link_tag["href"] if link_tag else "#"

                parsed_jobs.append({
                    "company":company,
                    "title":title,
                    "location":location,
                    "date_added":formatted_date,
                    "link":apply_link,
                })

        return parsed_jobs
    except Exception as e:
        print(f"Notice: Could not fetch URL directly ({e}).")
        return []

def send_email_alert(new_postings):
    """Sends an HTML formatted email summary of newly added job postings."""
    if not new_postings:
        return

    subject = f"{len(new_postings)} New Internship Postings Detected!"

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
        """
    for job in new_postings:
        html_content += f"""
            <tr>
                <td><b>{job['company']}</b></td>
                <td>{job['title']}</td>
                <td>{job['location']}</td>
                <td>{job['date_added']}</td>
                <td style="text-align: center;">
                    <a href="{job['link']}" target="_blank"
                        style="background-color: #2a8a5e; color:white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">
                        Apply now
                    </a>
                </td>
            </tr>
            """
    html_content += "</table>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print(f"Alert email successfully sent to {RECEIVER_EMAIL}")
    except Exception as e:
        print(f"Failed to send email alert: {e}")

def process_and_notify(scraped_postings):
    """Deduplicates records against SQLite, saves new entries, and sends alerts."""
    conn = sqlite3.connect("internships.db")
    cursor = conn.cursor()

    new_postings = []

    for job in scraped_postings:
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
                        INSERT INTO job_postings (company, title, location, date_added, link)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                (
                    job["company"],
                    job["title"],
                    job["location"],
                    job["date_added"],
                    job["link"],
                ),
            )
            new_postings.append(job)

    conn.commit()
    conn.close()

    if new_postings:
        print(
            f"Inserted {len(new_postings)} new posting(s). Triggering email..."
        )
        send_email_alert(new_postings)
    else:
        print("ℹNo new postings found. Everything is up to date.")

if __name__ == "__main__":
    init_db()

    # 1. Fetch live web postings
    postings = fetch_postings(TARGET_URL)

    # 2. Fallback to mock data for local testing if URL isn't configured
    if not postings:
        print("Running in test mode with sample data...")
        today_str = datetime.now().strftime("%b-%d-%Y")
        postings = [
            {
                "company": "Google",
                "title": "Software Engineer Intern",
                "location": "Mountain View, CA",
                "date_added": today_str,
                "link": "https://careers.google.com",
            },
            {
                "company": "Microsoft",
                "title": "Explore Intern",
                "location": "Redmond, WA",
                "date_added": today_str,
                "link": "https://careers.microsoft.com",
            },
            {
                "company": "Apple",
                "title": "Hardware/SWE Intern",
                "location": "Cupertino, CA",
                "date_added": parse_posted_date("2d ago"),
                "link": "https://www.apple.com/careers/us/work-at-apple/locations.html",
            },
        ]

    # 3. Process postings and trigger notifications
    process_and_notify(postings)
