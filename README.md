# UHI Mitigation Mapper

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-enabled-green?logo=google)
![License](https://img.shields.io/badge/License-MIT-yellow)

An AI-driven tool that identifies the highest-priority locations for tree planting to reduce Urban Heat Island (UHI) effects — combining satellite thermal data, land cover classification, and US Census vulnerability data into a single ranked action list for city planners.

---

## The Problem

Cities absorb and retain heat due to dark impervious surfaces — asphalt, rooftops, and concrete. This creates Urban Heat Islands where surface temperatures can exceed **50°C** in summer, directly causing heat stroke, especially in low-income and elderly communities with limited access to air conditioning.

| Statistic | Value |
|---|---|
| Albuquerque tree canopy cover | ~9% |
| US city average tree canopy | ~27% |
| Surface temp difference (road vs. park) | up to 25°C |
| Cooling effect of a mature tree | 2–4°C ambient |

---

## How It Works

```
Landsat 9 Satellite        US Census ACS 2022         NLCD 2021
      │                           │                        │
      ▼                           ▼                        ▼
 LST + NDVI               Income, Age, Poverty      Land Cover Classes
      │                           │                        │
      ▼                           ▼                        ▼
 Heat Score              Vulnerability Score        Actionable Zones
  (0 → 1)                   (0 → 1)               (filter non-plantable)
      │                           │                        │
      └───────────────────────────┴────────────────────────┘
                                  │
                                  ▼
                     Priority Score = Heat × 0.4 + Vulnerability × 0.6
                                  │
                                  ▼
                     Ranked GPS locations + Interactive Map
```

---

## Results

### Step 1 — Land Surface Temperature Map
![Heat Map](assets/heat_map.png)
> Red/orange zones exceed 50°C surface temperature. These are the primary Urban Heat Island hotspots driven by asphalt and bare concrete with no vegetation cover.

---

### Step 2 — Community Vulnerability Score
![Vulnerability Map](assets/vulnerability_map.png)
> Darker red census tracts have lower median income, higher median age, and higher poverty rates — the communities most at risk from extreme heat with least ability to adapt.

---

### Step 3 — Tree Planting Priority Locations
![Priority Map](assets/priority_map.png)
> Each dot is a high-priority planting location that scores high on both heat intensity AND community vulnerability. Red = highest priority. Planting trees here is estimated to drop ambient temperature by **2–4°C**.

---

## Sample Output

```
Rank  Latitude     Longitude     Heat   Vuln   Priority  Est.Drop
1     35.08423     -106.65231    0.923  0.871   0.893     3.7°C
2     35.07891     -106.66102    0.911  0.834   0.865     3.6°C
3     35.09102     -106.67834    0.898  0.812   0.847     3.6°C
...
```

> Top 100 locations exported to `data/outputs/priority_locations.csv`

---

## Pipeline

| Script | Input | Output |
|---|---|---|
| `data_fetch.py` | GEE Landsat 9 | Interactive heat map HTML |
| `heat_analysis.py` | LST + NDVI + NLCD | Heat score + hotspot map |
| `vulnerability.py` | Census ACS API + TIGER | Vulnerability score per census tract |
| `priority_index.py` | Heat score + Vulnerability | Priority map + ranked CSV |

---

## Project Structure

```
uhi-mitigation-mapper/
├── assets/
│   ├── heat_map.png
│   ├── vulnerability_map.png
│   └── priority_map.png
├── data/
│   ├── raw/          # Downloaded shapefiles
│   ├── processed/    # Vulnerability scores by census tract
│   └── outputs/      # Final maps and priority CSV
├── notebooks/        # Jupyter notebooks
├── src/
│   ├── data_fetch.py       # GEE data + heat map
│   ├── heat_analysis.py    # LST + NDVI hotspot detection
│   ├── vulnerability.py    # Census vulnerability scoring
│   ├── priority_index.py   # Final priority ranking
│   └── export_images.py    # Export static PNG images
├── requirements.txt
└── .gitignore
```

---

## Setup

```bash
git clone https://github.com/Adnan082/uhi-mitigation-mapper.git
cd uhi-mitigation-mapper
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Authenticate Google Earth Engine:

```python
import ee
ee.Authenticate()
ee.Initialize(project='your-project-id')
```

Run the full pipeline:

```bash
python src/data_fetch.py       # Step 1 — heat map
python src/heat_analysis.py    # Step 2 — hotspot detection
python src/vulnerability.py    # Step 3 — vulnerability scoring
python src/priority_index.py   # Step 4 — final priority map
```

---

## Data Sources

| Data | Source | Resolution |
|------|--------|------------|
| Land Surface Temperature | Landsat 9 (USGS via GEE) | 30m |
| Vegetation Index (NDVI) | Landsat 9 (USGS via GEE) | 30m |
| Land Cover Classification | NLCD 2021 (USGS) | 30m |
| Socioeconomic Data | US Census ACS 2022 | Census Tract |
| Tract Boundaries | US Census TIGER 2022 | Vector |

---

## Tech Stack

| Task | Tool |
|------|------|
| Satellite data access | Google Earth Engine |
| Land cover classification | NLCD 2021 |
| Data processing | Python, `geopandas`, `pandas` |
| Census data | US Census ACS API |
| Visualization | `folium`, `geemap`, `matplotlib` |

---

## Target Region

Southwest United States — **Albuquerque, New Mexico**

Selected because:
- One of the lowest tree canopy coverages of any major US city (~9%)
- Rapidly expanding impervious surfaces from urban sprawl
- Large low-income and elderly population concentrated in South Valley
- Active city tree planting program (Cool ABQ) that can directly use this output
