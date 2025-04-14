# Strava Data Project

This project fetches your running activity data from the Strava API and saves it into a MySQL database. It also includes a Streamlit dashboard to explore your training history by year, month, and week.

## 🚀 Features

- Authenticates with the Strava API using access & refresh tokens
- Fetches all activities via paginated API requests
- Calculates:
  - Distance (miles)
  - Moving/elapsed time (minutes)
  - Pace (min/mile)
- Stores data in a MySQL database
- Visualizes your mileage with a Streamlit dashboard
- Uses environment variables or Streamlit secrets for credentials

## 📁 Project Structure

```
strava-data-project/
├── strava_api.py             # Script to fetch data and load into MySQL  
├── streamlit_app.py          # Streamlit dashboard for viewing stats  
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

Set these in your system or `.env`:

- STRAVA_CLIENT_ID  
- STRAVA_CLIENT_SECRET  
- DATABASE_URL (e.g. `mysql+pymysql://user:pass@host/dbname`)

For Conda:

```bash
conda env config vars set STRAVA_CLIENT_ID=your_id
conda env config vars set STRAVA_CLIENT_SECRET=your_secret
conda env config vars set DATABASE_URL="your_db_url"
conda deactivate && conda activate yourenv
```

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

---

## 📊 Launch the Dashboard

For local testing, create `.streamlit/secrets.toml` with:

```toml
DATABASE_URL = "your_database_url"
```

Then run:

```bash
streamlit run streamlit_app.py
```

---

## 🛑 Important

Make sure `.gitignore` includes:

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
cryptography
streamlit
altair
```

---

## 🧠 Author

[Gabe Leatherwood](https://github.com/g-leatherwood)

Feel free to fork, deploy, or contribute!