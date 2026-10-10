# Strava Data Project

Pull every activity from your Strava account into a Postgres database, then explore your running history in a Streamlit dashboard: mileage by year, month and week, plus any custom date range.

## How it works

1. **Loader** (`strava_api.py`): uses your Strava API credentials to fetch all of your activities and writes them to an `activities` table in a [Neon](https://neon.tech) Postgres database. Each run replaces the table with a fresh copy.
2. **Dashboard** (`streamlit_app.py`): reads that table and charts your runs. It only shows activities whose sport type is `Run`, but the table has all of them.

You run the loader whenever you want fresh data, or on a schedule (see [Optional: Scheduled Refresh](#-optional-scheduled-refresh)).

## ✅ What you need

- A Strava account with some activities
- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- A free [Neon](https://neon.tech) account for the database
- About 20 minutes

## 🔐 Setup

### 1. Clone the repo and install dependencies

```bash
git clone https://github.com/g-leatherwood/strava-data-project.git
cd strava-data-project
uv sync
```

Without uv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use pip, drop the `uv run` prefix from the commands below.

### 2. Create a Strava API application

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api) and create an app. The name, website and icon can be anything.
2. Set **Authorization Callback Domain** to `localhost`.
3. Note the **Client ID** and **Client Secret**. You'll need both in step 4.

The "Your Access Token" shown on that page won't work for this project. It can only read your profile, not your activities. Step 5 gets a token that can.

### 3. Create a Neon database

1. Sign in to [Neon](https://console.neon.tech) and create a project. The default database is fine.
2. Click **Connect** and copy the connection string. It looks like:

   ```
   postgresql://user:password@ep-example-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

You don't need to create any tables. The loader does that on its first run.

### 4. Add your credentials to `.env`

Create a file named `.env` in the project folder:

```bash
STRAVA_CLIENT_ID=12345
STRAVA_CLIENT_SECRET=your_client_secret
DATABASE_URL_NEON=postgresql://user:password@ep-example-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
```

`.env` is in `.gitignore`, so it won't be committed.

### 5. Authorize the app to read your activities

This is a one-time step that gives the loader a refresh token it can keep using.

1. Open this URL in your browser, with your Client ID in place of `YOUR_CLIENT_ID`:

   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all
   ```

2. Click **Authorize**. Your browser then tries to open a `localhost` page and shows an error. That's expected.
3. Copy the `code` value from the address bar. In `http://localhost/?state=&code=abc123def456&scope=read,activity:read_all`, the code is `abc123def456`.
4. Exchange the code for tokens. The code only works once and expires within minutes, so do this right away:

   ```bash
   curl -X POST https://www.strava.com/oauth/token \
     -d client_id=YOUR_CLIENT_ID \
     -d client_secret=YOUR_CLIENT_SECRET \
     -d code=THE_CODE_FROM_STEP_3 \
     -d grant_type=authorization_code
   ```

5. The response is JSON. Copy its `refresh_token` into a new file named `strava_tokens.json` in the project folder:

   ```json
   {
     "refresh_token": "your_refresh_token"
   }
   ```

`activity:read_all` includes activities you've set to "Only You". Use `activity:read` in the URL instead if you only want activities others can see. `strava_tokens.json` is in `.gitignore`.

### 6. Load your data

From the project folder:

```bash
uv run python strava_api.py
```

The loader prints nothing to the terminal. It writes to `cron.log` in the project folder instead. A successful run ends with:

```
2026-01-15 17:01:13 INFO Successfully loaded data to Neon
```

It takes about a minute for a few thousand activities. Each run asks Strava for a new access token and saves it to `strava_tokens.json`, so you never have to repeat step 5 unless you revoke access.

Run the loader from the project folder: it looks for `strava_tokens.json` in the current directory.

## 📊 Run the dashboard

### On your computer

1. Create `.streamlit/secrets.toml` in the project folder:

   ```toml
   DATABASE_URL_NEON = "postgresql://user:password@ep-example-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
   ```

2. Start it:

   ```bash
   uv run streamlit run streamlit_app.py
   ```

It opens in your browser. Use the sidebar to pick a year and month. The **Custom Range** page in the sidebar charts any date range.

### On Streamlit Community Cloud (free hosting)

1. Fork this repo to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io), click **Create app**, and pick your fork with `streamlit_app.py` as the main file.
3. Under **Advanced settings**, set Python to 3.13 or newer, and under **Secrets** paste the same line as your `secrets.toml`:

   ```toml
   DATABASE_URL_NEON = "postgresql://..."
   ```

4. Deploy. The dashboard reads from Neon, so it updates whenever the loader runs.

## ⏰ Optional: Scheduled Refresh

To keep your data current without running the loader by hand, run it on a schedule from any always-on Linux machine, like a small cloud server:

1. On the server, do setup step 1, then copy your `.env` and `strava_tokens.json` into the project folder.
2. Add a cron job. `deploy/crontab.example` runs the loader twice a day. Edit its paths and times, then add it with `crontab -e`.

After that, run the loader only on the server. Strava can issue a new refresh token each time the loader runs, and the loader saves it locally. If two machines both run it, one machine's copy goes out of date and stops working.

`deploy/export_to_dropbox.sh` is an optional extra step. After a successful load, it exports every activity to a CSV and uploads it to Dropbox with [rclone](https://rclone.org/dropbox/), replacing the file each time. If the load fails, the export is skipped and the old CSV stays. It expects an rclone remote named `dropbox` and a CSV exporter at `~/bin/strava-cli`. Set `DROPBOX_DEST` or `STRAVA_CLI` to change either.

`cron.log` rotates at midnight and keeps 14 days.

## 🗄️ What's stored

One table, `activities`, with a row per activity:

| Column | What it is |
|---|---|
| `id`, `name`, `sport_type` | Strava's activity ID, title and type (`Run`, `Ride`, ...) |
| `start_date`, `start_date_local` | Start time in UTC and in local time |
| `distance_meters`, `distance_miles` | Distance |
| `moving_time`, `elapsed_time` | Time in seconds (`*_min` columns have minutes) |
| `average_speed`, `max_speed` | Meters per second (`*_pace_min_per_mile` columns have pace) |
| `total_elevation_gain` | Meters |
| `average_heartrate` | Beats per minute, if recorded |
| `race` | `1` if marked as a race on Strava |

## 🛠️ Troubleshooting

Check `cron.log` first. Every error the loader hits is written there.

- **`No valid refresh token found! Reauthorize your app.`**: `strava_tokens.json` is missing, or you ran the loader from another folder. Run it from the project folder, or redo setup step 5.
- **`Error fetching access token`**: the Client ID or Secret in `.env` is wrong, or the refresh token was revoked (for example, by removing the app under Strava's **Settings → My Apps**). Check `.env`, then redo step 5.
- **`Error fetching activities` with `activity:read_permission`**: the token was authorized without an activity scope. Redo step 5 with the exact URL shown.
- **`Error fetching activities` with status `429`**: you've hit Strava's [rate limits](https://developers.strava.com/docs/rate-limits/). Wait 15 minutes. Each run makes about one request per 100 activities.
- **`Failed to load data to Neon`**: check `DATABASE_URL_NEON` in `.env`. It should start with `postgresql://`.
- **Dashboard shows an error about `DATABASE_URL_NEON`**: create `.streamlit/secrets.toml` (or the Streamlit Cloud secret) as shown above. The dashboard doesn't read `.env`.

## 📁 Project structure

```
strava-data-project/
├── strava_api.py             # Loader: Strava → Neon
├── streamlit_app.py          # Dashboard
├── pages/Custom_Range.py     # Dashboard page for custom date ranges
├── deploy/                   # Optional: example crontab and Dropbox export
├── pyproject.toml, uv.lock   # Dependencies (uv)
└── requirements.txt          # Dependencies (pip)
```

Not committed: `.env`, `strava_tokens.json`, `.streamlit/secrets.toml`, `cron.log`.

## 🧠 Author

[Gabe Leatherwood](https://github.com/g-leatherwood)

Feel free to fork, deploy, or contribute!
