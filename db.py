from datetime import datetime, timedelta
import os
import re
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/internships"
)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    # The central scheme initialization for PostgreSQL
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_postings (
            id SERIAL PRIMARY KEY,
            company VARCHAR(255),
            title VARCHAR(255),
            location VARCHAR(255),
            date_added VARCHAR(100),
            link TEXT,
            source_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Stores Key-Value
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT
            )
        """)

    # Ensures that the link exists since the program ran previously
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key VARCHAR(255) PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Changed to allow  status, URLs, and emails to come from db 
def get_scraper_status(key, default_value=""):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row[0] if (row and row [0] is not None) else default_value
    except Exception as e:
        print(f"Database read notice for '{key}': {e}")
        return default_value

def set_scraper_status(key, value):
    # Saves and updates based on the key and value pair
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO settings (key, value) 
        VALUES (%s, %s)
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDE.value;
    """
    cursor.execute(query, (key, str(value)))

    conn.commit()
    cursor.close()
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