"""
ROADVISION - Road Accident Analytics Dashboard
Three sections:
  London          record-level analysis of 74,359 STATS19 accidents (2013-2015)
  India           state-wise analysis of official MoRTH data for all 36 States/UTs (2012-2015)
  India vs London like-for-like comparisons for 2015
Run with:  streamlit run app.py
"""
import streamlit as st

from scripts.data_processing import load_data
from scripts.ui import apply_theme
from views import compare, india, london

st.set_page_config(page_title="RoadVision", page_icon="🚦", layout="wide")
apply_theme()


@st.cache_data(show_spinner="Loading and cleaning 74,000+ London accident records...")
def get_data():
    return load_data()


df_all, report = get_data()

SECTIONS = ["🇬🇧 London", "🇮🇳 India", "🆚 India vs London"]
st.sidebar.markdown("## 🚦 RoadVision")
section = st.segmented_control("Dashboard", SECTIONS, default=SECTIONS[0], key="section",
                               label_visibility="collapsed") or SECTIONS[0]

if section == SECTIONS[0]:
    london.render(df_all, report)
elif section == SECTIONS[1]:
    india.render()
else:
    compare.render(df_all)

st.markdown('<div class="foot">RoadVision · Python, Pandas, NumPy, Plotly, Streamlit · '
            'Data: UK DfT STATS19 (Open Government Licence) · MoRTH Road Accidents in India 2015</div>',
            unsafe_allow_html=True)
