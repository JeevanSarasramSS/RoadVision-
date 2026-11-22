"""
Indian road accident data (official, state-level).

Source: Ministry of Road Transport & Highways (Transport Research Wing),
"Road Accidents in India 2015". Tables transcribed into two CSV files:

  data/india_states.csv          36 States/UTs x 43 fields
      Annexure III  accidents 2012-2015 (+ accidents per lakh population 2015)
      Annexure IV   persons killed 2012-2015 (+ killed per lakh population 2015)
      Annexure V    persons injured 2012-2015
      Annexure VIII fatal accidents 2015
      Annexure X    urban / rural accidents and killed 2015
      Annexures XII-XVIII  National Highway / State Highway / other roads 2015
      Annexure XX   accidents by 3-hour time slot 2015
      Annexure XXII accidents by weather 2015 (six categories that could be read reliably)
  data/india_road_accidents.csv  national tables: totals 2013-2015, month (Table 7.1),
      time of day (Table 8.1), weather (Annexure XXII), causes (Table 11.1),
      million-plus cities (Annexure XLIII)

India publishes aggregate tables only (no per-accident records), so the India section
works with totals, shares and rates. Every column is checked against the report's
printed All-India total in verify_states().
"""
import json

import pandas as pd

from scripts.data_processing import DATA_DIR

INDIA_PATH = DATA_DIR / "india_road_accidents.csv"
STATES_PATH = DATA_DIR / "india_states.csv"
GEO_PATH = DATA_DIR / "india_states.geojson"
SOURCE = "MoRTH, Road Accidents in India 2015"
YEARS = [2012, 2013, 2014, 2015]

# Share of accidents that were fatal (accidents with at least one death), Table 1.2
INDIA_FATAL_SHARE = {2013: 25.2, 2014: 25.7, 2015: 26.3}

# Time slots in clock order, and the matching state-table columns
SLOTS = ["00-03", "03-06", "06-09", "09-12", "12-15", "15-18", "18-21", "21-24"]
SLOT_COLS = ["slot_" + s.replace("-", "_") for s in SLOTS]
DAY_SLOTS = ["06-09", "09-12", "12-15", "15-18"]          # MoRTH labels 06:00-18:00 as day

WEATHER_COLS = {"weather_fine": "Fine", "weather_fog": "Mist / fog", "weather_cloudy": "Cloudy",
                "weather_light_rain": "Light rain", "weather_heavy_rain": "Heavy rain",
                "weather_flooding": "Flooding", "weather_other_or_unspecified": "Other / not split by state"}

# All-India totals printed in the report, used to verify the transcribed state rows
REPORT_TOTALS = {
    "accidents_2012": 490383, "accidents_2013": 486476, "accidents_2014": 489400, "accidents_2015": 501423,
    "killed_2012": 138258, "killed_2013": 137572, "killed_2014": 139671, "killed_2015": 146133,
    "injured_2012": 509667, "injured_2013": 494893, "injured_2014": 493474, "injured_2015": 500279,
    "fatal_accidents_2015": 131726,
    "slot_06_09": 55518, "slot_09_12": 81964, "slot_12_15": 79616, "slot_15_18": 87819,
    "slot_18_21": 86836, "slot_21_24": 51425, "slot_00_03": 27954, "slot_03_06": 30291,
    "urban_acc": 231894, "urban_killed": 56978, "rural_acc": 269529, "rural_killed": 89155,
    "nh_acc": 142268, "nh_killed": 51204, "sh_acc": 120518, "sh_killed": 40863,
    "other_acc": 238637, "other_killed": 54066,
    "weather_fine": 339580, "weather_fog": 20196, "weather_cloudy": 15567,
    "weather_light_rain": 24881, "weather_heavy_rain": 17780, "weather_flooding": 1834,
}

# London STATS19 weather labels -> broad groups shared with India's categories
LONDON_WEATHER_GROUP = {"Fine": "Fine", "Rain": "Rain", "Rain + high winds": "Rain", "Fog or mist": "Fog / mist",
                        "Snow": "Snow / hail", "Snow + high winds": "Snow / hail", "Fine + high winds": "Strong wind",
                        "Other": "Other"}
INDIA_WEATHER_GROUP = {"Fine": "Fine", "Light rain": "Rain", "Heavy rain": "Rain", "Mist/fog": "Fog / mist",
                       "Snow": "Snow / hail", "Hail/sleet": "Snow / hail", "Strong wind": "Strong wind",
                       "Cloudy": "Other", "Flooding": "Other", "Dust storm": "Other", "Other extraordinary": "Other"}


def load_india():
    """National tables as a dict of DataFrames keyed by table name."""
    d = pd.read_csv(INDIA_PATH)
    return {name: g.drop(columns="table").reset_index(drop=True) for name, g in d.groupby("table")}


def load_states():
    """State table with derived rates. Andhra Pradesh was split in June 2014, so its 2012-2013 figures
    include Telangana; growth rates for both are left blank."""
    s = pd.read_csv(STATES_PATH)
    s["deaths_per_100"] = s["killed_2015"] / s["accidents_2015"] * 100
    s["fatal_share"] = s["fatal_accidents_2015"] / s["accidents_2015"] * 100
    s["change_2013_2015"] = (s["accidents_2015"] / s["accidents_2013"] - 1) * 100
    s.loc[s["state"].isin(["Andhra Pradesh", "Telangana"]), "change_2013_2015"] = float("nan")
    night = [c for c, sl in zip(SLOT_COLS, SLOTS) if sl not in DAY_SLOTS]
    s["night_share"] = s[night].sum(axis=1) / s["accidents_2015"] * 100
    s["rural_death_share"] = s["rural_killed"] / s["killed_2015"] * 100
    s["nh_death_share"] = s["nh_killed"] / s["killed_2015"] * 100
    return s


def load_geojson():
    with open(GEO_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def verify_states(states):
    """Compare the sum of the 36 state rows with the All-India total printed in the report."""
    rows = [{"Column": col, "Sum of 36 states": int(states[col].sum()), "Report total": total,
             "Match": "✅" if int(states[col].sum()) == total else "❌"} for col, total in REPORT_TOTALS.items()]
    return pd.DataFrame(rows)


def london_slots(london):
    """London accidents in the same 3-hour slots India uses."""
    h = london["Hour"].dropna().astype(int)
    slot = (h // 3).map(lambda i: SLOTS[i])
    return slot.value_counts().reindex(SLOTS, fill_value=0)
