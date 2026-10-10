# Strava Data Project

Python ETL pipeline that retrieves running activity data from the Strava API, stores it in a SQL database (MySQL for local development and Postgres via Neon for deployment), and includes a Streamlit dashboard to explore training history by year, month, and week.

## 🚀 Features

- Authenticates with the Strava API using access & refresh tokens
- Fetches all activities via paginated API requests
- Calculates:
  - Distance (miles)
  - Moving/elapsed time (minutes)
  - Pace (min/mile)
- Loads data into both MySQL and Neon (Postgres)
- Visualizes mileage and trends in a Streamlit dashboard
- Uses environment variables or Streamlit secrets for credentials

## 📁 Project Structure

```
strava-data-project/
├── strava_api.py             # Script to fetch data and load into MySQL + Neon  
├── strava_api_neon.py        # Neon-only loader, run by cron on the droplet  
├── streamlit_app.py          # Streamlit dashboard for viewing stats  
├── deploy/                   # Droplet crontab and Dropbox export script  
├── strava_tokens.json        # Stores Strava tokens (excluded from git)  
├── requirements.txt          # Python dependencies  
├── .gitignore                # Prevents secrets & token files from tracking  
└── README.md                 # This file
```

## 🔐 Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/g-leatherwood/strava-data-project.git
cd strava-data-project
```

### 2. Set Environment Variables

Create a .env file in your project directory and define the following:

- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `DATABASE_URL` (for MySQL)
- `NEON_DATABASE_URL` (for Neon Postgres)

These will be acessed in the strava_api.py script. Make sure your .gitignore includes .env files.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Authorize with Strava

Use the Strava OAuth link to get a `code`, then exchange it for an `access_token` and `refresh_token`.

Create a `strava_tokens.json` file:

```json
{
  "access_token": "your_token_here",
  "refresh_token": "your_refresh_token_here"
}
```

### 5. Run the Data Loader

```bash
python strava_api.py
```

✅ This will load your Strava data into **both MySQL and Neon**.

---

## 📊 Launch the Dashboard

### Local Testing

1. Create a `.streamlit/secrets.toml` file:

```toml
DATABASE_URL = "your_neon_database_url"
```

2. Run Streamlit:

```bash
streamlit run streamlit_app.py
```

### Deploy on Streamlit Cloud

1. Push your code to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Click **New App** → Connect your GitHub repo
4. Set your secret in **"App Settings" > "Secrets"**:

```toml
DATABASE_URL = "your_neon_database_url"
```

5. Deploy and share the link!

---

## 🌐 Neon Postgres Setup

1. Go to [neon.tech](https://neon.tech)
2. Create a new project
3. Copy the **connection string** for your Python app
4. Save it as `NEON_DATABASE_URL` in your environment or Streamlit secrets

---

## ⏰ Scheduled Refresh (Droplet)

A DigitalOcean droplet runs `strava_api_neon.py` at 5pm and 11pm Central. After each successful refresh, it exports every activity to `strava_all.csv` in Dropbox (`Apps/strava-export-gabe/`), replacing the previous file. If the refresh fails, the export is skipped and the old CSV stays.

The files in `deploy/` are the source of truth for this setup:

- `deploy/crontab`: the cron schedule. Install with `crontab deploy/crontab`, which replaces root's whole crontab.
- `deploy/export_to_dropbox.sh`: install at `/root/bin/export_to_dropbox.sh`. It uses `strava-cli` (a separate repo) at `/root/bin/strava-cli`, which reads `DATABASE_URL_NEON` from `~/.config/strava-cli/.env`, and an rclone remote named `dropbox`.

Logs:

- `/root/cron.log`: Dropbox export output (and any crash output from either step).
- `/root/strava-data-project/cron.log`: refresh output, rotated at midnight, with 14 days kept.

---

## 🛑 Important

Make sure your `.gitignore` includes:

```
strava_tokens.json
.env
.streamlit/secrets.toml
```

---

## 📦 requirements.txt

```
requests
pandas
SQLAlchemy
PyMySQL
psycopg2-binary
cryptography
streamlit
altair
```

---

## 🧠 Author

[Gabe Leatherwood](https://github.com/g-leatherwood)

Feel free to fork, deploy, or contribute!