# Strava Data Project

This project fetches your activity data from the Strava API and saves it into a MySQL database for analysis.

## 🚀 Features
- Authenticates with the Strava API using access & refresh tokens
- Fetches all activity data via paginated API requests
- Stores structured data in a MySQL database
- Uses environment variables for credentials and database connection

## 📁 Project Structure
```
strava-data-project/
├── strava_api.py             # Main script
├── strava_tokens.json        # Stores access/refresh tokens (not committed)
├── .gitignore                # Prevents secrets from being tracked
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## 🔐 Setup Instructions

### 1. Clone the Repo (or copy the folder)
```bash
git clone https://github.com/yourusername/strava-data-project.git
cd strava-data-project
```

### 2. Set Environment Variables
Set the following in your system or in a `.env` file (and use `python-dotenv` to load it, if desired):
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `DATABASE_URL` (e.g. `mysql+pymysql://root:password@localhost/strava_db`)

If you're using conda:
```bash
conda env config vars set STRAVA_CLIENT_ID=your_id_here
conda env config vars set STRAVA_CLIENT_SECRET=your_secret_here
conda env config vars set DATABASE_URL="your_mysql_url_here"
conda deactivate && conda activate yourenvname
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Authorize and Generate Tokens
- Go to the Strava authorization URL to get a fresh `code`
- Exchange it using a helper script or manually via API
- Save your `access_token` and `refresh_token` in `strava_tokens.json`

Example format:
```json
{
  "access_token": "...",
  "refresh_token": "..."
}
```

### 5. Run the Script
```bash
python strava_api.py
```

## 🛑 Important
- **DO NOT COMMIT `strava_tokens.json` or `.env`**
- Ensure `.gitignore` contains:
```
strava_tokens.json
.env
```

---

## 📦 Dependencies (from `requirements.txt`)
```text
requests
pandas
SQLAlchemy
PyMySQL
```

---

## 📈 Ideas for Next Steps
- Build a dashboard in Streamlit or Power BI
- Schedule the script to run weekly or daily
- Connect to cloud MySQL or SQLite for portability

---

## 🧠 Author
[Gabe Leatherwood](https://github.com/g-leatherwood)

Feel free to fork or contribute!