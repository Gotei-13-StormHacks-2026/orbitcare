# OrbitCare

> Know before you step outside: satellite data, translated into health advice.

OrbitCare turns free, open Earth observation data into personalized daily health alerts for people with asthma, COPD, and heart conditions. Heat waves and wildfire smoke are dangerous for these groups, but raw satellite data isn't readable by the people who need it most. Pick your neighborhood and condition, and get a simple risk score with plain-language advice.

Built at **StormHacks 2026** (SFU Burnaby).

**Tracks:** MedTech · SFU Satellite ALEASAT (Earth Observation) · Enactus UN SDG (SDG 3, SDG 13) · SSSS Python · IATSU Design · MLH Gemini API · MLH Tiger Data

---

## The Problem

Extreme heat and wildfire smoke send people with respiratory and cardiac conditions to the ER every year. The data to predict risky days already exists in free satellite archives, but almost nobody uses it, and it isn't presented in a way a patient can act on.

## What It Does

1. User picks a neighborhood and their health condition.
2. We pull open satellite and fire data for that area.
3. A risk engine combines heat, smoke/aerosol, and fire proximity into a score tuned to the condition.
4. Gemini turns the score into short, plain-language advice (no diagnoses).
5. Readings are stored over time so users can see trends and plan ahead.

## How It Works

```
Satellite data ──► Pipeline ──► Risk engine ──► Gemini advice ──► Streamlit UI
(Landsat, S5P,     (clip &      (weighted        (plain           (map, score,
 FIRMS)             cache)       score)           language)        trends)
                                     │
                                     ▼
                              Tiger Data (hypertable + continuous aggregates)
```

## Tech Stack

| Layer | Tools |
|---|---|
| Frontend | Streamlit, Folium / pydeck, Plotly |
| Logic | Python 3.11, pandas, numpy (optional FastAPI) |
| Satellite / open data | Microsoft Planetary Computer (STAC), Landsat surface temperature, Sentinel-5P air quality, NASA FIRMS fire detections |
| Raster processing | pystac-client, rioxarray, xarray, rasterio |
| Fallback data | Open-Meteo |
| AI | Gemini API (`google-genai`) |
| Database | Tiger Data (TimescaleDB on Postgres) via psycopg |
| Deployment | Streamlit Community Cloud |

## Data Sources

All data is open, free to download, and readable with free Python libraries.

- **Landsat**: land surface temperature
- **Sentinel-5P**: aerosol / air quality
- **NASA FIRMS**: active fire detections
- **Open-Meteo**: fallback weather and air quality

## Getting Started

```bash
git clone https://github.com/Gotei-13-StormHacks-2026/orbitcare.git
cd orbitcare
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your keys
streamlit run app.py
```

**Environment variables (`.env`)**

```
GEMINI_API_KEY=
FIRMS_MAP_KEY=
TIGER_DATA_URL=
```

Never commit `.env`.

## Project Structure (planned)

```
breathe-easy-sat/
├── app.py              # Streamlit entry point
├── pipeline/           # satellite fetching, clipping, caching
├── risk/               # risk score + condition thresholds
├── ai/                 # Gemini prompts and guardrails
├── db/                 # Tiger Data schema and queries
├── data/cache/         # pre-fetched demo data
└── README.md
```

## Shared Data Contract

Agree on this in the first two hours so everyone can build in parallel.

| Column | Description |
|---|---|
| `location` | neighborhood name |
| `timestamp` | reading time (UTC) |
| `temp` | surface temperature |
| `aerosol` | smoke / air quality value |
| `fire_distance` | distance to nearest active fire |
| `risk_score` | computed by the risk engine |

---

## Team and User Stories

Rough and intentionally vague. Refine as you build.

### Person 1: Satellite Data Pipeline (ALEASAT lead)
- As a user, I want the app to use real satellite data so the risk score reflects what's actually happening outside.
- As a teammate, I want a clean, cached data table so I can build without waiting on slow downloads.
- As a judge, I want to see the satellite data doing real work, not just sitting in the background.
- As a presenter, I want the demo to work even if the internet doesn't.

### Person 2: Risk Engine and AI
- As a user with a health condition, I want a risk score that makes sense for *my* condition, not a generic one.
- As a user, I want advice I can understand quickly without medical jargon.
- As a user, I want to trust that the app won't pretend to be a doctor.
- As a teammate, I want to be able to test the score with fake numbers before real data is ready.

### Person 3: Frontend (Streamlit)
- As a user, I want to pick my neighborhood and condition in a couple of clicks.
- As a user, I want to see my risk on a map and understand it at a glance.
- As a judge, I want to see the raw satellite layer next to the final score.
- As a user on my phone, I want it to still look decent.

### Person 4: Database, Deployment, and Submission
- As a user, I want to see how risk changes over time so I can plan my week.
- As a judge, I want a live link that just opens and works.
- As a teammate, I want the repo and environment set up early so nobody is blocked.
- As the team, we want every track opted in and a clear 3-minute demo video submitted before the deadline.

---

## Responsible Use

Breathe Easy Sat is an informational tool, not medical advice. It does not diagnose or treat any condition. People with health concerns should follow guidance from their doctor and local health authorities.

## Roadmap (post-hackathon)

- Expand beyond Metro Vancouver
- Push notifications for high-risk days
- Partnerships with clinics and community health organizations (SDG 17)
- Forecasting, not just current conditions

## Acknowledgements

Built at StormHacks 2026. Thanks to SFU Satellite (ALEASAT), Enactus SFU, MLH, Google Gemini, and Tiger Data.

## License

MIT
