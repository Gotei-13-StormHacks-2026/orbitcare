"""OrbitCare — satellite data, translated into health advice.

Streamlit frontend: location search, air-quality letter grade, trend charts.
Runs on mock data until the pipeline/risk/db components are ready.
"""

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="OrbitCare", page_icon="🛰️", layout="wide")

# ---------------------------------------------------------------------------
# Global styles
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1100px; }
      header[data-testid="stHeader"] { background: transparent; }

      .oc-logo { display: flex; align-items: center; gap: 10px; }
      .oc-wordmark { font-size: 1.7rem; font-weight: 800; letter-spacing: -0.5px;
        background: linear-gradient(90deg, #1565c0, #26a69a);
        -webkit-background-clip: text; background-clip: text; color: transparent; }
      .oc-tagline { font-size: 0.8rem; color: #78909c; margin-top: -4px; }

      .oc-hero { border-radius: 18px; color: white; padding: 26px 20px; text-align: center;
        box-shadow: 0 6px 18px rgba(0,0,0,.12); }
      .oc-card { border-radius: 14px; border: 1px solid #e3e8ee; background: white;
        padding: 14px 16px; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,.05);
        border-top: 4px solid var(--accent, #90a4ae); height: 100%; }
      .oc-card .label { font-size: .8rem; color: #78909c; text-transform: uppercase;
        letter-spacing: .06em; }
      .oc-card .grade { font-size: 2.6rem; font-weight: 800; line-height: 1.15; }
      .oc-card .detail { font-size: .85rem; color: #546e7a; }
      .oc-card .delta { font-size: .75rem; color: #90a4ae; margin-top: 2px; }

      .oc-window { border-radius: 14px; background: #e8f5e9; border: 1px solid #c8e6c9;
        padding: 14px 18px; font-size: .95rem; color: #1b5e20; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Location search (Open-Meteo geocoding, free, no key) with offline fallback
# ---------------------------------------------------------------------------

FALLBACK_LOCATIONS = {
    "Burnaby": (49.2488, -122.9805),
    "Vancouver Downtown": (49.2827, -123.1207),
    "Surrey": (49.1913, -122.8490),
    "Richmond": (49.1666, -123.1336),
    "North Vancouver": (49.3200, -123.0724),
    "Coquitlam": (49.2838, -122.7932),
}


@st.cache_data(ttl=3600, show_spinner=False)
def geocode(query: str):
    """Return a list of (label, lat, lon) matches for a search query."""
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 5, "language": "en"},
            timeout=5,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        return [
            (
                ", ".join(
                    p for p in [x.get("name"), x.get("admin1"), x.get("country_code")] if p
                ),
                x["latitude"],
                x["longitude"],
            )
            for x in results
        ]
    except requests.RequestException:
        # Offline / demo mode: match against preset neighborhoods
        return [
            (name, lat, lon)
            for name, (lat, lon) in FALLBACK_LOCATIONS.items()
            if query.lower() in name.lower()
        ]


# ---------------------------------------------------------------------------
# Mock readings — follows the shared data contract (replace with pipeline/db)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def fetch_readings(location: str, lat: float, lon: float) -> pd.DataFrame:
    """Hourly readings for the past 7 days. Deterministic per location."""
    rng = np.random.default_rng(abs(hash(location)) % (2**32))
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    ts = pd.date_range(end=now, periods=7 * 24, freq="h")
    hours = ts.hour.to_numpy()

    # Daily heat cycle + location-flavored noise
    temp = 22 + 8 * np.sin((hours - 9) / 24 * 2 * np.pi) + rng.normal(0, 1.5, len(ts))
    # Aerosol index: baseline with an occasional "smoke event"
    aerosol = np.clip(rng.gamma(2.0, 0.4, len(ts)) + rng.choice([0, 2.5], len(ts), p=[0.9, 0.1]), 0, 8)
    fire_distance = np.clip(rng.normal(60, 30, len(ts)), 2, 200)

    df = pd.DataFrame(
        {
            "location": location,
            "timestamp": ts,
            "temp": temp.round(1),
            "aerosol": aerosol.round(2),
            "fire_distance": fire_distance.round(1),
        }
    )
    df["risk_score"] = compute_risk(df)
    return df


def compute_risk(df: pd.DataFrame) -> pd.Series:
    """Placeholder 0-100 risk score; the risk/ component will replace this."""
    heat = np.clip((df["temp"] - 20) / 15, 0, 1)
    smoke = np.clip(df["aerosol"] / 5, 0, 1)
    fire = np.clip(1 - df["fire_distance"] / 100, 0, 1)
    return (100 * (0.35 * heat + 0.45 * smoke + 0.20 * fire)).round(0)


# ---------------------------------------------------------------------------
# Letter grades
# ---------------------------------------------------------------------------

GRADES = [  # (max score, grade, color, headline)
    (20, "A", "#2e7d32", "Great — enjoy the outdoors"),
    (40, "B", "#7cb342", "Good — fine for most people"),
    (60, "C", "#f9a825", "Moderate — sensitive groups take it easy"),
    (80, "D", "#ef6c00", "Poor — limit time outside"),
    (101, "F", "#c62828", "Hazardous — stay indoors if you can"),
]


def grade_for(score: float):
    for cutoff, letter, color, headline in GRADES:
        if score < cutoff:
            return letter, color, headline
    return "F", "#c62828", "Hazardous"


def grade_card(label: str, score: float, detail: str, delta: float):
    letter, color, _ = grade_for(score)
    arrow = "▲ worse" if delta > 2 else ("▼ better" if delta < -2 else "— steady")
    st.markdown(
        f"""
        <div class="oc-card" style="--accent:{color};">
          <div class="label">{label}</div>
          <div class="grade" style="color:{color};">{letter}</div>
          <div class="detail">{detail}</div>
          <div class="delta">{arrow} vs yesterday</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def best_window(df: pd.DataFrame) -> str:
    """Lowest-risk 3-hour window from the most recent daily cycle."""
    day = df.tail(24).reset_index(drop=True)
    rolls = day["risk_score"].rolling(3).mean().dropna()
    i = int(rolls.idxmin())
    start, end = day["timestamp"][i - 2], day["timestamp"][i]
    return f"{start:%-I %p} – {end:%-I %p}"


# NOTE: keep this on one line — indented lines inside st.markdown render as a code block.
LOGO_SVG = (
    '<svg width="46" height="46" viewBox="0 0 46 46" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="23" cy="23" r="12" fill="url(#g)"/>'
    '<path d="M17 23h3l2-4 3 8 2-4h3" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
    '<ellipse cx="23" cy="23" rx="20" ry="8" stroke="#26a69a" stroke-width="1.6" fill="none" transform="rotate(-20 23 23)"/>'
    '<circle cx="40" cy="15" r="2.6" fill="#1565c0"/>'
    '<defs><linearGradient id="g" x1="11" y1="11" x2="35" y2="35">'
    '<stop stop-color="#1565c0"/><stop offset="1" stop-color="#26a69a"/>'
    "</linearGradient></defs></svg>"
)

# ---------------------------------------------------------------------------
# Header: logo left, search top right
# ---------------------------------------------------------------------------

head_l, head_r = st.columns([3, 2], vertical_alignment="center")
with head_l:
    st.markdown(
        f'<div class="oc-logo">{LOGO_SVG}'
        '<div><div class="oc-wordmark">OrbitCare</div>'
        '<div class="oc-tagline">Know before you step outside</div></div></div>',
        unsafe_allow_html=True,
    )
with head_r:
    query = st.text_input(
        "Search for a location",
        placeholder="🔍 Search a city or neighborhood…",
        label_visibility="collapsed",
    )

if query:
    matches = geocode(query)
    if not matches:
        st.warning("No locations found. Try another name.")
        st.stop()
    labels = [m[0] for m in matches]
    if len(labels) > 1:
        with head_r:
            choice = st.selectbox("Pick a match", labels, label_visibility="collapsed")
    else:
        choice = labels[0]
    label, lat, lon = matches[labels.index(choice)]
else:
    label, (lat, lon) = "Burnaby", FALLBACK_LOCATIONS["Burnaby"]

df = fetch_readings(label, lat, lon)
latest = df.iloc[-1]
day_ago = df.iloc[-25]

st.write("")

# ---------------------------------------------------------------------------
# Middle section: hero grade + component cards + best window + map
# ---------------------------------------------------------------------------

overall = latest["risk_score"]
letter, color, headline = grade_for(overall)

left, right = st.columns([1, 2], vertical_alignment="center")
with left:
    st.markdown(
        f"""
        <div class="oc-hero" style="background:linear-gradient(160deg,{color},{color}cc);">
          <div style="font-size:1rem;opacity:.92;">{label} — right now</div>
          <div style="font-size:4.6rem;font-weight:900;line-height:1;">{letter}</div>
          <div style="font-size:1.02rem;margin-top:6px;">{headline}</div>
          <div style="font-size:.85rem;opacity:.85;margin-top:4px;">risk score {overall:.0f} / 100</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with right:
    c1, c2, c3 = st.columns(3)
    with c1:
        heat = lambda row: float(np.clip((row["temp"] - 20) / 15, 0, 1) * 100)
        grade_card("Heat", heat(latest), f"{latest['temp']:.0f} °C surface temp",
                   heat(latest) - heat(day_ago))
    with c2:
        smoke = lambda row: float(np.clip(row["aerosol"] / 5, 0, 1) * 100)
        grade_card("Smoke / air", smoke(latest), f"aerosol index {latest['aerosol']:.1f}",
                   smoke(latest) - smoke(day_ago))
    with c3:
        fire = lambda row: float(np.clip(1 - row["fire_distance"] / 100, 0, 1) * 100)
        grade_card("Wildfire", fire(latest), f"nearest fire ~{latest['fire_distance']:.0f} km",
                   fire(latest) - fire(day_ago))
    st.write("")
    st.markdown(
        f"""<div class="oc-window">🌤️ <b>Best time to be outside today:</b> {best_window(df)}
        — lowest combined heat and smoke risk.</div>""",
        unsafe_allow_html=True,
    )

st.write("")

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

chart_l, chart_r = st.columns([2, 1])

with chart_l:
    tab_risk, tab_temp, tab_smoke = st.tabs(["Risk trend", "Temperature", "Smoke"])
    with tab_risk:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["risk_score"], name="Risk",
                                 line=dict(width=2, color="#1565c0"),
                                 fill="tozeroy", fillcolor="rgba(21,101,192,.08)"))
        for cutoff, g, c, _ in GRADES[:-1]:
            fig.add_hline(y=cutoff, line_dash="dot", line_color=c, opacity=0.45,
                          annotation_text=g, annotation_position="right")
        fig.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=0),
                          yaxis_title="Risk (0–100)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with tab_temp:
        fig_t = go.Figure(go.Scatter(x=df["timestamp"], y=df["temp"],
                                     line=dict(color="#ef6c00", width=2)))
        fig_t.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=0),
                            yaxis_title="Surface temp (°C)")
        st.plotly_chart(fig_t, use_container_width=True)
    with tab_smoke:
        fig_a = go.Figure(go.Scatter(x=df["timestamp"], y=df["aerosol"],
                                     line=dict(color="#6a1b9a", width=2)))
        fig_a.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=0),
                            yaxis_title="Aerosol / smoke index")
        st.plotly_chart(fig_a, use_container_width=True)

with chart_r:
    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=9, height=300)
    with st.expander("How grades work"):
        for cutoff, g, c, head in GRADES:
            lo = {20: 0, 40: 20, 60: 40, 80: 60, 101: 80}[cutoff]
            st.markdown(
                f"<span style='color:{c};font-weight:700;'>{g}</span> "
                f"&nbsp;{lo}–{min(cutoff, 100)} · {head}",
                unsafe_allow_html=True,
            )

st.divider()
st.caption(
    "⚠️ OrbitCare is an informational tool, not medical advice. It does not diagnose or "
    "treat any condition. Follow guidance from your doctor and local health authorities."
)
