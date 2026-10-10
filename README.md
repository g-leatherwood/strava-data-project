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
├── strava_api_neon.py        # Neon-only loader, for scheduled runs  
├── streamlit_app.py          # Streamlit dashboard for viewing stats  
├── deploy/                   # Optional: example crontab and Dropbox export  
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

## ⏰ Optional: Scheduled Refresh

If you want your data to stay current without running the loader by hand, you can run it on a schedule from any always-on Linux machine, like a small cloud server. `deploy/` has a starting point:

- `deploy/crontab.example`: runs `strava_api_neon.py` twice a day. Edit the paths and times, then add it with `crontab -e`.
- `deploy/export_to_dropbox.sh` (optional): after a successful refresh, exports every activity to a CSV and uploads it to Dropbox with [rclone](https://rclone.org/dropbox/), replacing the file each time. If the refresh fails, the export is skipped and the old CSV stays. It expects an rclone remote named `dropbox` and a CSV exporter at `~/bin/strava-cli`. Set `DROPBOX_DEST` or `STRAVA_CLI` to change either.

`strava_api_neon.py` writes its own log, `cron.log`, next to the script. It rotates at midnight and keeps 14 days.

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