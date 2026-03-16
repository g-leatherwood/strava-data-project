import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os

DATABASE_URL = st.secrets.get("DATABASE_URL_NEON", os.getenv("DATABASE_URL_NEON"))
engine = create_engine(DATABASE_URL)


@st.cache_data
def load_data():
    query = "SELECT * FROM activities WHERE sport_type = 'Run'"
    df = pd.read_sql(query, engine)
    df["start_date_local"] = pd.to_datetime(df["start_date_local"]).dt.tz_convert(None)
    return df


df = load_data()

st.title("📊 Custom Date Range")

min_date = df["start_date_local"].min().date()
max_date = df["start_date_local"].max().date()

date_col1, date_col2 = st.columns(2)
with date_col1:
    range_from = st.date_input(
        "From", value=min_date, min_value=min_date, max_value=max_date
    )
with date_col2:
    range_to = st.date_input(
        "To", value=max_date, min_value=min_date, max_value=max_date
    )

if range_from > range_to:
    st.warning("'From' date must be before 'To' date.")
else:
    range_df = df[
        (df["start_date_local"].dt.date >= range_from)
        & (df["start_date_local"].dt.date <= range_to)
    ]

    if range_df.empty:
        st.info("No activities found in this date range.")
    else:
        st.subheader(
            f"{range_from.strftime('%b %d, %Y')} — {range_to.strftime('%b %d, %Y')}"
        )

        range_miles = range_df["distance_miles"].sum()

        # Weighted average pace: total time / total distance
        range_time = (
            range_df["average_pace_min_per_mile"] * range_df["distance_miles"]
        ).sum()
        range_dist = range_df["distance_miles"].sum()
        range_avg_pace = range_time / range_dist if range_dist > 0 else None

        if pd.notnull(range_avg_pace):
            rp_min = int(range_avg_pace)
            rp_sec = int((range_avg_pace - rp_min) * 60)
            range_pace_str = f"{rp_min}:{rp_sec:02d} min/mi"
        else:
            range_pace_str = "N/A"

        range_elev_ft = range_df["total_elevation_gain"].sum() * 3.28084

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.metric("Total Miles", f"{range_miles:,.2f}")
        with rc2:
            st.metric("Avg Pace", range_pace_str)
        with rc3:
            st.metric("Total Elevation Gain", f"{range_elev_ft:,.0f} ft")
