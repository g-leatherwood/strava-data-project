import json
import logging
import os
import sys
import time

import requests
import reverse_geocode
from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, insert

load_dotenv()

# Logging Setup
# Logs go to stderr. Under cron, redirect them to a file (see deploy/).
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

# Strava API Credentials
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
TOKEN_FILE = "strava_tokens.json"
API_URL = "https://www.strava.com/api/v3"

# DB URL
NEON_URL = os.getenv("DATABASE_URL_NEON")

MILES_PER_METER = 0.000621371
METERS_PER_MILE = 1609.34

# Tables
# Both tables have a primary key, and each run updates them in place rather
# than dropping them, so the database itself refuses a second row for the
# same activity or shoe. To add a column later, add it here: ensure_schema()
# adds columns the live table is missing.
metadata = MetaData()

activities_table = Table(
    "activities",
    metadata,
    Column("id", BigInteger, primary_key=True),
    # The original columns, with the names and types the dashboard and
    # strava-cli already read.
    Column("name", Text),
    Column("distance_meters", Float),
    Column("distance_miles", Float),
    Column("moving_time", BigInteger),
    Column("elapsed_time", BigInteger),
    Column("total_elevation_gain", Float),
    Column("sport_type", Text),
    Column("start_date", Text),
    Column("start_date_local", Text),
    Column("average_speed", Float),
    Column("max_speed", Float),
    Column("average_heartrate", Float),
    Column("race", BigInteger),
    Column("moving_time_min", Float),
    Column("elapsed_time_min", Float),
    Column("average_pace_min_per_mile", Float),
    Column("max_pace_min_per_mile", Float),
    # Where: Strava's coordinates and route outline, plus the nearest town to
    # the start point (looked up offline; Strava's own location fields are
    # always empty).
    Column("start_lat", Float),
    Column("start_lng", Float),
    Column("end_lat", Float),
    Column("end_lng", Float),
    Column("city", Text),
    Column("county", Text),
    Column("state", Text),
    Column("country", Text),
    Column("timezone", Text),
    Column("summary_polyline", Text),
    # Shoe (or bike). gear_name is copied from the gear table for easy reading.
    Column("gear_id", Text),
    Column("gear_name", Text),
    # The rest of Strava's activity list, named as Strava names them.
    Column("workout_type", Integer),
    Column("device_name", Text),
    Column("trainer", Boolean),
    Column("commute", Boolean),
    Column("manual", Boolean),
    Column("private", Boolean),
    Column("visibility", Text),
    Column("max_heartrate", Float),
    Column("average_cadence", Float),
    Column("average_temp", Float),
    Column("average_watts", Float),
    Column("weighted_average_watts", Float),
    Column("max_watts", Float),
    Column("kilojoules", Float),
    Column("elev_high", Float),
    Column("elev_low", Float),
    Column("suffer_score", Float),
    Column("kudos_count", Integer),
    Column("comment_count", Integer),
    Column("achievement_count", Integer),
    Column("pr_count", Integer),
    Column("athlete_count", Integer),
    Column("total_photo_count", Integer),
    # The activity exactly as Strava sent it, for any field without a column.
    Column("raw", JSONB),
)

gear_table = Table(
    "gear",
    metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text),
    Column("brand_name", Text),
    Column("model_name", Text),
    Column("nickname", Text),
    Column("description", Text),
    Column("distance_meters", Float),
    Column("distance_miles", Float),
    Column("retired", Boolean),
    Column("is_primary", Boolean),
    Column("raw", JSONB),
)

# Strava fields copied into the column of the same name unchanged.
PASSTHROUGH_FIELDS = [
    "name",
    "moving_time",
    "elapsed_time",
    "total_elevation_gain",
    "sport_type",
    "start_date",
    "start_date_local",
    "average_speed",
    "max_speed",
    "average_heartrate",
    "timezone",
    "gear_id",
    "workout_type",
    "device_name",
    "trainer",
    "commute",
    "manual",
    "private",
    "visibility",
    "max_heartrate",
    "average_cadence",
    "average_temp",
    "average_watts",
    "weighted_average_watts",
    "max_watts",
    "kilojoules",
    "elev_high",
    "elev_low",
    "suffer_score",
    "kudos_count",
    "comment_count",
    "achievement_count",
    "pr_count",
    "athlete_count",
    "total_photo_count",
]


# Function to Load Tokens from File
def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as file:
            return json.load(file)
    return None


# Function to Save Tokens to File
def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as file:
        json.dump(tokens, file, indent=4)
    logging.info("Tokens saved to file.")


# Function to Refresh Access Token Automatically
def get_access_token():
    tokens = load_tokens()
    if not tokens or "refresh_token" not in tokens:
        logging.error("No valid refresh token found! Reauthorize your app.")
        sys.exit(1)

    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": tokens["refresh_token"],
            "grant_type": "refresh_token",
        },
    )

    token_data = response.json()
    if "access_token" in token_data:
        save_tokens(
            {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
            }
        )
        return token_data["access_token"]
    else:
        logging.error(f"Error fetching access token: {token_data}")
        sys.exit(1)


# GET with retries for Strava's server errors and network failures. A 429
# isn't retried: rate limits reset on a 15-minute window, so retrying soon
# only spends more of the quota. Returns the last response once retries run
# out, so the caller still sees the final status.
def get_with_retry(url, attempts=4, **kwargs):
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=30, **kwargs)
        except requests.RequestException as e:
            if attempt == attempts:
                raise
            problem = repr(e)
        else:
            if response.status_code < 500 or attempt == attempts:
                return response
            problem = f"{response.status_code} {response.text}"
        delay = 5 * 2 ** (attempt - 1)
        logging.warning(
            f"Request failed ({problem}); retrying in {delay}s "
            f"(attempt {attempt + 1} of {attempts})"
        )
        time.sleep(delay)


# Fetch Strava Activities
# Returns Strava's activity dicts, one per activity ID. Pages are numbered, so
# an activity uploaded while this runs shifts the list and repeats one
# activity on the next page; keying by ID drops the repeat.
def fetch_strava_activities(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    activities = {}
    page = 1

    while True:
        response = get_with_retry(
            f"{API_URL}/athlete/activities",
            headers=headers,
            params={"per_page": 200, "page": page},
        )
        # Raise rather than break: storing the pages fetched so far would
        # delete every activity on the pages that were missed.
        if response.status_code != 200:
            raise RuntimeError(
                f"Error fetching activities (page {page}): "
                f"{response.status_code} {response.text}"
            )

        data = response.json()
        if not data:
            break
        for activity in data:
            activities[activity["id"]] = activity
        page += 1

    logging.info(f"Fetched {len(activities)} activities")
    return list(activities.values())


# Gear IDs to look up this run: ones not in the gear table yet, plus active
# ones, whose mileage keeps changing. Retired gear is looked up once.
def gear_to_fetch(activities, known_gear):
    used = {a["gear_id"] for a in activities if a.get("gear_id")}
    return sorted(
        gear_id
        for gear_id in used
        if gear_id not in known_gear or not known_gear[gear_id]["retired"]
    )


# Fetch Gear
# A shoe that can't be fetched is logged and skipped rather than failing the
# run: it's tried again next run, and its activities keep their gear_id.
def fetch_gear(access_token, gear_ids):
    headers = {"Authorization": f"Bearer {access_token}"}
    gear = []
    for gear_id in gear_ids:
        response = get_with_retry(f"{API_URL}/gear/{gear_id}", headers=headers)
        if response.status_code == 200:
            gear.append(response.json())
            continue
        logging.warning(
            f"Could not fetch gear {gear_id}: {response.status_code} {response.text}"
        )
        if response.status_code == 429:
            logging.warning("Rate limited; skipping the remaining gear this run")
            break
    return gear


# Look Up Towns
# Nearest town to each activity's start point, from an offline copy of
# GeoNames bundled with the reverse_geocode package. Returns {activity id:
# place}; activities without coordinates (manual entries, most treadmill
# runs) are left out.
def look_up_places(activities):
    located = [a for a in activities if a.get("start_latlng")]
    if not located:
        return {}
    places = reverse_geocode.search([tuple(a["start_latlng"]) for a in located])
    return {a["id"]: place for a, place in zip(located, places)}


def minutes(seconds):
    return round(seconds / 60, 2) if seconds is not None else None


def speed_to_min_per_mile(speed_mps):
    if not speed_mps or speed_mps <= 0:
        return None
    return round((METERS_PER_MILE / speed_mps) / 60, 2)


# One row for the activities table.
def build_activity_row(activity, place, gear_names):
    row = {field: activity.get(field) for field in PASSTHROUGH_FIELDS}
    distance = activity.get("distance") or 0.0
    start = activity.get("start_latlng") or [None, None]
    end = activity.get("end_latlng") or [None, None]
    place = place or {}

    row.update(
        {
            "id": activity["id"],
            "distance_meters": distance,
            "distance_miles": round(distance * MILES_PER_METER, 2),
            "race": 1 if activity.get("workout_type") == 1 else 0,
            "moving_time_min": minutes(activity.get("moving_time")),
            "elapsed_time_min": minutes(activity.get("elapsed_time")),
            "average_pace_min_per_mile": speed_to_min_per_mile(
                activity.get("average_speed")
            ),
            "max_pace_min_per_mile": speed_to_min_per_mile(activity.get("max_speed")),
            "start_lat": start[0],
            "start_lng": start[1],
            "end_lat": end[0],
            "end_lng": end[1],
            "city": place.get("city"),
            "county": place.get("county"),
            "state": place.get("state"),
            "country": place.get("country"),
            "summary_polyline": (activity.get("map") or {}).get("summary_polyline")
            or None,
            "gear_name": gear_names.get(activity.get("gear_id")),
            "raw": activity,
        }
    )
    return row


# One row for the gear table.
def build_gear_row(gear):
    distance = gear.get("distance") or 0.0
    return {
        "id": gear["id"],
        "name": gear.get("name"),
        "brand_name": gear.get("brand_name"),
        "model_name": gear.get("model_name"),
        "nickname": gear.get("nickname"),
        "description": gear.get("description"),
        "distance_meters": distance,
        "distance_miles": round(distance * MILES_PER_METER, 2),
        "retired": gear.get("retired"),
        "is_primary": gear.get("primary"),
        "raw": gear,
    }


# {gear id: row} for gear already stored, or {} before the first run.
def load_known_gear(conn):
    if conn.execute(text("SELECT to_regclass('gear')")).scalar() is None:
        return {}
    rows = conn.execute(
        select(gear_table.c.id, gear_table.c.name, gear_table.c.retired)
    )
    return {row.id: row._asdict() for row in rows}


# Create the tables, or add columns that are new since they were created.
# Tables from before the primary key existed (built by pandas, which dropped
# and recreated the table on every run) are kept as activities_backup.
def ensure_schema(conn):
    if conn.execute(text("SELECT to_regclass('activities')")).scalar() is not None:
        has_primary_key = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_constraint "
                "WHERE conrelid = 'activities'::regclass AND contype = 'p')"
            )
        ).scalar()
        if not has_primary_key:
            conn.execute(text("ALTER TABLE activities RENAME TO activities_backup"))
            logging.info("Kept the old activities table as activities_backup")

    metadata.create_all(conn)

    quote = conn.dialect.identifier_preparer.quote
    for table in metadata.sorted_tables:
        existing = set(
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = :name"
                ),
                {"name": table.name},
            ).scalars()
        )
        for column in table.columns:
            if column.name not in existing:
                column_type = column.type.compile(dialect=conn.dialect)
                conn.execute(
                    text(
                        f"ALTER TABLE {quote(table.name)} "
                        f"ADD COLUMN {quote(column.name)} {column_type}"
                    )
                )
                logging.info(f"Added column {table.name}.{column.name}")


# Insert new rows and overwrite existing ones, matched on the primary key. A
# repeated ID within one batch makes Postgres raise, which fails the run
# instead of storing a duplicate.
def upsert(conn, table, rows, batch_size=500):
    for start in range(0, len(rows), batch_size):
        stmt = insert(table).values(rows[start : start + batch_size])
        stmt = stmt.on_conflict_do_update(
            index_elements=[table.c.id],
            set_={
                c.name: stmt.excluded[c.name]
                for c in table.columns
                if not c.primary_key
            },
        )
        conn.execute(stmt)


# Store Data in Neon
# Runs inside the caller's transaction, so a run either stores everything or
# changes nothing. Activities missing from this run's fetch were deleted on
# Strava and are removed here too. Returns how many were removed.
def store(conn, activity_rows, gear_rows):
    ensure_schema(conn)
    upsert(conn, gear_table, gear_rows)
    upsert(conn, activities_table, activity_rows)
    ids = [row["id"] for row in activity_rows]
    result = conn.execute(
        activities_table.delete().where(activities_table.c.id.not_in(ids))
    )
    return result.rowcount


def main():
    access_token = get_access_token()
    activities = fetch_strava_activities(access_token)
    if not activities:
        # Storing an empty fetch would delete every activity.
        logging.warning("No activities found! Leaving the database unchanged.")
        return

    try:
        engine = create_engine(NEON_URL)
        with engine.connect() as conn:
            known_gear = load_known_gear(conn)
    except Exception as e:
        raise RuntimeError("Failed to read from Neon") from e

    new_gear = fetch_gear(access_token, gear_to_fetch(activities, known_gear))
    gear_names = {gear_id: row["name"] for gear_id, row in known_gear.items()}
    gear_names.update({gear["id"]: gear.get("name") for gear in new_gear})

    places = look_up_places(activities)
    activity_rows = [
        build_activity_row(a, places.get(a["id"]), gear_names) for a in activities
    ]
    gear_rows = [build_gear_row(gear) for gear in new_gear]

    try:
        with engine.begin() as conn:
            removed = store(conn, activity_rows, gear_rows)
    except Exception as e:
        raise RuntimeError("Failed to load data to Neon") from e

    logging.info(
        f"Stored {len(activity_rows)} activities ({removed} removed as deleted on "
        f"Strava) and refreshed {len(gear_rows)} gear"
    )
    logging.info("Successfully loaded data to Neon")


# Run the Process
# Any failure exits non-zero so cron, and anything chained after this script,
# sees that the run failed.
if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Run failed")
        sys.exit(1)
