import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import calendar
from pandas.tseries.offsets import MonthEnd
import altair as alt

# Load DB URL from environment
DATABASE_URL = st.secrets.get("DATABASE_URL_NEON", os.getenv("DATABASE_URL_NEON"))
engine = create_engine(DATABASE_URL)

# Load data
@st.cache_data
def load_data():
    query = "SELECT * FROM activities WHERE sport_type = 'Run'"
    df = pd.read_sql(query, engine)
    df["start_date_local"] = pd.to_datetime(df["start_date_local"]).dt.tz_convert(None)
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")

# Year filter
years = sorted(df["start_date_local"].dt.year.unique(), reverse=True)
year_options = ["All time"] + years
year_filter = st.sidebar.selectbox("Year", year_options)

# Filter data by selected year
if year_filter != "All time":
    filtered_df = df[df["start_date_local"].dt.year == year_filter]
else:
    filtered_df = df.copy()

# Get available month numbers from filtered year
available_month_nums = sorted(filtered_df["start_date_local"].dt.month.unique())

# Convert to month names
available_months = [calendar.month_name[m] for m in available_month_nums]

# Add "All" at the top
month_options = ["All"] + available_months
month_filter = st.sidebar.selectbox("Month", month_options)

# Apply year filter only — do NOT filter month here
if year_filter != "All time":
    filtered_df = df[df["start_date_local"].dt.year == year_filter]
else:
    filtered_df = df.copy()

# Save month number if applicable
month_num = None
if month_filter != "All":
    month_num = list(calendar.month_name).index(month_filter)
    filtered_df = filtered_df[filtered_df["start_date_local"].dt.month == month_num]

# Dashboard Title
st.title("🏃 Strava Run Dashboard")

# ✅ Now filtered_df reflects both year and month — use it for metrics
total_miles = filtered_df["distance_miles"].sum()
total_miles_formated = f"{total_miles:,.2f} miles"
total_activities = filtered_df.shape[0]
# Total time in minutes (pace × miles)
total_time = (filtered_df["average_pace_min_per_mile"] * filtered_df["distance_miles"]).sum()
total_distance = filtered_df["distance_miles"].sum()

# True average pace (min/mile)
true_avg_pace = total_time / total_distance if total_distance > 0 else None

if pd.notnull(true_avg_pace):
    pace_minutes = int(true_avg_pace)
    pace_seconds = int((true_avg_pace - pace_minutes) * 60)
    formatted_pace = f"{pace_minutes}:{pace_seconds:02d} min/mi"
else:
    formatted_pace = "N/A"

date_range_weeks = filtered_df["start_date_local"].dt.to_period("W").nunique()
weekly_avg = total_miles / date_range_weeks if date_range_weeks > 0 else 0
active_days = filtered_df["start_date_local"].dt.date.nunique()
daily_miles_active = filtered_df["distance_miles"].sum() / active_days if active_days > 0 else 0

# 📊 Show charts based on filter combo
if year_filter == "All time" and month_filter == "All":
    # 🔹 Yearly mileage across all time
    st.subheader("📆 Yearly Mileage")
    yearly_miles = (
        filtered_df
        .set_index("start_date_local")
        .resample("Y")["distance_miles"]
        .sum()
    )
    yearly_miles.index = yearly_miles.index.year.astype(str)

    # Convert to DataFrame
    yearly_df = yearly_miles.reset_index()
    yearly_df.columns = ["Year", "Miles"]

    st.altair_chart(
        alt.Chart(yearly_df).mark_bar().encode(
            x=alt.X("Year:N", title="Year"),
            y=alt.Y("Miles:Q", title="Miles"),
            tooltip=["Year", "Miles"]
        ).properties(
            width=700,
            height=400
        ),
        use_container_width=True
    )

elif month_filter == "All":
    # 🔹 Monthly mileage for a single selected year
    st.subheader(f"📆 Monthly Mileage for {year_filter}")

    monthly_miles = (
        filtered_df
        .set_index("start_date_local")
        .resample("M")["distance_miles"]
        .sum()
    )

    # Build DataFrame with numeric month for sorting
    monthly_miles_df = monthly_miles.reset_index()
    monthly_miles_df["Month_Num"] = monthly_miles_df["start_date_local"].dt.month
    monthly_miles_df["Month"] = monthly_miles_df["start_date_local"].dt.strftime("%b")

    # Sort by calendar order
    monthly_miles_df = monthly_miles_df.sort_values("Month_Num")

    # Plot using Altair with axis labels
    st.altair_chart(
        alt.Chart(monthly_miles_df).mark_bar().encode(
            x=alt.X("Month:N", sort=monthly_miles_df["Month"].tolist(), title="Month"),
            y=alt.Y("distance_miles:Q", title="Miles"),
            tooltip=["Month", "distance_miles"]
        ).properties(
            width=700,
            height=400
        ),
        use_container_width=True
    )

elif year_filter != "All time" and month_filter != "All":
    st.subheader(f"📅 Weekly Mileage for {month_filter} {year_filter}")

    # Get month number
    month_num = list(calendar.month_name).index(month_filter)

    # Define date ranges
    start_date = pd.Timestamp(year=year_filter, month=month_num, day=1).tz_localize("UTC").tz_convert(None)
    end_date = (start_date + MonthEnd(1)).tz_localize("UTC").tz_convert(None)


    # Filter full dataset to runs within the extended window
    resample_df = df.copy()
    resample_df["week_start"] = resample_df["start_date_local"].dt.to_period("W-MON").dt.start_time

    # Filter to only activities that happened within the selected month
    eod = end_date + pd.Timedelta(hours=23, minutes=59, seconds=59)  # Include the last day of the month
    resample_df = resample_df[
        (resample_df["start_date_local"] >= start_date) &
        (resample_df["start_date_local"] <= eod)
    ]

    # Group by the Monday of the week and sum distance
    weekly_miles_df = (
        resample_df.groupby("week_start")["distance_miles"]
        .sum()
        .reset_index()
        .sort_values("week_start")
    )
    weekly_miles_df["Week"] = (weekly_miles_df["week_start"] - pd.to_timedelta(weekly_miles_df["week_start"].dt.weekday, unit='D')).dt.strftime("Week of %b %d")

    # Render chart
    st.altair_chart(
        alt.Chart(weekly_miles_df).mark_bar().encode(
            x=alt.X("Week:N", sort=weekly_miles_df["Week"].tolist(), title="Week"),
            y=alt.Y("distance_miles:Q", title="Miles"),
            tooltip=["Week", "distance_miles"]
        ).properties(
            width=700,
            height=400
        ),
        use_container_width=True
    )

else:
    # 📊 Year-over-year view for selected month across all years
    st.subheader(f"📈 {month_filter} Mileage by Year")

    month_num = list(calendar.month_name).index(month_filter)
    miles_by_year = (
        df[df["start_date_local"].dt.month == month_num]
        .groupby(df["start_date_local"].dt.year)["distance_miles"]
        .sum()
    )

    # Prepare DataFrame for Altair
    miles_by_year_df = miles_by_year.reset_index()
    miles_by_year_df.columns = ["Year", "Miles"]
    miles_by_year_df["Year"] = miles_by_year_df["Year"].astype(str)

    st.altair_chart(
        alt.Chart(miles_by_year_df).mark_bar().encode(
            x=alt.X("Year:N", title="Year"),
            y=alt.Y("Miles:Q", title="Miles"),
            tooltip=["Year", "Miles"]
        ).properties(
            width=700,
            height=400
        ),
        use_container_width=True
    )

# Filter selections
st.subheader(f"📆 Viewing data for: {month_filter} & {year_filter}")

# Display metrics in two columns
col1, col2 = st.columns(2)

with col1:
    st.metric("Total Miles", total_miles_formated)
    st.metric("Weekly Mileage (Active Weeks)", round(weekly_avg, 2))

with col2:
    st.metric("Avg Pace", formatted_pace)
    st.metric("Miles per Day (Active Days)", round(daily_miles_active, 2))