import requests
import json
import os
import pandas as pd
from sqlalchemy import create_engine, text

# ✅ Strava API Credentials (Replace with your actual values)
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")
TOKEN_FILE = "strava_tokens.json"

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

# ✅ Fetch Strava Activities (Basic Fields Only)
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
            break  # No more data to fetch

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
                "race": 1 if activity.get("workout_type") == 1 else 0,  # Convert to 1 (Race) or 0 (Not a Race)
            })

        page += 1  # Fetch next batch of activities

    return all_activities

# ✅ Store Data in MySQL (Basic Fields Only)
def store_activities_in_mysql(activities):
    if not activities:
        print("❌ No activities found!")
        return

    df = pd.DataFrame(activities)

    # ✅ Print column names to check if everything is correct
    print("🛠 Columns in DataFrame:", df.columns)

    # ✅ Ensure correct column names before applying data types
    expected_columns = ["id", "distance_meters", "distance_miles", "moving_time", 
                        "elapsed_time", "total_elevation_gain", "average_speed", 
                        "max_speed", "race"]
    
    missing_columns = [col for col in expected_columns if col not in df.columns]
    if missing_columns:
        print(f"❌ Missing Columns: {missing_columns}")
        return  # Stop execution if required columns are missing

    # ✅ Ensure proper data types
    df = df.astype({
        "id": "int",
        "distance_meters": "float",
        "distance_miles": "float",
        "moving_time": "int",
        "elapsed_time": "int",
        "total_elevation_gain": "float",
        "average_speed": "float",
        "max_speed": "float",
        "race": "int",  # Store as integer (1 = Race, 0 = Not a Race)
    }, errors="ignore")

    # ✅ Convert NaN values to None for MySQL
    df = df.where(pd.notna(df), None)

    # ✅ Connect to MySQL and Insert Data
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS activities (
                id BIGINT PRIMARY KEY,
                name TEXT,
                distance_meters FLOAT,
                distance_miles FLOAT,
                moving_time INT,
                elapsed_time INT,
                total_elevation_gain FLOAT,
                sport_type TEXT,
                start_date TEXT,
                start_date_local TEXT,
                average_speed FLOAT,
                max_speed FLOAT,
                average_heartrate FLOAT,
                race INT  -- 1 = Race, 0 = Not a Race
            )
        """))
    
    df.to_sql("activities", con=engine, if_exists="replace", index=False, chunksize=500, method="multi")
    print("✅ Data successfully inserted into MySQL!")

# ✅ Run the Process
ACCESS_TOKEN = get_access_token()
activities = fetch_strava_activities(ACCESS_TOKEN)
store_activities_in_mysql(activities)

print("🚀 Strava data successfully updated in MySQL!")