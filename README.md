# UHI Mitigation Mapper

An AI-driven tool that identifies the highest-priority locations for tree planting and urban greening interventions to reduce Urban Heat Island (UHI) effects across cities in the Southwest United States.

## What It Does

1. **Identifies heat hotspots** using Landsat 9 Land Surface Temperature (LST) data
2. **Classifies land cover** to find actionable planting zones (bare lots, sidewalks, parking lots)
3. **Overlays vulnerability data** from Census and health records to prioritize low-income and elderly communities
4. **Outputs a ranked priority map** showing where tree planting has the highest cooling ROI

## Target Region

Southwest United States — starting with **Albuquerque, New Mexico**

## Project Structure

```
uhi-mitigation-mapper/
├── data/
│   ├── raw/          # Downloaded satellite data and shapefiles
│   ├── processed/    # Cleaned and processed datasets
│   └── outputs/      # Final maps, CSVs, and results
├── notebooks/        # Jupyter notebooks for exploration and analysis
├── src/
│   ├── data_fetch.py       # Google Earth Engine data download
│   ├── heat_analysis.py    # LST and NDVI calculations
│   ├── segmentation.py     # Land cover classification
│   ├── vulnerability.py    # Census data processing
│   └── priority_index.py   # Final scoring and ranking
├── requirements.txt
└── .gitignore
```

## Tech Stack

- **Data Access:** Google Earth Engine
- **Data Processing:** Python, `rasterio`, `geopandas`
- **Machine Learning:** scikit-learn, PyTorch
- **Visualization:** Folium, Matplotlib
- **Notebooks:** Jupyter

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
ee.Initialize(project='your-project-name')
```

## Data Sources

| Data | Source | Resolution |
|------|--------|------------|
| Land Surface Temperature | Landsat 9 (USGS) | 30m |
| Vegetation Index (NDVI) | Landsat 9 (USGS) | 30m |
| Land Cover Classification | NLCD 2021 | 30m |
| Building Footprints | Microsoft Open Buildings | Vector |
| Socioeconomic Data | US Census ACS 2022 | Census Tract |
| Health Outcomes | CDC PLACES | Census Tract |
