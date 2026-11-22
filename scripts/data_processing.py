"""
Data pipeline for RoadVision.

Loads the UK STATS19 accident extract (Greater London, 2013-2015), cleans it,
converts the numeric STATS19 codes into readable labels, adds derived fields,
and records a cleaning report that the dashboard shows on its Data Pipeline tab.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "accident_data.csv"
CACHE_PATH = DATA_DIR / "accident_data_clean.parquet"

# ---------- Code labels from the UK Department for Transport STATS19 data guide ----------
SEVERITY = {1: "Fatal", 2: "Serious", 3: "Slight"}
DAYS = {1: "Sunday", 2: "Monday", 3: "Tuesday", 4: "Wednesday", 5: "Thursday", 6: "Friday", 7: "Saturday"}
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FORCE = {1: "Metropolitan Police", 48: "City of London Police"}
AREA = {1: "Urban", 2: "Rural"}
ROAD_TYPE = {1: "Roundabout", 2: "One way street", 3: "Dual carriageway", 6: "Single carriageway",
             7: "Slip road", 12: "One way / slip road"}
LIGHT = {1: "Daylight", 4: "Dark - lights lit", 5: "Dark - lights unlit", 6: "Dark - no lighting"}
WEATHER = {1: "Fine", 2: "Rain", 3: "Snow", 4: "Fine + high winds", 5: "Rain + high winds",
           6: "Snow + high winds", 7: "Fog or mist", 8: "Other"}
SURFACE = {1: "Dry", 2: "Wet or damp", 3: "Snow", 4: "Frost or ice", 5: "Flood"}

# Time-of-day bands used across the dashboard.
BANDS = [(0, 6, "Night (00-05)"), (6, 10, "Morning rush (06-09)"), (10, 16, "Daytime (10-15)"),
         (16, 20, "Evening rush (16-19)"), (20, 24, "Late evening (20-23)")]
BAND_ORDER = [b[2] for b in BANDS]

# Readable column -> (original STATS19 column, label map)
LABEL_MAPS = {
    "Severity": ("Accident_Severity", SEVERITY), "Day": ("Day_of_Week", DAYS),
    "Force": ("Police_Force", FORCE), "Area": ("Urban_or_Rural_Area", AREA),
    "Road": ("Road_Type", ROAD_TYPE), "Light": ("Light_Conditions", LIGHT),
    "Weather": ("Weather_Conditions", WEATHER), "Surface": ("Road_Surface_Conditions", SURFACE),
}


def time_band(hour):
    """Map an hour (0-23) to a named time-of-day band."""
    for start, end, name in BANDS:
        if start <= hour < end:
            return name
    return "Unknown"


def clean(raw):
    """Clean the raw table and return (clean_df, report_dict)."""
    report = {"raw_rows": len(raw), "raw_columns": raw.shape[1],
              "missing_by_column": raw.isna().sum().to_dict()}
    df = raw.copy()

    # 1. Duplicates: each accident ID must appear once.
    before = len(df)
    df = df.drop_duplicates(subset="Accident_Index")
    report["duplicates_removed"] = before - len(df)

    # 2. Type conversion. Bad values become NaN/NaT instead of crashing.
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Latitude", "Longitude", "Accident_Severity", "Speed_limit", "Number_of_Vehicles"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 3. Invalid records: no date, no severity, or coordinates outside Great Britain.
    before = len(df)
    df = df.dropna(subset=["Date", "Latitude", "Longitude", "Accident_Severity"])
    df = df[df["Latitude"].between(49, 61) & df["Longitude"].between(-9, 3)]
    report["invalid_removed"] = before - len(df)

    # 4. Missing values in non-critical fields are kept and labelled "Unknown".
    df["Hour"] = pd.to_datetime(df["Time"], format="%H:%M", errors="coerce").dt.hour
    report["missing_time"] = int(df["Hour"].isna().sum())
    df["Number_of_Casualties"] = pd.to_numeric(df["Number_of_Casualties"], errors="coerce").fillna(0).astype(int)

    # 5. Codes -> labels.
    for new, (old, labels) in LABEL_MAPS.items():
        df[new] = df[old].map(labels).fillna("Unknown")
    report["unknown_codes"] = {new: int((df[new] == "Unknown").sum()) for new in LABEL_MAPS}

    # 6. Derived features used by the analysis.
    df["Severe"] = df["Severity"].isin(["Fatal", "Serious"]).astype(int)
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Weekend"] = np.where(df["Day"].isin(["Saturday", "Sunday"]), "Weekend", "Weekday")
    df["Time_Band"] = df["Hour"].apply(lambda h: time_band(h) if pd.notna(h) else "Unknown")
    df["Speed"] = df["Speed_limit"].fillna(0).astype(int).astype(str) + " mph"
    df["Vehicles"] = df["Number_of_Vehicles"].clip(upper=4).fillna(0).astype(int).astype(str).replace("4", "4+")

    df = df.sort_values("Date").reset_index(drop=True)
    report["clean_rows"] = len(df)
    report["clean_columns"] = df.shape[1]
    return df, report


def load_data(path=CSV_PATH):
    """Load and clean the dataset. Returns (df, report)."""
    start = time.perf_counter()
    raw = pd.read_csv(path, low_memory=False)
    df, report = clean(raw)
    report["load_seconds"] = round(time.perf_counter() - start, 2)
    report["csv_mb"] = round(Path(path).stat().st_size / 1e6, 1)

    # Save a cleaned Parquet copy (columnar, compressed) for reuse and export.
    try:
        df.to_parquet(CACHE_PATH, index=False)
        report["parquet_mb"] = round(CACHE_PATH.stat().st_size / 1e6, 1)
    except Exception:
        report["parquet_mb"] = None
    return df, report
