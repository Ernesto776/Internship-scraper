import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Internship Tracker & Analytics", layout="wide")

def get_scraper_status():
    try:
        conn = sqlite3.connect("internships.db")
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        cursor.execute("SELECT value FROM settings WHERE key = 'scraper_status'")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 'active'
    except Exception:
        return "active"

def set_scraper_status(status):
    # Sets to either 'Active' or 'Paused'
    conn = sqlite3.connect("internships.db")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    )
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('scraper_status', ?)",
        (status,),
    )
    conn.commit()
    conn.close()

# Sidebar control panel
st.sidebar.title("Control Panel")
current_status = get_scraper_status()

if current_status == "active":
    st.sidebar.success("🟢 Scraper Status: ACTIVE")
    if st.sidebar.button("Pause notifications"):
        set_scraper_status("Paused")
        st.sidebar.warning("Notifications paused!")
        st.rerun()
else:
    st.sidebar.error("🔴 Scraper Status: PAUSED")
    if st.sidebar.button("Resume notifications"):
        set_scraper_status("Active")
        st.sidebar.success("Notifications active!")
        st.rerun()
st.sidebar.markdown("---")

# Main dashboard
st.title("Software Engineer Internship Tracker & Analytics")

# Fetch data from SQLite
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = sqlite3.connect("internships.db")
        df = pd.read_sql_query("SELECT * FROM job_postings", conn)
        conn.close()
        return df
    except Exception:
        # Return empty DataFrame with expected schema if DB doesn't exist yet
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
            use_container_width=True
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
            st.plotly_chart(fig1, use_container_width=True)

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
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info(
            "No internship postings found in the database yet. Run"
            " `scraper.py` to populate records!"
        )

except Exception as e:
    st.error(f"Error loading dashboard: {e}")