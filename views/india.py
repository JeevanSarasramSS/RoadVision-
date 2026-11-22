"""
India section: state-wise analysis of official MoRTH data (all 36 States/UTs, 2012-2015).
Mirrors the London section, but works with state-level totals because India does not
publish per-accident records.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from scripts.india import (DAY_SLOTS, REPORT_TOTALS, SLOT_COLS, SLOTS, SOURCE, WEATHER_COLS, YEARS, load_geojson,
                           load_india, load_states, verify_states)
from scripts.ui import (BLUE, CARD, CYAN, GRID, MONTHS, MUTED, ORANGE, RED, RISK, SEQ, hero, insight_cards, kpi,
                        show)

ZONE_COLORS = {"Southern": CYAN, "Western": BLUE, "Northern": ORANGE, "Central": "#A78BFA",
               "Eastern": "#34D399", "North-Eastern": "#F472B6"}
ROAD = {"nh": "National Highways", "sh": "State Highways", "other": "Other roads"}
ROAD_COLORS = {"National Highways": RED, "State Highways": ORANGE, "Other roads": BLUE}

# Map metrics: label -> (column, colour scale, hover format, note)
METRICS = {
    "Accidents (2015)": ("accidents_2015", SEQ[1:], ",.0f", ""),
    "Persons killed (2015)": ("killed_2015", RISK[1:], ",.0f", ""),
    "Deaths per 100 accidents": ("deaths_per_100", RISK[1:], ".1f", "How deadly an average accident is."),
    "Accidents per lakh population": ("acc_per_lakh", SEQ[1:], ".1f",
                                      "Population-adjusted. Blank for Andhra Pradesh and Telangana (shared population base after the 2014 split)."),
    "Deaths per lakh population": ("killed_per_lakh", RISK[1:], ".1f",
                                   "Population-adjusted death risk. Blank for Andhra Pradesh and Telangana."),
    "Change in accidents 2013→2015 (%)": ("change_2013_2015", ["#22D3EE", "#131C2E", "#F97316"], "+.1f",
                                          "Blank for Andhra Pradesh and Telangana (split in 2014)."),
}


@st.cache_data
def get_india():
    return load_states(), load_india(), load_geojson()


def short(name):
    return (name.replace("Andaman & Nicobar Islands", "A&N Islands").replace("Dadra & Nagar Haveli", "D&N Haveli")
            .replace("Jammu & Kashmir", "J&K"))


def state_map(geo, all_states, data, col, scale, fmt, metric):
    """
    India state map drawn as filled shapes on plain lon/lat axes.
    Works fully offline (no map tiles, no world outline download, no WebGL).
    """
    from plotly.colors import sample_colorscale
    shapes = {f["properties"]["state"]: f["geometry"]["coordinates"] for f in geo["features"]}
    vals = data.set_index("map_name")[col]
    lo, hi = float(vals.min()), float(vals.max())
    if col == "change_2013_2015":                      # diverging scale centred on zero
        lim = max(abs(lo), abs(hi)) or 1
        lo, hi = -lim, lim
    info = all_states.set_index("map_name")
    fig = go.Figure()
    for name, polys in shapes.items():
        xs, ys = [], []
        for poly in polys:
            ring = poly[0]
            xs += [p[0] for p in ring] + [None]
            ys += [p[1] for p in ring] + [None]
        if name in vals.index:
            v = float(vals[name])
            color = sample_colorscale(scale, [(v - lo) / (hi - lo) if hi > lo else .5])[0]
            label = ("{:" + fmt + "}").format(v)
        else:
            color, label = "#1E293B", "–"
        row = info.loc[name]
        fig.add_scatter(x=xs, y=ys, fill="toself", fillcolor=color, mode="lines", line=dict(color="#0B1220", width=.6),
                        hoveron="fills", name=row["state"], showlegend=False,
                        text=f"<b>{row['state']}</b><br>{metric}: {label}<br>Accidents 2015: {int(row['accidents_2015']):,}"
                             f"<br>Killed 2015: {int(row['killed_2015']):,}", hoverinfo="text")
    # invisible trace that only draws the colour bar
    fig.add_scatter(x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
                    marker=dict(colorscale=scale, cmin=lo, cmax=hi, color=[lo], showscale=True,
                                colorbar=dict(thickness=12, title="")))
    fig.update_xaxes(visible=False)
    # 1 degree of longitude is about 0.93 of a degree of latitude at India's mid-latitude (22°N)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1.08)
    fig.update_layout(margin=dict(l=0, r=0, t=50, b=0))
    return fig


def render():
    states, nat, geo = get_india()

    # ---------- Sidebar filters ----------
    st.sidebar.markdown("### 🇮🇳 India filters")
    zones = list(ZONE_COLORS)
    sel_zones = st.sidebar.multiselect("Zone (zonal council)", zones, default=zones,
                                       help="States grouped by the Ministry of Home Affairs zonal councils.")
    in_zone = sorted(states.loc[states["zone"].isin(sel_zones), "state"])
    sel_states = st.sidebar.multiselect("States / UTs", in_zone, default=in_zone)
    year = st.sidebar.select_slider("Headline year", YEARS, value=2015,
                                    help="Applies to the KPI cards. Breakdowns (time, roads, weather) exist for 2015 only.")
    st.sidebar.divider()
    st.sidebar.caption(f"Source: {SOURCE} (Ministry of Road Transport & Highways). State-level official tables.")

    s = states[states["state"].isin(sel_states)].copy()
    hero('ROAD<span>VISION</span> – India Road Accident Analytics',
         f"<b>All 36 States/UTs of India</b> · official {SOURCE} · 2012–2015 · state-level totals "
         "(India publishes tables, not one row per accident)",
         [f"{len(s)} of 36 States/UTs selected", f"{s['accidents_2015'].sum():,} accidents in 2015",
          "37 columns verified vs report", "Breakdowns: 2015"])
    if s.empty:
        st.warning("No states selected. Pick at least one zone and state in the sidebar.")
        return

    # ---------- KPIs ----------
    acc, kil, inj = s[f"accidents_{year}"].sum(), s[f"killed_{year}"].sum(), s[f"injured_{year}"].sum()
    if acc == 0:
        st.warning(f"No {year} figures for the selected states (Telangana was formed in 2014). Choose 2014 or 2015.")
        return
    top = s.sort_values(f"accidents_{year}", ascending=False).iloc[0]
    days = 366 if year == 2012 else 365
    c = st.columns(6)
    kpi(c[0], f"Accidents ({year})", f"{acc:,.0f}", "police-recorded")
    kpi(c[1], f"Persons killed ({year})", f"{kil:,.0f}", f"about {kil / days:,.0f} per day", "o")
    kpi(c[2], f"Persons injured ({year})", f"{inj:,.0f}", f"{inj / acc:.2f} per accident" if acc else "")
    kpi(c[3], "Deaths per 100 accidents", f"{kil / acc * 100:.1f}" if acc else "–", f"in {year}", "o")
    kpi(c[4], "Accidents per day", f"{acc / days:,.0f}", f"{year}")
    kpi(c[5], "Most affected state", short(top["state"]), f"{top[f'accidents_{year}'] / acc:.1%} of accidents")
    st.write("")

    tabs = st.tabs(["📊 Overview", "🗺️ State Map & Ranking", "⏱️ Time Patterns", "🛣️ Roads & Area",
                    "⚠️ Causes & Weather", "🧾 Data & Sources"])

    # ================= OVERVIEW =================
    with tabs[0]:
        st.subheader("Key insights")
        st.caption("Computed from the selected states. They update when you change the sidebar filters.")
        cards = []
        big = s[s["accidents_2015"] >= 1000]
        if not big.empty:
            dead = big.loc[big["deaths_per_100"].idxmax()]
            safe = big.loc[big["deaths_per_100"].idxmin()]
            cards.append(("☠️", f"Deadliest: {dead['state']}",
                          f"{dead['deaths_per_100']:.1f} deaths per 100 accidents vs {safe['deaths_per_100']:.1f} in "
                          f"{safe['state']} (states with 1,000+ accidents, 2015)."))
        top3 = s.nlargest(3, "accidents_2015")
        cards.append(("🏆", f"Top 3 states: {top3['accidents_2015'].sum() / s['accidents_2015'].sum():.0%} of accidents",
                      ", ".join(f"{r.state} ({r.accidents_2015:,})" for r in top3.itertuples()) + " in 2015."))
        g = s.dropna(subset=["change_2013_2015"])
        g = g[g["accidents_2013"] >= 1000]
        if not g.empty:
            up = g.loc[g["change_2013_2015"].idxmax()]
            cards.append(("📈", f"Fastest rise: {up['state']}",
                          f"Accidents {up['change_2013_2015']:+.1f}% from 2013 to 2015 "
                          f"({int(up['accidents_2013']):,} → {int(up['accidents_2015']):,})."))
        slots = s[SLOT_COLS].sum()
        peak = SLOTS[slots.values.argmax()]
        cards.append(("🕔", f"Peak time: {peak.replace('-', ':00–')}:00",
                      f"{slots.max() / slots.sum():.1%} of accidents; night (18:00–06:00) holds "
                      f"{slots[[c for c, sl in zip(SLOT_COLS, SLOTS) if sl not in DAY_SLOTS]].sum() / slots.sum():.1%}."))
        nh_a, nh_k = s["nh_acc"].sum() / s["accidents_2015"].sum(), s["nh_killed"].sum() / s["killed_2015"].sum()
        cards.append(("🛣️", "National Highways are the deadliest roads",
                      f"{nh_a:.0%} of accidents but {nh_k:.0%} of deaths happen on National Highways."))
        r_k = s["rural_killed"].sum() / s["killed_2015"].sum()
        cards.append(("🌾", f"{r_k:.0%} of deaths are in rural areas",
                      f"Rural: {s['rural_killed'].sum() / s['rural_acc'].sum() * 100:.1f} deaths per 100 accidents; "
                      f"urban: {s['urban_killed'].sum() / s['urban_acc'].sum() * 100:.1f}."))
        insight_cards(cards)

        left, right = st.columns([2, 1])
        with left:
            tr = pd.DataFrame({"Year": YEARS,
                               "Accidents": [s[f"accidents_{y}"].sum() for y in YEARS],
                               "Persons killed": [s[f"killed_{y}"].sum() for y in YEARS],
                               "Persons injured": [s[f"injured_{y}"].sum() for y in YEARS]})
            tr = tr[tr[["Accidents", "Persons killed"]].sum(axis=1) > 0]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=tr["Year"], y=tr["Accidents"], name="Accidents", marker_color=BLUE, opacity=.7)
            fig.add_scatter(x=tr["Year"], y=tr["Persons injured"], name="Persons injured", line=dict(color=CYAN, width=3))
            fig.add_scatter(x=tr["Year"], y=tr["Persons killed"], name="Persons killed", line=dict(color=RED, width=3),
                            secondary_y=True)
            fig.update_layout(title="Trend 2012–2015 for the selected states", hovermode="x unified",
                              legend=dict(orientation="h", y=1.12, x=.3))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(title_text="Accidents / injured", secondary_y=False)
            fig.update_yaxes(title_text="Persons killed", secondary_y=True, showgrid=False, rangemode="tozero")
            fig.update_yaxes(rangemode="tozero", secondary_y=False)
            show(fig, 380, legend=True)
            if {"Andhra Pradesh", "Telangana"} & set(s["state"]):
                st.caption("Andhra Pradesh's 2012–2013 figures include Telangana (formed June 2014).")
        with right:
            fa = s["fatal_accidents_2015"].sum()
            sev = pd.DataFrame({"Type": ["Fatal", "Non-fatal"], "Accidents": [fa, s["accidents_2015"].sum() - fa]})
            fig = px.pie(sev, names="Type", values="Accidents", hole=.62, title="Fatal vs non-fatal accidents (2015)",
                         color="Type", color_discrete_map={"Fatal": RED, "Non-fatal": BLUE})
            fig.update_traces(textinfo="percent", hovertemplate="%{label}: %{value:,} accidents<extra></extra>")
            fig.add_annotation(text=f"<b>{s['accidents_2015'].sum():,}</b><br>accidents", showarrow=False, font_size=14)
            show(fig, 380, legend=True)

        left, right = st.columns(2)
        with left:
            t10 = s.nlargest(10, "accidents_2015").sort_values("accidents_2015")
            fig = make_subplots(specs=[[{"secondary_y": False}]])
            fig.add_bar(y=t10["state"], x=t10["accidents_2015"], orientation="h", name="Accidents", marker_color=BLUE)
            fig.add_bar(y=t10["state"], x=t10["killed_2015"], orientation="h", name="Persons killed", marker_color=RED)
            fig.update_layout(title="Top 10 states by accidents (2015)", barmode="overlay",
                              legend=dict(orientation="h", y=1.1, x=.4))
            show(fig, 400, legend=True)
        with right:
            z = s.groupby("zone")[["accidents_2015", "killed_2015"]].sum().reset_index()
            z["Deaths per 100"] = z["killed_2015"] / z["accidents_2015"] * 100
            fig = px.bar(z.sort_values("Deaths per 100"), x="Deaths per 100", y="zone", orientation="h", color="zone",
                         color_discrete_map=ZONE_COLORS, text=z.sort_values("Deaths per 100")["Deaths per 100"].map("{:.1f}".format),
                         hover_data={"accidents_2015": ":,", "killed_2015": ":,"},
                         title="Zones: deaths per 100 accidents (2015)",
                         labels={"zone": "", "accidents_2015": "Accidents", "killed_2015": "Killed"})
            fig.update_traces(textposition="outside", cliponaxis=False)
            show(fig, 400)

    # ================= STATE MAP & RANKING =================
    with tabs[1]:
        metric = st.selectbox("Map metric", list(METRICS), index=2)
        col, scale, fmt, note = METRICS[metric]
        left, right = st.columns([3, 2])
        with left:
            data = s.dropna(subset=[col])
            fig = state_map(geo, states, data, col, scale, fmt, metric)
            fig.update_layout(title=f"{metric} by State/UT")
            show(fig, 620)
            if note:
                st.caption(note)
            st.caption("Hover a state for its figures. Grey = not selected or no figure.")
        with right:
            rate = col in ("deaths_per_100", "change_2013_2015")
            rk = (data[data["accidents_2015"] >= 500] if rate else data).sort_values(col, ascending=False).head(15)
            fig = px.bar(rk.sort_values(col), x=col, y="state", orientation="h", color=col, color_continuous_scale=scale,
                         text=rk.sort_values(col)[col].map(("{:" + fmt + "}").format),
                         title=f"Top 15 States/UTs: {metric}" + (" (500+ accidents)" if rate else ""),
                         labels={col: metric, "state": ""})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_coloraxes(showscale=False)
            show(fig, 620)

        st.subheader("Volume vs severity")
        b = s[s["accidents_2015"] >= 100]
        fig = px.scatter(b, x="accidents_2015", y="deaths_per_100", size="killed_2015", color="zone", text=b["state"].map(short),
                         color_discrete_map=ZONE_COLORS, log_x=True, size_max=45,
                         hover_data={"accidents_2015": ":,", "killed_2015": ":,", "deaths_per_100": ":.1f"},
                         labels={"accidents_2015": "Accidents in 2015 (log scale)", "deaths_per_100": "Deaths per 100 accidents",
                                 "killed_2015": "Killed"},
                         title="Each bubble is a state: many accidents (right) vs deadly accidents (top). Bubble size = deaths")
        fig.update_traces(textposition="top center", textfont_size=10)
        fig.add_hline(y=b["killed_2015"].sum() / b["accidents_2015"].sum() * 100, line_dash="dot", line_color=MUTED,
                      annotation_text="average for selection", annotation_font_color=MUTED)
        show(fig, 520, legend=True)
        st.caption("Top-right: many accidents and deadly ones. Bottom-right: many accidents but fewer deaths per accident. "
                   "States with fewer than 100 accidents are left out.")

        st.subheader("State table with 2012–2015 trend")
        tbl = s[["state", "zone", "accidents_2015", "killed_2015", "injured_2015", "deaths_per_100", "acc_per_lakh",
                 "killed_per_lakh", "change_2013_2015"]].copy()
        # Telangana has no 2012-2013 figures, so drop missing years from its sparkline
        tbl["Accident trend"] = [[v for v in row if pd.notna(v)] for row in s[[f"accidents_{y}" for y in YEARS]].values]
        tbl["Deaths trend"] = [[v for v in row if pd.notna(v)] for row in s[[f"killed_{y}" for y in YEARS]].values]
        st.dataframe(tbl.sort_values("accidents_2015", ascending=False), hide_index=True, height=480, column_config={
            "state": "State / UT", "zone": "Zone",
            "accidents_2015": st.column_config.NumberColumn("Accidents 2015", format="%d"),
            "killed_2015": st.column_config.NumberColumn("Killed 2015", format="%d"),
            "injured_2015": st.column_config.NumberColumn("Injured 2015", format="%d"),
            "deaths_per_100": st.column_config.ProgressColumn("Deaths / 100 acc.", format="%.1f", min_value=0, max_value=100),
            "acc_per_lakh": st.column_config.NumberColumn("Acc. / lakh pop.", format="%.1f"),
            "killed_per_lakh": st.column_config.NumberColumn("Deaths / lakh pop.", format="%.1f"),
            "change_2013_2015": st.column_config.NumberColumn("Change 2013→15 %", format="%+.1f"),
            "Accident trend": st.column_config.LineChartColumn("Accidents 2012–15"),
            "Deaths trend": st.column_config.LineChartColumn("Deaths 2012–15")})

    # ================= TIME PATTERNS =================
    with tabs[2]:
        left, right = st.columns([2, 3])
        tot = s[SLOT_COLS].sum().values
        with left:
            fig = go.Figure(go.Barpolar(r=tot, theta=[i * 45 + 22.5 for i in range(8)], width=[42] * 8,
                                        marker_color=tot, marker_colorscale=SEQ[1:], customdata=SLOTS,
                                        hovertemplate="%{customdata}h: %{r:,} accidents<extra></extra>"))
            fig.update_layout(title="24-hour accident clock (3-hour slots, 2015)", polar=dict(
                bgcolor=CARD, radialaxis=dict(showticklabels=False, gridcolor=GRID),
                angularaxis=dict(direction="clockwise", rotation=90, gridcolor=GRID,
                                 tickvals=[i * 45 for i in range(8)], ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)])))
            show(fig, 440)
        with right:
            hs = s.nlargest(20, "accidents_2015").set_index("state")
            share = hs[SLOT_COLS].div(hs["accidents_2015"], axis=0) * 100
            share.columns = SLOTS
            fig = px.imshow(share.round(1), aspect="auto", color_continuous_scale=SEQ, text_auto=".0f",
                            title="Share of each state's accidents by time slot, % (top 20 states, 2015)",
                            labels=dict(x="Time slot (hours)", y="", color="% of state"))
            fig.update_xaxes(type="category")
            show(fig, 440)

        left, right = st.columns(2)
        with left:
            dn = s[s["accidents_2015"] >= 500].sort_values("night_share")
            fig = px.bar(dn, x="night_share", y="state", orientation="h", color="night_share", color_continuous_scale=SEQ[1:],
                         text=dn["night_share"].map("{:.0f}%".format),
                         title="Night accidents (18:00–06:00) as % of each state's total",
                         labels={"night_share": "% at night", "state": ""})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_coloraxes(showscale=False)
            show(fig, 620)
            st.caption("States with fewer than 500 accidents are left out so small numbers don't mislead.")
        with right:
            m = nat["month"].assign(Month=lambda d: d["category"].astype(int).map(lambda x: MONTHS[x - 1]))
            fig = px.bar(m, x="Month", y="accidents", title="All-India accidents by month (2015)",
                         color="accidents", color_continuous_scale=SEQ[1:], labels={"accidents": "Accidents"},
                         category_orders={"Month": MONTHS})
            fig.update_coloraxes(showscale=False)
            fig.add_hline(y=m["accidents"].mean(), line_dash="dot", line_color=MUTED, annotation_text="monthly average",
                          annotation_font_color=MUTED)
            show(fig, 400)
            st.caption("Month-wise figures are published for All India only, so this chart ignores the state filter.")

    # ================= ROADS & AREA =================
    with tabs[3]:
        rows = []
        for k, label in ROAD.items():
            rows.append({"Road": label, "Accidents": s[f"{k}_acc"].sum(), "Killed": s[f"{k}_killed"].sum()})
        rd = pd.DataFrame(rows)
        rd["Deaths per 100"] = rd["Killed"] / rd["Accidents"] * 100
        left, right = st.columns(2)
        with left:
            long = rd.melt(id_vars="Road", value_vars=["Accidents", "Killed"], var_name="Measure", value_name="n")
            long["Share"] = long["n"] / long.groupby("Measure")["n"].transform("sum") * 100
            fig = px.bar(long, x="Measure", y="Share", color="Road", color_discrete_map=ROAD_COLORS,
                         text=long["Share"].map("{:.0f}%".format), title="Share of accidents vs share of deaths by road type",
                         labels={"Share": "%", "Measure": ""})
            show(fig, 400, legend=True)
        with right:
            fig = px.bar(rd, x="Road", y="Deaths per 100", color="Road", color_discrete_map=ROAD_COLORS,
                         text=rd["Deaths per 100"].map("{:.1f}".format), title="Deaths per 100 accidents by road type (2015)",
                         labels={"Road": ""})
            fig.update_traces(textposition="outside", cliponaxis=False)
            show(fig, 400)

        st.markdown("**Road type mix per state** (share of each state's accidents, top 20 states)")
        hs = s.nlargest(20, "accidents_2015")
        mix = hs.melt(id_vars="state", value_vars=["nh_acc", "sh_acc", "other_acc"], var_name="Road", value_name="n")
        mix["Road"] = mix["Road"].str.replace("_acc", "").map(ROAD)
        mix["Share"] = mix["n"] / mix.groupby("state")["n"].transform("sum") * 100
        fig = px.bar(mix, x="Share", y="state", color="Road", orientation="h", color_discrete_map=ROAD_COLORS,
                     category_orders={"state": hs.sort_values("accidents_2015", ascending=False)["state"].tolist()},
                     hover_data={"n": ":,"}, labels={"Share": "% of state's accidents", "state": "", "n": "Accidents"})
        show(fig, 560, legend=True)

        left, right = st.columns(2)
        with left:
            ur = pd.DataFrame({"Area": ["Urban", "Rural"],
                               "Accidents": [s["urban_acc"].sum(), s["rural_acc"].sum()],
                               "Killed": [s["urban_killed"].sum(), s["rural_killed"].sum()]})
            ur["Deaths per 100"] = ur["Killed"] / ur["Accidents"] * 100
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=ur["Area"], y=ur["Accidents"], name="Accidents", marker_color=BLUE)
            fig.add_bar(x=ur["Area"], y=ur["Killed"], name="Killed", marker_color=RED)
            fig.add_scatter(x=ur["Area"], y=ur["Deaths per 100"], name="Deaths per 100", mode="markers+text",
                            text=ur["Deaths per 100"].map("{:.1f}".format), textposition="top center",
                            marker=dict(size=14, color=ORANGE), secondary_y=True)
            fig.update_layout(title="Urban vs rural (2015)", barmode="group", legend=dict(orientation="h", y=1.12, x=.2))
            fig.update_yaxes(title_text="Deaths per 100 accidents", secondary_y=True, showgrid=False, rangemode="tozero",
                             tickformat=".0f")
            show(fig, 420, legend=True)
        with right:
            rr = s[s["killed_2015"] >= 300].sort_values("rural_death_share")
            fig = px.bar(rr, x="rural_death_share", y="state", orientation="h", color="zone", color_discrete_map=ZONE_COLORS,
                         text=rr["rural_death_share"].map("{:.0f}%".format), title="Share of each state's deaths in rural areas",
                         category_orders={"state": rr["state"].tolist()[::-1]},
                         labels={"rural_death_share": "% of deaths in rural areas", "state": ""})
            fig.update_traces(textposition="outside", cliponaxis=False)
            show(fig, 620, legend=True)

    # ================= CAUSES & WEATHER =================
    with tabs[4]:
        left, right = st.columns(2)
        with left:
            cz = nat["cause"].copy()
            cz["Accident share"] = cz["accidents"] / cz["accidents"].sum() * 100
            cz["Deaths per 100"] = cz["killed"] / cz["accidents"] * 100
            cz = cz.sort_values("accidents")
            fig = px.bar(cz, x="accidents", y="category", orientation="h", log_x=True, color="Deaths per 100",
                         color_continuous_scale=RISK[1:], text=cz["Accident share"].map("{:.1f}%".format),
                         hover_data={"killed": ":,", "Deaths per 100": ":.1f"},
                         title="All-India accidents by cause (2015, log scale; colour = deaths per 100)",
                         labels={"accidents": "Accidents (log)", "category": "", "killed": "Killed"})
            fig.update_traces(textposition="outside", cliponaxis=False)
            show(fig, 520)
            st.caption("Drivers' fault accounts for 77.1% of accidents (MoRTH Table 11.1). Causes are published for All India only.")
        with right:
            w = nat["weather"].copy()
            w["Deaths per 100"] = w["killed"] / w["accidents"] * 100
            w = w.sort_values("Deaths per 100")
            fig = px.bar(w, x="Deaths per 100", y="category", orientation="h", color="Deaths per 100",
                         color_continuous_scale=RISK[1:], text=w["Deaths per 100"].map("{:.1f}".format),
                         hover_data={"accidents": ":,", "killed": ":,"},
                         title="All-India deaths per 100 accidents by weather (2015)", labels={"category": ""})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_coloraxes(showscale=False)
            show(fig, 520)

        st.markdown("**Weather at the time of accidents, by state** (share of each state's 2015 accidents, top 20 states)")
        hs = s.nlargest(20, "accidents_2015")
        wl = hs.melt(id_vars="state", value_vars=list(WEATHER_COLS), var_name="Weather", value_name="n")
        wl["Weather"] = wl["Weather"].map(WEATHER_COLS)
        wl["Share"] = wl["n"] / wl.groupby("state")["n"].transform("sum") * 100
        fig = px.bar(wl, x="Share", y="state", color="Weather", orientation="h",
                     color_discrete_sequence=[BLUE, "#94A3B8", "#64748B", CYAN, "#0E7490", ORANGE, "#334155"],
                     category_orders={"state": hs.sort_values("accidents_2015", ascending=False)["state"].tolist(),
                                      "Weather": list(WEATHER_COLS.values())},
                     hover_data={"n": ":,"}, labels={"Share": "% of state's accidents", "state": "", "n": "Accidents"})
        show(fig, 560, legend=True)
        st.caption("Hail, snow, wind, dust storm and other extraordinary weather could not be split by state reliably, "
                   "so they are grouped as 'Other / not split by state'.")

        cities = nat["city"].assign(**{"Deaths per 100": lambda d: d["killed"] / d["accidents"] * 100}).sort_values("Deaths per 100")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=cities["category"], y=cities["accidents"], name="Accidents", marker_color=BLUE)
        fig.add_scatter(x=cities["category"], y=cities["Deaths per 100"], name="Deaths per 100 accidents",
                        mode="lines+markers+text", text=cities["Deaths per 100"].map("{:.1f}".format), textposition="top center",
                        line=dict(color=ORANGE, width=3), secondary_y=True)
        fig.update_layout(title="Million-plus cities: accidents vs deaths per 100 accidents (2015)",
                          legend=dict(orientation="h", y=-0.15, x=.3))
        fig.update_yaxes(tickformat=".0f", secondary_y=True)
        fig.update_yaxes(title_text="Accidents", secondary_y=False)
        fig.update_yaxes(title_text="Deaths per 100 accidents", secondary_y=True, showgrid=False)
        show(fig, 420, legend=True)

    # ================= DATA & SOURCES =================
    with tabs[5]:
        st.subheader("How the Indian data was built")
        steps = [("1 · Source", f"{SOURCE}, published by the Transport Research Wing, MoRTH, from police records."),
                 ("2 · Extract", "State-wise annexures (III–XXII) and national tables (1.2, 7.1, 8.1, 11.1, XLIII) transcribed into two CSV files."),
                 ("3 · Verify", f"Every state column is summed and checked against the report's printed All-India total "
                                f"({len(REPORT_TOTALS)} checks, below)."),
                 ("4 · Harmonise", "State names matched to the map; zones added; Ladakh shown with J&K as in 2015."),
                 ("5 · Derive", "Deaths per 100 accidents, growth 2013→2015, night share, rural and highway death shares.")]
        cols = st.columns(len(steps))
        for col, (h, b) in zip(cols, steps):
            col.markdown(f'<div class="step"><div class="h">{h}</div><div class="b">{b}</div></div>', unsafe_allow_html=True)
        st.write("")
        left, right = st.columns([3, 2])
        with left:
            v = verify_states(states)
            st.markdown(f"**Verification: {(v['Match'] == '✅').sum()} of {len(v)} columns match the report exactly**")
            st.dataframe(v, hide_index=True, height=420,
                         column_config={"Sum of 36 states": st.column_config.NumberColumn(format="%d"),
                                        "Report total": st.column_config.NumberColumn(format="%d")})
        with right:
            st.markdown("**Notes and limits**")
            st.markdown("""
- India publishes **aggregate tables only**; there is no per-accident file like London's.
- **Andhra Pradesh** was split in June 2014: its 2012–2013 figures include **Telangana**. Growth and per-population rates for both are left blank.
- **Ladakh** became a separate UT in 2019; it is drawn as part of **Jammu & Kashmir**, matching the 2015 data.
- **Weather by state:** six categories could be read reliably; the rest are grouped.
- **Month, cause, city** tables are national (not split by state).
- Police records undercount minor accidents, so *deaths per 100 accidents* is higher than in countries that record every injury accident.
""")
        st.markdown("**Download the state table**")
        show_cols = ["state", "zone", "accidents_2015", "killed_2015", "injured_2015", "fatal_accidents_2015",
                     "deaths_per_100", "acc_per_lakh", "killed_per_lakh", "change_2013_2015", "night_share",
                     "rural_death_share", "nh_death_share"]
        st.dataframe(s[show_cols].round(2), hide_index=True, height=360)
        st.download_button("⬇️ Download selected states (CSV)", s.drop(columns="map_name").to_csv(index=False).encode("utf-8"),
                           file_name="roadvision_india_states.csv", mime="text/csv")
