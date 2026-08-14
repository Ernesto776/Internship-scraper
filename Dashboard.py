import pandas as pd
import plotly.express as px
import streamlit as st
import threading
import time
from db import get_connection, get_scraper_status, init_db, set_scraper_status
from Scraper import process_and_notify

st.set_page_config(page_title="Internship Tracker & Analytics", layout="wide")  

init_db()

def is_db_empty():
    # Returns true if Database empty
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM job_postings;")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count == 0   
    except Exception as e:
        print(f"Error checking DB row count: {e}")
        return True

def run_scraper_loop():
    # Runs the process_and_notify function every 15 minutes
    while True:
        try:
            process_and_notify()
        except Exception as e:
            print(f"Background scraper thread error: {e}")
        time.sleep(900)

if "scraper_thread_started" not in st.session_state:
    st.session_state["scraper_thread_started"] = True

    # Checks if empty on a cold boot
    if is_db_empty():
        with st.spinner(
            "First boot detected! Initializing database with Internships!"
        ):
            process_and_notify()          

    # Then it checks every 15 minutes, 24/7
    scraper_thread = threading.Thread(target=run_scraper_loop, daemon=True)
    scraper_thread.start()

# Sidebar control panel using db.py
st.sidebar.title("Control Panel")
current_status = get_scraper_status("scraper_status", "active")
is_active = current_status == "active"

st.sidebar.markdown(
    f"**Status:** {'🟢 ACTIVE' if is_active else '🔴 PAUSED'}"
)
if st.sidebar.button("Pause Notifications" if is_active else "Resume Scraper"):
    new_status = "paused" if is_active else "active"
    set_scraper_status("scraper_status", new_status)
    st.sidebar.info(f"Status changed to {new_status.upper()}!")
    st.rerun()

st.sidebar.markdown("---")

# Adds UI control to allow users to update information
with st.sidebar.expander("Settings & Configurations", expanded=True):
    # Update information, placeholder info added
    current_urls = get_scraper_status("target_urls", "")
    current_email = get_scraper_status("receiver_email", "")

    updated_urls = st.text_area(
        "Target URLs (One link per line):",
        value=current_urls,
        placeholder="https://example.com/target-page",
        height=120,
        help="Paste internship URLs here."
    )

    updated_email = st.text_input(
        "Alert reciever email",
        value=current_email,
        placeholder="your_email@example.com",
        help="Input email that will be alerted here."
    )

    if st.button("💾 Save Settings"):
        set_scraper_status("target_urls", updated_urls.strip())
        set_scraper_status("receiver_email", updated_email.strip())
        st.success("Settings updated successfully! Implementation will begin on the next run!")
        st.rerun()

    if st.sidebar.button("🔄 Run Scraping Check Now"):
        with st.spinner("Scrapping the inserted URLs..."):
            process_and_notify()
            st.cache_data.clear()
            st.sidebar.success("Check completed! Dashboard refreshed.")
            st.rerun()

st.sidebar.markdown("---")

# Main dashboard
st.title("Software Engineer Internship Tracker & Analytics")

# Fetch data from PostgreSQL
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM job_postings", conn)
        conn.close()
        if not df.empty and "scraped_at" in df.columns:
            df["scraped_at"] = pd.to_datetime(df["scraped_at"]).dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        return df
    except Exception as e:
        print(f"Error read from PostgreSQL: {e}")
        return pd.DataFrame(
            columns=[
                "id",
                "company",
                "title",
                "location",
                "date_added",
                "link",
                "scraped_at",
            ]
        )

try:
    df = load_data()

    # Top Key Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Roles Tracked", len(df))
    col2.metric("Unique Companies", df["company"].nunique() if not df.empty else 0)
    col3.metric(
        "Latest Update",
        df["scraped_at"].max() if not df.empty and "scraped_at" in df else "N/A",
    )

    st.markdown("---")

    # Data Table View & Analytics (Wrapped in empty state check)
    if not df.empty:
        st.subheader("Recent Internship Postings")

        # Adding clickable links
        display_cols = ["company", "title", "location", "date_added", "link"]
        available_cols = [c for c in display_cols if c in df.columns]
        
        st.dataframe(
            df[available_cols],
            column_config={
                "link": st.column_config.LinkColumn(
                    "Apply Link", display_text="Apply"
                ),
                "date_added": st.column_config.TextColumn("Date Posted"),
            },
            width="stretch"
        )

        # Analytics Section
        st.subheader("Hiring Insights & Metrics")
        col_left, col_right = st.columns(2)

        with col_left:
            # Chart 1: Top Companies Hiring
            top_companies = df["company"].value_counts().head(10).reset_index()
            top_companies.columns = ["Company", "Openings"]
            fig1 = px.bar(
                top_companies,
                x="Company",
                y="Openings",
                title="Top Companies by Openings",
            )
            st.plotly_chart(fig1, width="stretch")

        with col_right:
            # Chart 2: Top Locations
            top_locations = df["location"].value_counts().head(10).reset_index()
            top_locations.columns = ["Location", "Count"]
            fig2 = px.pie(
                top_locations,
                names="Location",
                values="Count",
                title="Geographic Distribution",
            )
            st.plotly_chart(fig2, width="stretch")
    else:
        st.info(
            "No internship postings found in the database yet. Run"
            " `scraper.py` to populate records!"
        )

except Exception as e:
    st.error(f"Error loading dashboard: {e}")