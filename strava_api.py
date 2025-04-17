import requests
import json
import os
import pandas as pd
from sqlalchemy import create_engine, text

# ✅ Strava API Credentials
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
TOKEN_FILE = "strava_tokens.json"

# ✅ DB URLs
MYSQL_URL = os.getenv("DATABASE_URL")
NEON_URL = os.getenv("DATABASE_URL_NEON")

# ✅ Function to Load Tokens from File
def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as file:
            return json.load(file)
    return None

# ✅ Function to Save Tokens to File
def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as file:
        json.dump(tokens, file, indent=4)
    print("💾 Tokens saved to file.")

# ✅ Function to Refresh Access Token Automatically
def get_access_token():
    tokens = load_tokens()
    if not tokens or "refresh_token" not in tokens:
        print("❌ No valid refresh token found! Reauthorize your app.")
        exit()

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
        save_tokens({
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"]
        })
        return token_data["access_token"]
    else:
        print("❌ Error fetching access token:", token_data)
        exit()

# ✅ Fetch Strava Activities
def fetch_strava_activities(access_token):
    ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    all_activities = []
    page = 1

    while True:
        response = requests.get(ACTIVITIES_URL, headers=headers, params={"per_page": 100, "page": page})
        if response.status_code != 200:
            print("❌ Error fetching activities:", response.json())
            break

        data = response.json()
        if not data:
            break

        for activity in data:
            all_activities.append({
                "id": activity.get("id"),
                "name": activity.get("name"),
                "distance_meters": activity.get("distance", 0.0),
                "distance_miles": round(activity.get("distance", 0.0) * 0.000621371, 2),
                "moving_time": activity.get("moving_time"),
                "elapsed_time": activity.get("elapsed_time"),
                "total_elevation_gain": activity.get("total_elevation_gain"),
                "sport_type": activity.get("sport_type"),
                "start_date": activity.get("start_date"),
                "start_date_local": activity.get("start_date_local"),
                "average_speed": activity.get("average_speed"),
                "max_speed": activity.get("max_speed"),
                "average_heartrate": activity.get("average_heartrate"),
                "race": 1 if activity.get("workout_type") == 1 else 0,
            })

        page += 1

    return all_activities

# ✅ Store Data in MySQL + Neon
def store_activities_in_databases(activities):
    if not activities:
        print("❌ No activities found!")
        return

    df = pd.DataFrame(activities)
    df["moving_time_min"] = (df["moving_time"] / 60).round(2)
    df["elapsed_time_min"] = (df["elapsed_time"] / 60).round(2)

    def speed_to_min_per_mile(speed_mps):
        return (1609.34 / speed_mps) / 60 if speed_mps and speed_mps > 0 else None

    df["average_pace_min_per_mile"] = df["average_speed"].apply(speed_to_min_per_mile).round(2)
    df["max_pace_min_per_mile"] = df["max_speed"].apply(speed_to_min_per_mile).round(2)

    df = df.astype({
        "id": "int",
        "distance_meters": "float",
        "distance_miles": "float",
        "moving_time": "int",
        "elapsed_time": "int",
        "moving_time_min": "float",
        "elapsed_time_min": "float",
        "total_elevation_gain": "float",
        "average_speed": "float",
        "average_pace_min_per_mile": "float",
        "max_speed": "float",
        "max_pace_min_per_mile": "float",
        "race": "int"
    }, errors="ignore")

    df = df.where(pd.notna(df), None)

    create_sql = """
        CREATE TABLE IF NOT EXISTS activities (
            id BIGINT PRIMARY KEY,
            name TEXT,
            distance_meters FLOAT,
            distance_miles FLOAT,
            moving_time INT,
            elapsed_time INT,
            moving_time_min FLOAT,
            elapsed_time_min FLOAT,
            total_elevation_gain FLOAT,
            sport_type TEXT,
            start_date TEXT,
            start_date_local TEXT,
            average_speed FLOAT,
            average_pace_min_per_mile FLOAT,
            max_speed FLOAT,
            max_pace_min_per_mile FLOAT,
            average_heartrate FLOAT,
            race INT
        )
    """

    db_targets = [("MySQL", MYSQL_URL), ("Neon", NEON_URL)]

    for label, db_url in db_targets:
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text(create_sql))
            df.to_sql("activities", con=engine, if_exists="replace", index=False, chunksize=500, method="multi")
            print(f"✅ Successfully loaded data to {label}")
        except Exception as e:
            print(f"❌ Failed to load data to {label}: {e}")

# ✅ Run the Process
if __name__ == "__main__":
    ACCESS_TOKEN = get_access_token()
    activities = fetch_strava_activities(ACCESS_TOKEN)
    store_activities_in_databases(activities)
    print("🚀 Strava data successfully updated in all databases!")