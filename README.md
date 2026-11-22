# RoadVision – Road Accident Analytics Dashboard (London · India · Comparison)

Interactive big-data visualization dashboard built with **Python, Pandas, NumPy, Plotly and Streamlit**.
It analyses **74,359 police-reported road accidents in Greater London, UK (2013–2015)**.
The data covers London only, not other countries.

## Run (Command Prompt)
```
cd /d "D:\Coding\Big Data Visualization"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Or double-click `run.bat`. The app opens at http://localhost:8501.

## Dashboard sections
Switch sections with the buttons at the top of the page.

### 🇬🇧 London (record-level, 74,359 accidents, 2013–2015)
| Tab | What it shows |
|---|---|
| Overview | KPI cards, auto-generated insights, monthly trend with 3-month average and severity %, severity donut, year-over-year comparison |
| Time Patterns | Day × hour heatmap, 24-hour polar clock, daily calendar heatmap, time-of-day bands, weekday volume vs severity |
| Geography & Hotspots | Street-map density heatmap, accident points, offline density grid, top-10 hotspot detection (1 km grid) |
| Risk Factors | Chi-square / Cramér's V ranking, weather × surface risk matrix, speed limit, lighting, road type, vehicles |
| Data Pipeline | Cleaning steps and statistics, completeness, data dictionary |
| Data Explorer | Filtered records, CSV download, summary statistics |

Filters: date range, police force, severity, hour of day, weather, road surface, lighting.

### 🇮🇳 India (state-wise, all 36 States/UTs, 2012–2015)
| Tab | What it shows |
|---|---|
| Overview | KPI cards, auto-generated insights, 2012–2015 trend, fatal vs non-fatal donut, top 10 states, zone severity |
| State Map & Ranking | India state map (6 metrics: accidents, deaths, deaths per 100 accidents, per-lakh-population rates, growth), top-15 ranking, volume-vs-severity bubble chart, state table with sparklines |
| Time Patterns | 24-hour clock (3-hour slots), state × time-slot heatmap, night-accident share by state, month-wise accidents |
| Roads & Area | National/State Highway vs other roads (accidents vs deaths), road mix per state, urban vs rural |
| Causes & Weather | Causes of accidents, deaths per 100 accidents by weather, weather mix per state, million-plus cities |
| Data & Sources | How the data was built, live verification of 37 columns against the report's totals, notes, download |

Filters: zone (MHA zonal councils), States/UTs, headline year.

### 🆚 India vs London (2015)
- London vs any chosen Indian state (default Delhi): accidents, fatal share, urban share, night share, growth, time-of-day profile.
- All India vs London: time-of-day and monthly shares, weather, growth since 2013, city deaths per 100 accidents.

## Project structure
```
app.py                       Entry point: theme, data loading, section switch
views/london.py              London section
views/india.py               India section (state-wise)
views/compare.py             India vs London section
scripts/ui.py                Shared colours, CSS, KPI cards, chart style
scripts/data_processing.py   London: load, clean, decode STATS19 codes, derive features
scripts/analysis.py          London: insights, hotspot detection, chi-square / Cramér's V
scripts/india.py             India: loaders, derived rates, verification against report totals
data/accident_data.csv       London records (STATS19)
data/india_states.csv        36 States/UTs x 43 fields (MoRTH 2015 annexures)
data/india_road_accidents.csv  India national tables (MoRTH 2015)
data/india_states.geojson    State boundaries (Census of India based; Ladakh merged into J&K for 2015)
run.bat                      One-click start on Windows
```

## Dataset
- Original source: UK Department for Transport, STATS19 road safety data (Open Government Licence). Yearly CSVs are published at https://data.dft.gov.uk/road-accidents-safety-data/ , for example `dft-road-casualty-statistics-collision-2015.csv`.
- File used: the Greater London 2013–2015 extract from https://github.com/Tural-Hamidov/Final_Project_Car_Accidents (`notebooks/data/accidents_london_2013_2015.csv`), trimmed to the 16 columns the dashboard needs.
- Not in this dataset, so not shown: vehicle type, accident cause, persons killed (fatal *accidents* are counted instead). Region means police force.

## Indian data
- Source: Ministry of Road Transport & Highways (Transport Research Wing), *Road Accidents in India 2015*. Report copy: https://www.cag.org.in/sites/default/files/database/morth2015.pdf
- State tables used: Annexures III, IV, V (accidents, killed, injured 2012–2015 and per-lakh-population rates), VIII (fatal accidents), X (urban/rural), XII–XVIII (road type), XX (time of occurrence), XXII (weather).
- National tables used: Table 1.2 (totals), 7.1 (month), 8.1 (time of day), 11.1 (causes), Annexure XXII (weather), XLIII (cities).
- Verification: the app sums every state column and compares it with the report's printed All-India total (37 of 37 match; see India → Data & Sources).
- India publishes aggregate tables only, so the India section uses totals, shares and rates, not individual accidents.
- Andhra Pradesh was split in June 2014: its 2012–2013 figures include Telangana; growth and per-population rates for both are blank.
- State map: Census of India state boundaries from https://github.com/datta07/INDIAN-SHAPEFILES ; Ladakh is drawn with Jammu & Kashmir to match 2015. The map is drawn without internet.
- Recording differs: London lists every police-reported injury accident; Indian police records are less likely to include minor accidents, so deaths per 100 accidents is not an exact like-for-like measure.

## Data cleaning (`scripts/data_processing.py`)
1. Remove duplicate accident IDs.
2. Convert types safely; invalid values become missing instead of crashing.
3. Drop records with no date or severity, or coordinates outside Great Britain.
4. Decode STATS19 numeric codes to labels; unknown codes become "Unknown".
5. Derive hour, time band, weekend flag, year, month, severity flag, speed and vehicle groups.
6. Save a compressed Parquet copy and cache the result in memory for fast filtering.

## Notes
- The street-map views load map tiles from the internet. Without a connection, use **Offline density grid** on the Geography tab.
- Cramér's V shows association, not cause.
