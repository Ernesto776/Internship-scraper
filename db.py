from datetime import datetime, timedelta
import re
import sqlite3

DB_NAME = "internships.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    # The central scheme initialization
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_postings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            title TEXT,
            location TEXT,
            date_added TEXT,
            link TEXT,
            source_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Stores Key-Value
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

    # Ensures that the link exists since the program ran previously
    cursor.execute("PRAGMA table_info(job_postings)")
    columns = [col[1] for col in cursor.fetchall()]
    if "link" not in columns:
        cursor.execute("ALTER TABLE job_postings ADD COLUMN link TEXT")
    if "source_url" not in columns:
        cursor.execute("ALTER TABLE job_postings ADD COLUMN source_url TEXT")

    conn.commit()
    conn.close()

# Changed to allow  status, URLs, and emails to come from db 
def get_scraper_status(key, default_value=""):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if (row and row [0] is not None) else default_value
    except Exception:
        return default_value

def set_scraper_status(key, value):
    # Saves and updates based on the key and value pair
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key,str(value)),
    )
    conn.commit()
    conn.close()

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
        return (today - timedelta(days=days_ago)).strftime("%b-%d-%Y")

    # Count as today if site uses h or m 
    if "h" in age_str or "m" in age_str or "today" in age_str:
        return today.strftime("%b-%d-%Y")

    # Return the date if already formatted
    if len(age_str) > 0:
        return age_str 
    else: 
        return today.strftime("%b-%d-%Y")