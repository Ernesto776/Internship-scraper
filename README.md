# Automated Internship Tracker & Analytics

An automated, full-stack monitoring system that scrapes internship postings or other types of job postings, persists records to a cloud PostgreSQL database, alerts users via automated email summaries by automatically checking every 15 minutes, and displays trends on an interactive Streamlit dashboard.

---

## Architecture & Features

- **Automated Web Scraper:** Crawls target internship posting URLs and parses structured job details.
- **GitHub Actions Scheduled Worker:** Runs serverless background scraping tasks every 15 minutes on a cron schedule without keeping local servers active.
- **Render PostgreSQL Database:** Manages relational persistence, tracking active settings and deduplicating job postings based on company, role, and location.
- **Interactive Streamlit Dashboard:** Visualizes company hiring trends, geographic distributions, and tracked positions with direct application links.
- **Custom Email Alerts:** Triggers HTML-formatted email alerts to specified recipients whenever brand-new positions are detected.
- **Dynamic Control Panel:** Allows toggling scraper status, updating target source URLs, and modifying alert recipient emails directly from the UI.

---

## Tech Stack

- **Frontend / Dashboard:** Streamlit, Plotly Express, Pandas
- **Scraper & Logic:** Python, BeautifulSoup4, Requests
- **Database:** PostgreSQL (`psycopg2`)
- **Automation / CI/CD:** GitHub Actions (Cron Workflow)
- **Deployment:** Render (Database & Web Service)
- **Alerting:** SMTP (`smtplib`, `email.mime`)

---

## Environment Variables

Create a `.env` file in the project root directory with the following configuration:

`.env`
- DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require
- ALERT_EMAIL=your_sender_email@gmail.com
- ALERT_PASSWORD=your_gmail_app_password
- ALERT_RECEIVER=your_recipient_email@example.com
- TARGET_URLS=[https://example.com/job-board-1,https://example.com/job-board-2](https://example.com/job-board-1,https://example.com/job-board-2)

---

## Setup

### Do first (Sender Email)

- Two email accounts are needed (A sender and receiver)
- If the sending account is a gmail, it is recommended to use an app password, don't insert your actual password (2-Factor Authentication required) [https://myaccount.google.com/apppasswords].

### Render (For GUI and Postgres database) [https://render.com/]

1. Create a free account
2. Create a project and name it, then create a new Postgres, just change the membership to free (unless you need more storage)
3. When completed, click the `Connect` button, use the internal URL for the Render `DATABASE_URL` and the external URL for the Github `DATABASE_URL`

4. Create a web service and use the github link to insert in the `Public Git Repository`
5. insert [streamlit run Dashboard.py --server.port $PORT --server.address 0.0.0.0] in the Start Command
6. Choose free option (or not, if you got money like that)
7. Choose `Add from .env` (Scroll up to `## Environment Variables`)

### Github automation
1. Fork the repository
2. To begin the automation process go to Settings > Secrets and Variables > Actions
3. Click the `New Repository Secret` button and insert the key (example: `ALERT_EMAIL`), and the value (example: exampleEmail@email.com), one at a time (Do this for the ALERT_EMAIL, ALERT_PASSWORD, ALERT_RECEIVER, and DATABASE_URL [use external database URL])
4. Once completed, to go run go to, Actions > Automated Internship Scraper > Run Workflow > Run Workflow

If you want to visit the GUI version visit the Render website and in your project go to the web service created earlier and hit the purple url link or you can also go to Manual Deploy > Deploy latest commit 