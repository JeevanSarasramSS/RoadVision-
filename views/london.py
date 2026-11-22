"""London section: record-level analysis of 74,359 STATS19 accidents (Greater London, 2013-2015)."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from scripts.analysis import factor_strength, hotspots, insights, severe_rate_table
from scripts.data_processing import BAND_ORDER, DAY_ORDER
from scripts.ui import (BLUE, CARD, CYAN, GRID, MONTHS, MUTED, ORANGE, RED, RISK, SEQ, SEV_COLORS, kpi, rate_bar,
                        show)


def render(df_all, report):
    # ---------- Sidebar filters ----------
    st.sidebar.markdown("### 🇬🇧 London filters")
    st.sidebar.caption("Apply to every London chart.")
    min_d, max_d = df_all["Date"].min().date(), df_all["Date"].max().date()
    dates = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
    forces = sorted(df_all["Force"].unique())
    sel_force = st.sidebar.multiselect("Region (police force)", forces, default=forces)
    sel_sev = st.sidebar.multiselect("Severity", list(SEV_COLORS), default=list(SEV_COLORS))
    hours = st.sidebar.slider("Hour of day", 0, 23, (0, 23))
    with st.sidebar.expander("Conditions"):
        weathers = sorted(df_all["Weather"].unique())
        sel_weather = st.multiselect("Weather", weathers, default=weathers)
        surfaces = sorted(df_all["Surface"].unique())
        sel_surface = st.multiselect("Road surface", surfaces, default=surfaces)
        lights = sorted(df_all["Light"].unique())
        sel_light = st.multiselect("Lighting", lights, default=lights)
    st.sidebar.divider()
    st.sidebar.caption("Source: UK Department for Transport STATS19 road safety data, "
                       "Greater London extract, 2013-2015.")

    # A date range is incomplete while the user is still picking the end date.
    start, end = dates if isinstance(dates, (tuple, list)) and len(dates) == 2 else (min_d, max_d)
    mask = (df_all["Date"].dt.date.between(start, end) & df_all["Force"].isin(sel_force)
            & df_all["Severity"].isin(sel_sev) & df_all["Weather"].isin(sel_weather)
            & df_all["Surface"].isin(sel_surface) & df_all["Light"].isin(sel_light)
            & (df_all["Hour"].between(*hours) | (df_all["Hour"].isna() & (hours == (0, 23)))))
    f = df_all[mask]

    # ---------- Header ----------
    st.markdown(f"""<div class="hero"><div class="t">ROAD<span>VISION</span> – London Road Accident Analytics</div>
    <div class="s">Coverage: <b>Greater London, United Kingdom only</b> (not global) · {min_d:%d %b %Y} – {max_d:%d %b %Y}
    · police-reported injury accidents</div>
    <span class="pill">{report['clean_rows']:,} records</span><span class="pill">{report['raw_columns']} source fields</span>
    <span class="pill">{(max_d - min_d).days + 1:,} days</span><span class="pill">Showing {len(f):,} after filters</span>
    </div>""", unsafe_allow_html=True)

    if f.empty:
        st.warning("No accidents match these filters. Widen the selection in the sidebar.")
        return

    # ---------- KPIs ----------
    days = (end - start).days + 1
    top = f["Force"].value_counts()
    severe = int(f["Severe"].sum())
    c = st.columns(6)
    kpi(c[0], "Total accidents", f"{len(f):,}", "in current selection")
    kpi(c[1], "Serious or fatal", f"{severe:,}", f"{severe / len(f):.1%} of accidents", "o")
    kpi(c[2], "Fatal accidents", f"{(f['Severity'] == 'Fatal').sum():,}", "accidents, not persons killed", "o")
    kpi(c[3], "Total casualties", f"{f['Number_of_Casualties'].sum():,}", f"{f['Number_of_Casualties'].mean():.2f} per accident")
    kpi(c[4], "Accidents per day", f"{len(f) / days:.1f}", f"over {days:,} days")
    kpi(c[5], "Most affected region", top.index[0].replace("Metropolitan", "Met").replace("City of London Police", "City of London"), f"{top.iloc[0] / len(f):.1%} of accidents")
    st.write("")

    tabs = st.tabs(["📊 Overview", "⏱️ Time Patterns", "🗺️ Geography & Hotspots", "⚠️ Risk Factors",
                    "🧹 Data Pipeline", "🔎 Data Explorer"])

    # ================= TAB 1: OVERVIEW =================
    with tabs[0]:
        st.subheader("Key insights")
        st.caption("Generated automatically from the current selection. They update when you change a filter.")
        found = insights(f)
        if found:
            for i in range(0, len(found), 3):
                cols = st.columns(3)
                for col, (icon, head, body) in zip(cols, found[i:i + 3]):
                    col.markdown(f'<div class="ins"><div class="h">{icon} {head}</div><div class="b">{body}</div></div>',
                                 unsafe_allow_html=True)
                st.write("")
        else:
            st.info("Select more data to generate insights.")

        left, right = st.columns([2, 1])
        with left:
            monthly = f.set_index("Date").resample("MS").agg(Accidents=("Severe", "size"), Severe=("Severe", "mean")).reset_index()
            monthly["Trend"] = monthly["Accidents"].rolling(3, min_periods=1).mean()
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=monthly["Date"], y=monthly["Accidents"], name="Accidents", marker_color=BLUE, opacity=.55)
            fig.add_scatter(x=monthly["Date"], y=monthly["Trend"], name="3-month average", line=dict(color=CYAN, width=3))
            fig.add_scatter(x=monthly["Date"], y=monthly["Severe"] * 100, name="Serious or fatal %",
                            line=dict(color=ORANGE, dash="dot"), secondary_y=True)
            fig.update_layout(title="Monthly accidents, trend and severity", hovermode="x unified",
                              legend=dict(orientation="h", y=1.12, x=.35))
            fig.update_yaxes(title_text="Accidents", secondary_y=False)
            fig.update_yaxes(title_text="Serious or fatal (%)", secondary_y=True, showgrid=False)
            show(fig, 380, legend=True)
        with right:
            sev = f["Severity"].value_counts().reset_index()
            fig = px.pie(sev, names="Severity", values="count", hole=.62, title="Severity distribution",
                         color="Severity", color_discrete_map=SEV_COLORS)
            fig.update_traces(textinfo="percent", hovertemplate="%{label}: %{value:,} accidents<extra></extra>")
            fig.add_annotation(text=f"<b>{len(f):,}</b><br>accidents", showarrow=False, font_size=14)
            show(fig, 380, legend=True)

        left, right = st.columns(2)
        with left:
            season = f.groupby(["Year", "Month"]).size().reset_index(name="Accidents")
            season["Month"] = season["Month"].map(lambda m: MONTHS[m - 1])
            season["Year"] = season["Year"].astype(str)
            show(px.line(season, x="Month", y="Accidents", color="Year", markers=True, title="Year-over-year comparison by month",
                         category_orders={"Month": MONTHS}, color_discrete_sequence=[MUTED, BLUE, CYAN, ORANGE]),
                 legend=True)
        with right:
            yr = f.groupby("Year").agg(Accidents=("Severe", "size"), Severe=("Severe", "mean")).reset_index()
            yr["Change"] = yr["Accidents"].pct_change() * 100
            yr["Label"] = [f"{n:,}" + ("" if pd.isna(c) else f"<br>{c:+.1f}% vs prev") for n, c in zip(yr["Accidents"], yr["Change"])]
            yr["Year"] = yr["Year"].astype(str)
            fig = px.bar(yr, x="Year", y="Accidents", text="Label", title="Accidents per year and year-over-year change",
                         color="Severe", color_continuous_scale=RISK[1:], hover_data={"Severe": ":.1%"},
                         labels={"Severe": "Serious or fatal"})
            fig.update_traces(textposition="inside", insidetextanchor="end", textfont_color="white")
            fig.update_coloraxes(colorbar=dict(title="Severe", tickformat=".1%"))
            show(fig)

    # ================= TAB 2: TIME PATTERNS =================
    with tabs[1]:
        left, right = st.columns([3, 2])
        with left:
            heat = (f.dropna(subset=["Hour"]).pivot_table(index="Day", columns="Hour", values="Severe", aggfunc="size", fill_value=0)
                    .reindex(index=DAY_ORDER, columns=range(24), fill_value=0))
            fig = px.imshow(heat, aspect="auto", title="Weekly rhythm: accidents by day and hour",
                            color_continuous_scale=SEQ, labels=dict(x="Hour (24h)", y="", color="Accidents"))
            fig.update_xaxes(dtick=2)
            show(fig, 380)
        with right:
            by_hour = f["Hour"].dropna().astype(int).value_counts().reindex(range(24), fill_value=0)
            fig = go.Figure(go.Barpolar(r=by_hour.values, theta=[h * 15 for h in range(24)], width=[14] * 24,
                                        marker_color=by_hour.values, marker_colorscale=SEQ[1:],
                                        customdata=list(range(24)),
                                        hovertemplate="%{customdata:02d}:00 – %{r:,} accidents<extra></extra>"))
            fig.update_layout(title="24-hour accident clock", polar=dict(
                bgcolor=CARD, radialaxis=dict(showticklabels=False, gridcolor=GRID),
                angularaxis=dict(direction="clockwise", rotation=90, gridcolor=GRID,
                                 tickvals=list(range(0, 360, 45)), ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)])))
            show(fig, 380)

        # Calendar heatmap: one square per day
        years = sorted(f["Year"].unique())
        year = st.segmented_control("Calendar year", years, default=years[-1], key="cal_year") or years[-1]
        daily = f[f["Year"] == year].groupby(f["Date"].dt.normalize()).size()
        all_days = pd.date_range(f"{year}-01-01", f"{year}-12-31")
        daily = daily.reindex(all_days, fill_value=0)
        first_wd = all_days[0].weekday()
        week = [(d.dayofyear - 1 + first_wd) // 7 for d in all_days]
        cal = pd.DataFrame({"week": week, "wd": all_days.weekday, "n": daily.values, "date": all_days.strftime("%a %d %b %Y")})
        z = cal.pivot(index="wd", columns="week", values="n")
        text = cal.pivot(index="wd", columns="week", values="date")
        fig = go.Figure(go.Heatmap(z=z.values, x=z.columns, y=DAY_ORDER, text=text.values, xgap=3, ygap=3,
                                   colorscale=SEQ, hovertemplate="%{text}<br>%{z} accidents<extra></extra>",
                                   colorbar=dict(title="Accidents")))
        month_starts = [(pd.Timestamp(year, m, 1).dayofyear - 1 + first_wd) // 7 for m in range(1, 13)]
        fig.update_layout(title=f"Daily accident calendar – {year} (busiest day: {daily.idxmax():%d %b}, {daily.max()} accidents)")
        fig.update_xaxes(tickvals=month_starts, ticktext=MONTHS, showgrid=False)
        fig.update_yaxes(autorange="reversed", showgrid=False)
        show(fig, 300)

        left, right = st.columns(2)
        with left:
            band = f[f["Time_Band"] != "Unknown"].groupby(["Time_Band", "Severity"]).size().reset_index(name="Accidents")
            show(px.bar(band, x="Time_Band", y="Accidents", color="Severity", color_discrete_map=SEV_COLORS,
                        category_orders={"Time_Band": BAND_ORDER, "Severity": ["Slight", "Serious", "Fatal"]},
                        title="Accidents by time of day and severity", labels={"Time_Band": ""}), legend=True)
        with right:
            g = f.groupby("Day")["Severe"].agg(Accidents="size", Rate="mean").reindex(DAY_ORDER).reset_index()
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=g["Day"], y=g["Accidents"], name="Accidents", marker_color=BLUE)
            fig.add_scatter(x=g["Day"], y=g["Rate"] * 100, name="Serious or fatal %", mode="lines+markers",
                            line=dict(color=ORANGE, width=3), secondary_y=True)
            fig.update_layout(title="Volume vs severity by day of week", legend=dict(orientation="h", y=1.12, x=.3))
            fig.update_yaxes(title_text="Serious or fatal (%)", secondary_y=True, showgrid=False)
            show(fig, legend=True)

    # ================= TAB 3: GEOGRAPHY =================
    with tabs[2]:
        view = st.radio("Map view", ["Hotspot heatmap (street map)", "Accident points (street map)", "Offline density grid"],
                        horizontal=True, help="The street maps load background tiles from the internet. "
                                              "Use the offline grid if there is no connection.")
        left, right = st.columns([2, 1])
        hs = hotspots(f, top=10)
        with left:
            center = dict(lat=f["Latitude"].median(), lon=f["Longitude"].median())
            hover = {"Date": "|%d %b %Y", "Road": True, "Number_of_Casualties": True, "Latitude": False, "Longitude": False}
            if view.startswith("Hotspot"):
                fig = px.density_map(f, lat="Latitude", lon="Longitude", radius=6, zoom=9.2, center=center,
                                     map_style="carto-darkmatter", color_continuous_scale="Turbo",
                                     title=f"Accident density – all {len(f):,} accidents")
                fig.add_scattermap(lat=hs["cell_lat"], lon=hs["cell_lon"], mode="markers+text", text=hs["Rank"].astype(str),
                                   marker=dict(size=18, color="rgba(0,0,0,0)"), textfont=dict(color="white", size=13),
                                   hovertext=[f"Hotspot #{r}: {a} accidents" for r, a in zip(hs["Rank"], hs["Accidents"])],
                                   hoverinfo="text", name="Top 10 hotspots")
                fig.update_coloraxes(showscale=False)
            elif view.startswith("Accident"):
                pts = f.sample(min(8000, len(f)), random_state=42)
                fig = px.scatter_map(pts, lat="Latitude", lon="Longitude", color="Severity", color_discrete_map=SEV_COLORS,
                                     category_orders={"Severity": ["Slight", "Serious", "Fatal"]}, opacity=.6, zoom=9.2,
                                     center=center, map_style="carto-darkmatter", hover_data=hover,
                                     title=f"Accident locations ({len(pts):,} of {len(f):,} shown)")
                fig.update_traces(marker_size=5)
            else:
                fig = px.density_heatmap(f, x="Longitude", y="Latitude", nbinsx=70, nbinsy=55, color_continuous_scale=SEQ,
                                         title="Accident density grid (offline)")
                # At London's latitude one degree of longitude is about 0.62 of a degree of latitude.
                fig.update_yaxes(scaleanchor="x", scaleratio=1 / 0.62)
            fig.update_layout(legend=dict(orientation="h", y=-0.02))
            show(fig, 560, legend=not view.startswith("Offline"))
        with right:
            st.markdown("**Top 10 accident hotspots** (1 km grid cells)")
            st.dataframe(hs[["Rank", "Accidents", "Severe_pct", "Casualties", "cell_lat", "cell_lon"]], hide_index=True,
                         height=390, column_config={
                             "Accidents": st.column_config.ProgressColumn("Accidents", format="%d", min_value=0,
                                                                          max_value=int(hs["Accidents"].max())),
                             "Severe_pct": st.column_config.NumberColumn("Severe %", format="%.1f"),
                             "cell_lat": st.column_config.NumberColumn("Lat", format="%.3f"),
                             "cell_lon": st.column_config.NumberColumn("Lon", format="%.3f")})
            share = hs["Accidents"].sum() / len(f)
            st.caption(f"These 10 cells cover about 10 km² yet hold **{share:.1%}** of all accidents in the selection.")
            reg = f["Force"].value_counts().rename_axis("Force").reset_index(name="Accidents")
            st.dataframe(reg, hide_index=True, column_config={"Force": "Region (police force)"})

        left, right = st.columns(2)
        with left:
            show(px.pie(f["Area"].value_counts().reset_index(), names="Area", values="count", hole=.6,
                        title="Urban vs rural", color_discrete_sequence=[CYAN, ORANGE, MUTED]), legend=True)
        with right:
            rate_bar(f, "Area", "Serious-or-fatal share: urban vs rural", CYAN)

    # ================= TAB 4: RISK FACTORS =================
    with tabs[3]:
        st.subheader("Which factors are linked to more severe accidents?")
        factors = {"Speed limit": "Speed", "Lighting": "Light", "Road type": "Road", "Time of day": "Time_Band",
                   "Vehicles involved": "Vehicles", "Weather": "Weather", "Road surface": "Surface",
                   "Day of week": "Day", "Urban / rural": "Area"}
        left, right = st.columns([1, 1])
        with left:
            fs = factor_strength(f, factors)
            fig = px.bar(fs, x="Cramers_V", y="Factor", orientation="h", color="Cramers_V", color_continuous_scale=RISK[1:],
                         title="Association with severity (Cramér's V from chi-square test)",
                         hover_data={"Chi_square": ":,.0f", "Categories": True, "Cramers_V": ":.3f"},
                         labels={"Cramers_V": "Cramér's V (0 = none, 1 = perfect)", "Factor": ""})
            fig.update_coloraxes(showscale=False)
            show(fig, 380)
            st.caption("Cramér's V measures how strongly each factor and severity move together. "
                       "Values below 0.1 are weak links. This shows association, not cause.")
        with right:
            sub = f[(f["Weather"] != "Unknown") & (f["Surface"] != "Unknown")]
            piv = sub.groupby(["Weather", "Surface"])["Severe"].agg(["mean", "size"]).reset_index()
            piv = piv[piv["size"] >= 20]
            z = piv.pivot(index="Weather", columns="Surface", values="mean") * 100
            cnt = piv.pivot(index="Weather", columns="Surface", values="size")
            fig = go.Figure(go.Heatmap(z=z.values, x=z.columns, y=z.index, colorscale=RISK, customdata=cnt.values,
                                       text=z.map(lambda v: "" if pd.isna(v) else f"{v:.1f}%").values, texttemplate="%{text}",
                                       hovertemplate="%{y} on %{x}<br>%{z:.1f}% serious or fatal<br>%{customdata:,} accidents<extra></extra>",
                                       colorbar=dict(title="Severe %")))
            fig.update_layout(title="Risk matrix: weather × road surface (serious or fatal %)")
            show(fig, 380)
            st.caption("Cells with fewer than 20 accidents are hidden so small samples don't mislead.")

        left, right = st.columns(2)
        with left:
            sp = severe_rate_table(f, "Speed", min_count=20)
            sp["n"] = sp["Speed"].str.extract(r"(\d+)").astype(int)
            sp = sp.sort_values("n")
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=sp["Speed"], y=sp["Accidents"], name="Accidents", marker_color=BLUE)
            fig.add_scatter(x=sp["Speed"], y=sp["Rate"], name="Serious or fatal %", mode="lines+markers",
                            line=dict(color=ORANGE, width=3), secondary_y=True)
            fig.update_layout(title="Speed limit: how many accidents vs how severe", legend=dict(orientation="h", y=1.12, x=.3))
            fig.update_yaxes(type="log", title_text="Accidents (log)", secondary_y=False)
            fig.update_yaxes(title_text="Serious or fatal (%)", secondary_y=True, showgrid=False, tickformat=".1f")
            show(fig, legend=True)
        with right:
            rate_bar(f, "Light", "Serious-or-fatal share by lighting")
        left, right = st.columns(2)
        with left:
            rate_bar(f, "Road", "Serious-or-fatal share by road type", BLUE)
        with right:
            rate_bar(f, "Vehicles", "Serious-or-fatal share by vehicles involved", CYAN)

    # ================= TAB 5: DATA PIPELINE =================
    with tabs[4]:
        st.subheader("How the data is processed")
        steps = [("1 · Ingest", f"Read {report['csv_mb']} MB CSV with Pandas ({report['raw_rows']:,} rows, {report['raw_columns']} columns)."),
                 ("2 · Deduplicate", f"Drop repeated accident IDs: {report['duplicates_removed']:,} removed."),
                 ("3 · Validate", f"Parse dates and numbers; drop bad dates or coordinates outside Great Britain: {report['invalid_removed']:,} removed."),
                 ("4 · Decode", "Map STATS19 numeric codes to readable labels; unknown codes become 'Unknown'."),
                 ("5 · Enrich", "Add hour, time band, weekend flag, year, month, severity flag, speed and vehicle groups."),
                 ("6 · Store", f"Save a compressed Parquet copy ({report['parquet_mb']} MB) and cache in memory for fast filtering.")]
        cols = st.columns(len(steps))
        for col, (h, b) in zip(cols, steps):
            col.markdown(f'<div class="step"><div class="h">{h}</div><div class="b">{b}</div></div>', unsafe_allow_html=True)
        st.write("")
        c = st.columns(4)
        kpi(c[0], "Raw records", f"{report['raw_rows']:,}")
        kpi(c[1], "Clean records", f"{report['clean_rows']:,}", f"{report['clean_rows'] / report['raw_rows']:.1%} kept")
        kpi(c[2], "Fields after enrichment", f"{report['clean_columns']}", f"from {report['raw_columns']} source fields", "o")
        kpi(c[3], "Load + clean time", f"{report['load_seconds']} s", "then cached in memory", "o")
        st.write("")
        left, right = st.columns(2)
        with left:
            miss = pd.Series(report["missing_by_column"]).rename_axis("Column").reset_index(name="Missing")
            miss["Complete %"] = ((1 - miss["Missing"] / report["raw_rows"]) * 100).round(2)
            fig = px.bar(miss.sort_values("Complete %"), x="Complete %", y="Column", orientation="h",
                         title="Data completeness per source column", color_discrete_sequence=[CYAN],
                         hover_data={"Missing": True}, range_x=[0, 100.5])
            show(fig, 460)
        with right:
            st.markdown("**Data dictionary (fields used)**")
            st.dataframe(pd.DataFrame([
                ("Accident_Index", "Unique accident ID", "Deduplication key"),
                ("Date, Time", "When it happened", "Trends, calendar, hour, time band"),
                ("Latitude, Longitude", "Where it happened", "Maps, hotspot grid"),
                ("Accident_Severity", "Fatal / Serious / Slight", "Severity analysis, filter"),
                ("Number_of_Casualties", "People injured or killed", "Casualty KPI, hotspots"),
                ("Number_of_Vehicles", "Vehicles involved", "Vehicle risk chart"),
                ("Speed_limit", "Posted limit (mph)", "Speed risk chart"),
                ("Weather_Conditions", "Weather at the time", "Weather risk, filter"),
                ("Road_Surface_Conditions", "Dry, wet, ice...", "Surface risk, filter"),
                ("Light_Conditions", "Daylight or dark", "Lighting risk, filter"),
                ("Road_Type", "Carriageway type", "Road type risk"),
                ("Police_Force", "Reporting force", "Region filter and comparison"),
                ("Urban_or_Rural_Area", "Urban or rural", "Area comparison"),
            ], columns=["Field", "Meaning", "Used for"]), hide_index=True, height=460)
        st.info("**Scope and limits.** The data covers Greater London only, 2013-2015, so it is not global. "
                "It has no vehicle type, cause, or count of persons killed, so fatal *accidents* are shown instead.")

    # ================= TAB 6: DATA EXPLORER =================
    with tabs[5]:
        st.subheader("Explore the filtered records")
        cols = ["Accident_Index", "Date", "Time", "Day", "Severity", "Number_of_Casualties", "Number_of_Vehicles",
                "Speed_limit", "Road", "Weather", "Surface", "Light", "Area", "Force", "Latitude", "Longitude"]
        st.caption(f"{len(f):,} records match the sidebar filters. The table shows the first 1,000; the download has all of them.")
        st.dataframe(f[cols].head(1000), hide_index=True, height=480,
                     column_config={"Date": st.column_config.DateColumn(format="DD MMM YYYY")})
        st.download_button("⬇️ Download filtered data (CSV)", f[cols].to_csv(index=False).encode("utf-8"),
                           file_name="roadvision_filtered.csv", mime="text/csv")
        st.markdown("**Summary statistics**")
        st.dataframe(f[["Number_of_Casualties", "Number_of_Vehicles", "Speed_limit", "Hour"]].describe().T.round(2))

