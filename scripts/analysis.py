"""
Analysis helpers for RoadVision: auto-generated insights, hotspot detection,
and a statistical association test (chi-square / Cramer's V).
Every number here is computed from the filtered dataset at run time.
"""
import numpy as np
import pandas as pd


def severe_rate_table(df, column, min_count=30):
    """Accidents and serious-or-fatal share per category (small groups dropped)."""
    g = df[df[column] != "Unknown"].groupby(column)["Severe"].agg(Accidents="size", Rate="mean").reset_index()
    g = g[g["Accidents"] >= min_count]
    g["Rate"] = (g["Rate"] * 100).round(2)
    return g.sort_values("Rate")


def cramers_v(df, column, target="Severity"):
    """
    Strength of association between a factor and accident severity (0 = none, 1 = perfect).
    Built from the chi-square statistic of the contingency table, using NumPy only.
    """
    table = pd.crosstab(df[column], df[target]).to_numpy(dtype=float)
    if table.shape[0] < 2 or table.shape[1] < 2:
        return np.nan, np.nan
    n = table.sum()
    expected = table.sum(axis=1, keepdims=True) * table.sum(axis=0, keepdims=True) / n
    chi2 = ((table - expected) ** 2 / expected).sum()
    k = min(table.shape) - 1
    return float(np.sqrt(chi2 / (n * k))), float(chi2)


def factor_strength(df, factors):
    """Cramer's V for each factor against severity, strongest first."""
    rows = []
    for label, col in factors.items():
        sub = df[df[col] != "Unknown"]
        v, chi2 = cramers_v(sub, col)
        rows.append({"Factor": label, "Cramers_V": v, "Chi_square": chi2, "Categories": sub[col].nunique()})
    return pd.DataFrame(rows).dropna().sort_values("Cramers_V")


def hotspots(df, top=10, cell_km=1.0):
    """
    Grid-based hotspot detection: snap each accident to a ~1 km grid cell
    and rank the cells by accident count.
    """
    lat_step = cell_km / 111.0                       # km per degree of latitude
    lon_step = cell_km / (111.0 * np.cos(np.radians(51.5)))  # adjusted for London's latitude
    cells = df.assign(cell_lat=(df["Latitude"] / lat_step).round() * lat_step,
                      cell_lon=(df["Longitude"] / lon_step).round() * lon_step)
    g = cells.groupby(["cell_lat", "cell_lon"]).agg(
        Accidents=("Severe", "size"), Severe=("Severe", "sum"),
        Casualties=("Number_of_Casualties", "sum")).reset_index()
    g["Severe_pct"] = (g["Severe"] / g["Accidents"] * 100).round(1)
    g = g.sort_values("Accidents", ascending=False).head(top).reset_index(drop=True)
    g.insert(0, "Rank", range(1, len(g) + 1))
    return g


def insights(df):
    """Plain-language findings for the current selection. Returns a list of (icon, title, text)."""
    out = []
    n = len(df)
    if n < 50:
        return out
    base = df["Severe"].mean() * 100

    # Peak hour and rush-hour share
    hours = df["Hour"].dropna().astype(int).value_counts()
    if not hours.empty:
        rush = df["Time_Band"].isin(["Morning rush (06-09)", "Evening rush (16-19)"]).mean() * 100
        out.append(("🕔", f"Peak hour: {hours.idxmax():02d}:00",
                    f"{rush:.0f}% of accidents happen in the two rush-hour windows (8 of 24 hours)."))

    # Busiest day
    days = df["Day"].value_counts()
    out.append(("📅", f"Busiest day: {days.idxmax()}",
                f"{days.max():,} accidents, {days.max() / days.min():.2f}x the quietest day ({days.idxmin()})."))

    # Darkness vs daylight severity
    light = df[df["Light"] != "Unknown"]
    dark = light[light["Light"].str.startswith("Dark")]["Severe"].mean() * 100
    day = light[light["Light"] == "Daylight"]["Severe"].mean() * 100
    if pd.notna(dark) and pd.notna(day) and day > 0:
        out.append(("🌙", "Darkness raises severity",
                    f"{dark:.1f}% of accidents in the dark are serious or fatal vs {day:.1f}% in daylight "
                    f"({(dark / day - 1) * 100:+.0f}%)."))

    # Weekend vs weekday severity
    wk = df.groupby("Weekend")["Severe"].mean() * 100
    if len(wk) == 2:
        diff = wk["Weekend"] - wk["Weekday"]
        word = "slightly " if abs(diff) < 1 else ""
        out.append(("🎉", f"Weekend accidents are {word}{'more' if diff > 0 else 'less'} severe",
                    f"Serious-or-fatal share: weekend {wk['Weekend']:.1f}%, weekday {wk['Weekday']:.1f}%."))

    # Highest-risk speed limit (with enough data)
    sp = severe_rate_table(df, "Speed", min_count=200)
    if len(sp) > 1:
        r = sp.iloc[-1]
        out.append(("🚗", f"Riskiest speed limit: {r['Speed']}",
                    f"{r['Rate']:.1f}% serious or fatal vs {base:.1f}% overall ({int(r['Accidents']):,} accidents)."))

    # Year-over-year change
    yearly = df.groupby("Year").size()
    if len(yearly) >= 2 and df.groupby("Year")["Month"].nunique().min() == 12:
        change = (yearly.iloc[-1] / yearly.iloc[0] - 1) * 100
        out.append(("📈", f"{yearly.index[0]} to {yearly.index[-1]}: {change:+.1f}%",
                    f"Accidents went from {yearly.iloc[0]:,} to {yearly.iloc[-1]:,} per year."))
    return out
