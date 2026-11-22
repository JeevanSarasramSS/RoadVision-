"""Shared look and feel: colours, page styling, KPI cards and the common chart style."""
import plotly.express as px
import streamlit as st

from scripts.analysis import severe_rate_table

# ---------- Theme ----------
BG, CARD, GRID = "#0B1220", "#131C2E", "#22304A"
BLUE, CYAN, ORANGE, RED, MUTED = "#3B82F6", "#22D3EE", "#F97316", "#EF4444", "#94A3B8"
SEV_COLORS = {"Fatal": RED, "Serious": ORANGE, "Slight": BLUE}
SEQ = [CARD, "#1E3A8A", BLUE, CYAN]            # count scale
RISK = [CARD, "#7C2D12", ORANGE, "#FDBA74"]     # severity-rate scale
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PLACE = {"India": ORANGE, "London": CYAN}


def apply_theme():
    """Inject the dashboard CSS (dark cards, hero banner, KPI and insight cards)."""
    st.markdown(f"""
    <style>
    .block-container {{padding-top: 3.2rem; max-width: 1500px;}}
    .hero {{background: linear-gradient(120deg, #0F1B33 0%, #13284A 55%, #1B2A3F 100%);
            border: 1px solid {GRID}; border-radius: 14px; padding: 20px 26px; margin-bottom: 16px;}}
    .hero .t {{font-size: 2.1rem; font-weight: 800; color: #F1F5F9; letter-spacing: .02em; line-height: 1.15;}}
    .hero .t span {{color: {CYAN};}}
    .hero .s {{color: {MUTED}; margin-top: 6px; font-size: .95rem;}}
    .pill {{display: inline-block; background: #0B1220; border: 1px solid {GRID}; color: #CBD5E1;
            border-radius: 999px; padding: 2px 10px; font-size: .75rem; margin: 8px 6px 0 0;}}
    .kpi {{background: {CARD}; border: 1px solid {GRID}; border-left: 4px solid {CYAN};
           border-radius: 10px; padding: 14px 16px; height: 100%;}}
    .kpi.o {{border-left-color: {ORANGE};}}
    .kpi .l {{color: {MUTED}; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em;}}
    .kpi .v {{color: #F8FAFC; font-size: clamp(1.05rem, 1.5vw, 1.65rem); font-weight: 700; margin-top: 4px;
              white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-variant-numeric: tabular-nums;}}
    .kpi .n {{color: {MUTED}; font-size: .74rem;}}
    .ins {{background: {CARD}; border: 1px solid {GRID}; border-radius: 10px; padding: 14px 16px; height: 100%;}}
    .ins .h {{color: #F1F5F9; font-weight: 700; font-size: .98rem;}}
    .ins .b {{color: #B6C2D3; font-size: .86rem; margin-top: 4px;}}
    .step {{background: {CARD}; border: 1px solid {GRID}; border-top: 3px solid {CYAN}; border-radius: 10px;
            padding: 12px 14px; height: 100%;}}
    .step .h {{color: {CYAN}; font-weight: 700; font-size: .8rem; text-transform: uppercase; letter-spacing: .05em;}}
    .step .b {{color: #CBD5E1; font-size: .85rem; margin-top: 4px;}}
    .stTabs [data-baseweb="tab-list"] {{gap: 6px; border-bottom: 1px solid {GRID};}}
    .stTabs [data-baseweb="tab"] {{background: {CARD}; border-radius: 8px 8px 0 0; padding: 8px 16px;}}
    .stTabs [aria-selected="true"] {{background: #1B2A44;}}
    h3 {{margin-top: .6rem !important;}}
    [data-testid="stButtonGroup"] button {{font-size: 1.02rem; padding: 8px 22px; font-weight: 600;}}
.foot {{color: #64748B; font-size: .78rem; text-align: center; margin-top: 30px;}}
    </style>""", unsafe_allow_html=True)




def insight_cards(cards, per_row=3):
    """Render (icon, title, text) tuples as a grid of insight cards."""
    for i in range(0, len(cards), per_row):
        cols = st.columns(per_row)
        for col, (icon, head, body) in zip(cols, cards[i:i + per_row]):
            col.markdown(f'<div class="ins"><div class="h">{icon} {head}</div><div class="b">{body}</div></div>',
                         unsafe_allow_html=True)
        st.write("")


def hero(title_html, subtitle, pills=()):
    pill_html = "".join(f'<span class="pill">{p}</span>' for p in pills)
    st.markdown(f'<div class="hero"><div class="t">{title_html}</div><div class="s">{subtitle}</div>{pill_html}</div>',
                unsafe_allow_html=True)


def kpi(col, label, value, note="", cls=""):
    col.markdown(f'<div class="kpi {cls}"><div class="l">{label}</div><div class="v">{value}</div>'
                 f'<div class="n">{note}</div></div>', unsafe_allow_html=True)


def show(fig, height=360, legend=False):
    """One shared style for every chart."""
    fig.update_layout(template="plotly_dark", height=height, showlegend=legend,
                      paper_bgcolor=CARD, plot_bgcolor=CARD, font_color="#CBD5E1",
                      margin=dict(l=50, r=20, t=50, b=40), title_font_size=15,
                      legend=dict(bgcolor="rgba(0,0,0,0)"), hoverlabel=dict(bgcolor="#0F172A"))
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    st.plotly_chart(fig, width="stretch")


def rate_bar(data, column, title, color=ORANGE, min_count=30):
    """Horizontal bar: share of accidents that were serious or fatal, per category."""
    g = severe_rate_table(data, column, min_count)
    if g.empty:
        st.info(f"Not enough data for '{title}' in this selection.")
        return
    fig = px.bar(g, x="Rate", y=column, orientation="h", title=title, color_discrete_sequence=[color],
                 hover_data={"Accidents": ":,"}, text=g["Rate"].map("{:.1f}%".format),
                 labels={"Rate": "Serious or fatal (%)", column: ""})
    fig.update_traces(textposition="outside", cliponaxis=False)
    # Dotted line = overall rate, so each bar reads as above or below average.
    fig.add_vline(x=data["Severe"].mean() * 100, line_dash="dot", line_color=MUTED)
    fig.update_layout(title=f"{title}  ·  dotted line = overall {data['Severe'].mean() * 100:.1f}%")
    show(fig)
