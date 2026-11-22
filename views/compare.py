"""India vs London section: like-for-like comparisons (shares, timing, rates) for 2015."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scripts.india import (DAY_SLOTS, INDIA_FATAL_SHARE, INDIA_WEATHER_GROUP, LONDON_WEATHER_GROUP, SLOT_COLS, SLOTS,
                           SOURCE, london_slots, load_india, load_states)
from scripts.ui import CYAN, MONTHS, MUTED, ORANGE, PLACE, RED, RISK, hero, insight_cards, kpi, show


def render(df_all):
    hero('ROAD<span>VISION</span> – India vs London',
         "Official Indian data (MoRTH) set against London's STATS19 records · 2015 is the year both datasets share",
         ["London: 74,359 accident records", "India: 36 States/UTs", "Like-for-like: shares, timing, rates"])
    states = load_states()
    lon15 = df_all[df_all["Year"] == 2015]
    lslots = london_slots(lon15)
    lon_fatal = (lon15["Severity"] == "Fatal").mean() * 100

    # ---------- London vs one chosen state ----------
    st.subheader("London vs an Indian state")
    names = states.sort_values("accidents_2015", ascending=False)["state"].tolist()
    pick = st.selectbox("Compare London with", names, index=names.index("Delhi"),
                        help="Delhi is the closest match: a city-state that, like London, is almost entirely urban.")
    r = states.set_index("state").loc[pick]
    lon13 = (df_all["Year"] == 2013).sum()
    c = st.columns(5)
    kpi(c[0], "Accidents 2015", f"{int(r['accidents_2015']):,} vs {len(lon15):,}", f"{pick} vs London")
    kpi(c[1], "Fatal accident share", f"{r['fatal_share']:.1f}% vs {lon_fatal:.1f}%", f"{pick} vs London", "o")
    kpi(c[2], "Urban share of accidents", f"{r['urban_acc'] / r['accidents_2015']:.0%} vs "
        f"{(lon15['Area'] == 'Urban').mean():.0%}", f"{pick} vs London")
    kpi(c[3], "Night (18–06) share", f"{r['night_share']:.0f}% vs "
        f"{lslots[[s for s in SLOTS if s not in DAY_SLOTS]].sum() / lslots.sum() * 100:.0f}%", f"{pick} vs London", "o")
    change = "n/a" if pd.isna(r["change_2013_2015"]) else f"{r['change_2013_2015']:+.1f}%"
    kpi(c[4], "Change 2013→2015", f"{change} vs {(len(lon15) / lon13 - 1) * 100:+.1f}%", f"{pick} vs London")
    st.write("")
    left, right = st.columns(2)
    with left:
        st_slots = r[SLOT_COLS].astype(float).values
        sdf = pd.DataFrame({"Slot": SLOTS * 2, "Share": list(st_slots / st_slots.sum() * 100) + list(lslots / lslots.sum() * 100),
                            "Place": [pick] * 8 + ["London"] * 8})
        fig = px.bar(sdf, x="Slot", y="Share", color="Place", barmode="group",
                     color_discrete_map={pick: ORANGE, "London": CYAN},
                     title=f"Time of day: {pick} vs London (2015, % of accidents)",
                     labels={"Slot": "Time of day (hours)", "Share": "% of the year's accidents"})
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=SLOTS)
        show(fig, legend=True)
    with right:
        ly = df_all.groupby("Year").size()
        idx = pd.DataFrame({"Year": [2013, 2014, 2015] * 2,
                            "Index": [r[f"accidents_{y}"] / r["accidents_2013"] * 100 for y in (2013, 2014, 2015)]
                                     + [ly[y] / ly[2013] * 100 for y in (2013, 2014, 2015)],
                            "Place": [pick] * 3 + ["London"] * 3})
        fig = px.line(idx, x="Year", y="Index", color="Place", markers=True,
                      color_discrete_map={pick: ORANGE, "London": CYAN}, title="Accident growth since 2013 (2013 = 100)")
        fig.update_xaxes(dtick=1)
        fig.add_hline(y=100, line_dash="dot", line_color=MUTED)
        show(fig, legend=True)
        if pick in ("Andhra Pradesh", "Telangana"):
            st.caption("Andhra Pradesh's 2013 figure includes Telangana, so its growth line is not comparable.")
    st.divider()

    india = load_india()
    st.subheader("All India vs London (2015)")
    st.caption(f"India figures: {SOURCE} (official aggregate tables, 2015 unless stated). "
               "London figures: all London records for the same year.")
    lon15 = df_all[df_all["Year"] == 2015]
    nat = india["national"].set_index("year")
    lon_fatal = (lon15["Severity"] == "Fatal").mean() * 100

    c = st.columns(4)
    kpi(c[0], "India accidents (2015)", f"{nat.loc[2015, 'accidents']:,.0f}", "all India, police-recorded")
    kpi(c[1], "India persons killed (2015)", f"{nat.loc[2015, 'killed']:,.0f}",
        f"about {nat.loc[2015, 'killed'] / 365:,.0f} deaths per day", "o")
    kpi(c[2], "Fatal accidents share", f"{INDIA_FATAL_SHARE[2015]}% vs {lon_fatal:.1f}%", "India vs London, 2015", "o")
    kpi(c[3], "London accidents (2015)", f"{len(lon15):,}", f"{(lon15['Severity'] == 'Fatal').sum()} fatal accidents")
    st.write("")

    # --- Shares by time slot and month (like-for-like: percentages, not raw counts)
    tod = india["time_of_day"].set_index("category")["accidents"].reindex(SLOTS)
    lslots = london_slots(lon15)
    slot_df = pd.DataFrame({"Slot": SLOTS * 2, "Share": list(tod / tod.sum() * 100) + list(lslots / lslots.sum() * 100),
                            "Place": ["India"] * 8 + ["London"] * 8})
    mon = india["month"].assign(Month=lambda d: d["category"].astype(int))
    lmon = lon15["Month"].value_counts().reindex(range(1, 13), fill_value=0)
    mon_df = pd.DataFrame({"Month": MONTHS * 2,
                           "Share": list(mon["accidents"] / mon["accidents"].sum() * 100) + list(lmon / lmon.sum() * 100),
                           "Place": ["India"] * 12 + ["London"] * 12})

    peak_i, peak_l = tod.idxmax(), lslots.idxmax()
    night_i = tod[["00-03", "03-06"]].sum() / tod.sum() * 100
    night_l = lslots[["00-03", "03-06"]].sum() / lslots.sum() * 100
    cities = india["city"].assign(Rate=lambda d: d["killed"] / d["accidents"] * 100)
    w = india["weather"].assign(Rate=lambda d: d["killed"] / d["accidents"] * 100)
    cards = [("🕒", f"Same busiest window: {peak_i}h" if peak_i == peak_l else f"Peak: India {peak_i}h, London {peak_l}h",
              f"India {tod[peak_i] / tod.sum():.1%} of accidents, London {lslots[peak_l] / lslots.sum():.1%}."),
             ("☠️", f"Fatal share {INDIA_FATAL_SHARE[2015] / lon_fatal:.0f}x higher in India",
              f"{INDIA_FATAL_SHARE[2015]}% of recorded accidents in India were fatal vs {lon_fatal:.1f}% in London. "
              "Part of this gap comes from different recording (see note below)."),
             ("🏙️", f"City gap: {cities.loc[cities['Rate'].idxmin(), 'category']} vs {cities.loc[cities['Rate'].idxmax(), 'category']}",
              f"{cities['Rate'].min():.1f} vs {cities['Rate'].max():.1f} deaths per 100 accidents, within India."),
             ("🌫️", "Bad weather is deadlier in India",
              f"Fog: {w.set_index('category').loc['Mist/fog', 'Rate']:.0f} deaths per 100 accidents vs "
              f"{w.set_index('category').loc['Fine', 'Rate']:.0f} in fine weather."),
             ("🌙", "Night accidents (00-06)", f"India {night_i:.1f}% of accidents vs London {night_l:.1f}%."),
             ("📈", "2013 to 2015 trend", f"India accidents {(nat.loc[2015, 'accidents'] / nat.loc[2013, 'accidents'] - 1) * 100:+.1f}%, "
              f"deaths {(nat.loc[2015, 'killed'] / nat.loc[2013, 'killed'] - 1) * 100:+.1f}%; London accidents "
              f"{(len(lon15) / (df_all['Year'] == 2013).sum() - 1) * 100:+.1f}%.")]
    for i in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, (icon, head, body) in zip(cols, cards[i:i + 3]):
            col.markdown(f'<div class="ins"><div class="h">{icon} {head}</div><div class="b">{body}</div></div>',
                         unsafe_allow_html=True)
        st.write("")

    left, right = st.columns(2)
    with left:
        fig = px.bar(slot_df, x="Slot", y="Share", color="Place", barmode="group", color_discrete_map=PLACE,
                     title="When accidents happen: share by 3-hour slot (2015)",
                     labels={"Slot": "Time of day (hours)", "Share": "% of the year's accidents"})
        fig.update_traces(hovertemplate="%{x}h: %{y:.1f}%<extra></extra>")
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=SLOTS)
        show(fig, legend=True)
    with right:
        fig = px.line(mon_df, x="Month", y="Share", color="Place", markers=True, color_discrete_map=PLACE,
                      title="Seasonality: share of the year's accidents by month (2015)",
                      category_orders={"Month": MONTHS}, labels={"Share": "% of the year's accidents"})
        fig.add_hline(y=100 / 12, line_dash="dot", line_color=MUTED, annotation_text="even spread",
                      annotation_font_color=MUTED)
        show(fig, legend=True)

    left, right = st.columns(2)
    with left:
        iw = india["weather"].assign(Group=lambda d: d["category"].map(INDIA_WEATHER_GROUP)).groupby("Group")["accidents"].sum()
        lw = lon15["Weather"].map(LONDON_WEATHER_GROUP).dropna().value_counts()
        groups = ["Fine", "Rain", "Fog / mist", "Snow / hail", "Strong wind", "Other"]
        wdf = pd.DataFrame({"Weather": groups * 2,
                            "Share": list(iw.reindex(groups, fill_value=0) / iw.sum() * 100) + list(lw.reindex(groups, fill_value=0) / lw.sum() * 100),
                            "Place": ["India"] * 6 + ["London"] * 6})
        fig = px.bar(wdf, x="Weather", y="Share", color="Place", barmode="group", color_discrete_map=PLACE, log_y=True,
                     title="Weather at the time of the accident (2015, log scale)", labels={"Share": "% of accidents", "Weather": ""})
        fig.update_traces(hovertemplate="%{x}: %{y:.2f}%<extra></extra>")
        show(fig, legend=True)
    with right:
        trend = pd.DataFrame({"Year": [2013, 2014, 2015]})
        trend["India accidents"] = [nat.loc[y, "accidents"] / nat.loc[2013, "accidents"] * 100 for y in trend["Year"]]
        trend["India deaths"] = [nat.loc[y, "killed"] / nat.loc[2013, "killed"] * 100 for y in trend["Year"]]
        ly = df_all.groupby("Year").size()
        trend["London accidents"] = [ly[y] / ly[2013] * 100 for y in trend["Year"]]
        tl = trend.melt("Year", var_name="Series", value_name="Index")
        fig = px.line(tl, x="Year", y="Index", color="Series", markers=True, title="Growth since 2013 (index, 2013 = 100)",
                      color_discrete_map={"India accidents": ORANGE, "India deaths": RED, "London accidents": CYAN})
        fig.update_xaxes(dtick=1)
        fig.add_hline(y=100, line_dash="dot", line_color=MUTED)
        show(fig, legend=True)

    left, right = st.columns(2)
    with left:
        cdf = pd.concat([cities[["category", "accidents", "Rate"]].assign(Place="Indian city (deaths)"),
                         pd.DataFrame({"category": ["London*"], "accidents": [len(lon15)], "Rate": [lon_fatal],
                                       "Place": ["London (fatal accidents)"]})]).sort_values("Rate")
        fig = px.bar(cdf, x="Rate", y="category", orientation="h", color="Place", text=cdf["Rate"].map("{:.1f}".format),
                     color_discrete_map={"Indian city (deaths)": ORANGE, "London (fatal accidents)": CYAN},
                     hover_data={"accidents": ":,", "Place": False},
                     title="Major cities: deaths per 100 accidents (2015)",
                     labels={"Rate": "Per 100 accidents", "category": "", "accidents": "Accidents"})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(legend=dict(orientation="h", y=-0.18, x=0, title=None))
        show(fig, 460, legend=True)
        st.caption("*London's data counts fatal accidents, not persons killed. Every fatal accident has at least one death, "
                   "so London's true deaths-per-100 figure is at least this value.")
    with right:
        wr = w.sort_values("Rate")
        fig = px.bar(wr, x="Rate", y="category", orientation="h", color="Rate", color_continuous_scale=RISK[1:],
                     text=wr["Rate"].map("{:.1f}".format), hover_data={"accidents": ":,", "killed": ":,"},
                     title="India: deaths per 100 accidents by weather (2015)",
                     labels={"Rate": "Deaths per 100 accidents", "category": ""})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_coloraxes(showscale=False)
        show(fig, 440)

    st.markdown("**Selected states, 2015**")
    states = india["state"].assign(**{"Deaths per 100 accidents": lambda d: (d["killed"] / d["accidents"] * 100).round(1)})
    st.dataframe(states.rename(columns={"category": "State / UT", "accidents": "Accidents", "killed": "Persons killed"})
                 .drop(columns="year").sort_values("Accidents", ascending=False), hide_index=True,
                 column_config={"Accidents": st.column_config.NumberColumn(format="%d"),
                                "Persons killed": st.column_config.NumberColumn(format="%d")})
    st.info("**Read the comparison carefully.** London's data lists every police-reported injury accident, one row each. "
            "India publishes only yearly totals from police records, where minor accidents are less likely to be recorded. "
            "So the shares and timing patterns compare well, but the fatal-share gap is partly a recording difference. "
            "Treat it as a pattern, not an exact measure. India figures: Ministry of Road Transport & Highways, "
            "*Road Accidents in India 2015* (Tables 1.2, 7.1, 8.1; Annexures III, IV, XXII, XLIII).")
