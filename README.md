# Strava Data Project

Pull every activity from your Strava account into a Postgres database, then explore your running history in a Streamlit dashboard: mileage by year, month and week, plus any custom date range.

## How it works

1. **Loader** (`strava_api.py`): uses your Strava API credentials to fetch all of your activities and writes them to an `activities` table in a [Neon](https://neon.tech) Postgres database, along with the shoe you wore and the town each activity started in. Each run updates the table in place: new activities are added, changed ones are overwritten, and ones you deleted on Strava are removed.
2. **Dashboard** (`streamlit_app.py`): reads that table and charts your runs. It only shows activities whose sport type is exactly `Run` (so not `TrailRun` or `VirtualRun`), but the table has all of them.

You run the loader whenever you want fresh data, or on a schedule (see [Optional: Scheduled Refresh](#optional-scheduled-refresh)).

## What you need

- A Strava account with some activities
- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- A free [Neon](https://neon.tech) account for the database
- About 20 minutes

## Setup

### 1. Clone the repo and install dependencies

```bash
git clone https://github.com/g-leatherwood/strava-data-project.git
cd strava-data-project
uv sync
```

Without uv (`python3 --version` must be 3.13 or newer):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use pip, drop the `uv run` prefix from the commands below, and run `source .venv/bin/activate` again in each new terminal.

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
     -d code=YOUR_CODE \
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

Run the loader from the project folder, because it looks for `strava_tokens.json` in the current directory:

```bash
uv run python strava_api.py
```

The loader logs its progress to the terminal. A successful run ends with:

```
2026-01-15 17:01:13 INFO Successfully loaded data to Neon
```

It takes about a minute for a few thousand activities. Each run uses the refresh token to get a new access token from Strava and saves the latest tokens to `strava_tokens.json`, so you don't have to repeat step 5 unless you revoke access.

## Run the dashboard

### On your computer

The dashboard reads `DATABASE_URL_NEON` from the same `.env` as the loader (setup step 4), so there's nothing else to configure. Start it:

```bash
uv run streamlit run streamlit_app.py
```

It opens in your browser. Use the sidebar to pick a year and month. The **Custom Range** page in the sidebar charts any date range.

The dashboard caches your data when it starts, so it won't show activities loaded after that. Restart it (Ctrl+C, then run the command again) to pick up new data.

### On Streamlit Community Cloud (free hosting)

1. Fork this repo to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io), click **Create app**, and pick your fork with `streamlit_app.py` as the main file.
3. Under **Advanced settings**, set Python to 3.13 or newer, and under **Secrets** paste this line, with the connection string from your `.env`:

   ```toml
   DATABASE_URL_NEON = "postgresql://..."
   ```

   The hosted app reads this secret instead of `.env`, which isn't committed. A local `.streamlit/secrets.toml` with the same line works too, and wins over `.env`.

4. Deploy.

The hosted dashboard also caches your data. To see newly loaded activities, open your app's **Manage app** panel and choose **Reboot app**. An app that went to sleep after a stretch with no visitors also starts fresh when it wakes up.

## Optional: Scheduled Refresh

To keep your data current without running the loader by hand, run it on a schedule from any always-on Linux machine, like a small cloud server:

1. On the server, do setup step 1, then copy your `.env` and `strava_tokens.json` into the project folder.
2. Add a cron job. `deploy/crontab.example` runs the loader twice a day. Edit its paths and times, then add it with `crontab -e`.
3. Rotate the log. `deploy/logrotate.example` keeps 14 days of it. Edit its path, then copy it to `/etc/logrotate.d/`.

After that, run the loader only on the server. Strava can issue a new refresh token each time the loader runs, and the loader saves it on the machine that ran it. If two machines both run it, one machine's copy goes out of date and stops working.

The cron job writes everything the run prints to `logs/cron.log` in the project folder, including errors from before the loader starts, such as a missing package.

## What's stored

Two tables. `activities` has a row per activity:

| Column | What it is |
|---|---|
| `id`, `name`, `sport_type` | Strava's activity ID, title and type (`Run`, `Ride`, ...) |
| `start_date`, `start_date_local` | Start time in UTC and in local time |
| `distance_meters`, `distance_miles` | Distance |
| `moving_time`, `elapsed_time` | Time in seconds (`*_min` columns have minutes) |
| `average_speed`, `max_speed` | Meters per second (`*_pace_min_per_mile` columns have pace) |
| `total_elevation_gain` | Meters |
| `average_heartrate` | Beats per minute, if recorded |
| `race` | `1` if marked as a race on Strava (`workout_type` has Strava's own value) |
| `city`, `county`, `state`, `country` | The nearest town to where the activity started, looked up offline from [GeoNames](https://www.geonames.org) data. Empty for activities without GPS, such as manual entries |
| `start_lat`, `start_lng`, `end_lat`, `end_lng` | Start and end coordinates |
| `summary_polyline` | The route outline, in Google's [encoded polyline](https://developers.google.com/maps/documentation/utilities/polylinealgorithm) format |
| `timezone` | Strava's timezone for the activity |
| `gear_id`, `gear_name` | The shoe (or bike) used. Several shoes can share a name, so group by `gear_id` to tell them apart |
| `device_name`, `trainer`, `commute`, `manual`, `private`, `visibility` | Recording device and Strava's flags (`trainer` means a treadmill or indoor trainer) |
| `max_heartrate`, `average_cadence`, `average_temp`, `elev_high`, `elev_low`, `suffer_score` | More stats, if recorded. `suffer_score` is Strava's Relative Effort |
| `average_watts`, `weighted_average_watts`, `max_watts`, `kilojoules` | Power, if recorded |
| `kudos_count`, `comment_count`, `achievement_count`, `pr_count`, `athlete_count`, `total_photo_count` | Counts from Strava |
| `raw` | The whole activity as Strava sent it (JSON), for any field without its own column |

`gear` has a row per shoe or bike you've used: `id`, `name`, `brand_name`, `model_name`, `nickname`, `description`, `distance_meters` and `distance_miles` (Strava's running total), `retired`, `is_primary` and `raw`. The loader looks up each one once, and after that only the ones you haven't retired, since their mileage keeps changing.

Both tables use Strava's ID as the primary key, so the database refuses a second row for the same activity or shoe.

The coordinates and routes show where you run, including from home, so keep the database private.

**Upgrading from an older version:** older versions dropped and rebuilt the table on every run. The first run of this version keeps that old table as `activities_backup`. Once you've checked the new one, remove the backup by running `DROP TABLE activities_backup;` in Neon's SQL Editor.

## Troubleshooting

Check the loader's output first: the terminal for a manual run, or `logs/cron.log` on a server. Every error the loader hits is logged.

- **`No valid refresh token found! Reauthorize your app.`**: `strava_tokens.json` is missing, or you ran the loader from another folder. Run it from the project folder, or redo setup step 5.
- **`Error fetching access token`**: the Client ID or Secret in `.env` is wrong, or the refresh token was revoked (for example, by removing the app under Strava's **Settings → My Apps**). Check `.env`, then redo step 5.
- **`Error fetching activities` with `activity:read_permission`**: the token was authorized without an activity scope. Redo step 5 with the exact URL shown.
- **`Error fetching activities` with status `500`-`504`**: Strava's servers had a problem. The loader retries these, and network errors, 3 times over about 35 seconds before failing, logging a `Request failed ... retrying` warning each time. If it still fails, the next run starts over, and the data from the last good run stays in place.
- **`Error fetching activities` with status `429`**: you've hit Strava's [rate limits](https://developers.strava.com/docs/rate-limits/). Wait 15 minutes. A run makes about one request per 200 activities, plus one per shoe you haven't retired. The first run looks up every shoe you've ever used, so it makes more.
- **`Could not fetch gear ...` warning**: Strava didn't return one shoe's details. The run still finishes, and the shoe is looked up again on the next run.
- **`Failed to read from Neon` or `Failed to load data to Neon`**: check `DATABASE_URL_NEON` in `.env`. It should start with `postgresql://`. A failed load changes nothing, so the data from the last good run stays in place.
- **Dashboard shows `No database connection string`**: on your computer, set `DATABASE_URL_NEON` in `.env` (setup step 4). On Streamlit Community Cloud, add it under the app's **Settings → Secrets**.

## Project structure

```
strava-data-project/
├── strava_api.py             # Loader: Strava → Neon
├── streamlit_app.py          # Dashboard
├── pages/Custom_Range.py     # Dashboard page for custom date ranges
├── dashboard_db.py           # Dashboard's database connection setting
├── deploy/crontab.example    # Optional: example cron schedule
├── deploy/logrotate.example  # Optional: rotation for the cron log
├── pyproject.toml, uv.lock   # Dependencies (uv)
└── requirements.txt          # Dependencies (pip)
```

Not committed: `.env`, `strava_tokens.json`, `.streamlit/secrets.toml`, `logs/`.

## Author

[Gabe Leatherwood](https://github.com/g-leatherwood)

Feel free to fork, deploy, or contribute!
