import ee
import geemap
import geopandas as gpd
import pandas as pd
import folium
import requests
import os
import json

ee.Initialize(project='urban-heat-project-495712')

# Albuquerque city boundary
albuquerque = ee.Geometry.Polygon([[
    [-106.88, 34.95],
    [-106.47, 34.95],
    [-106.47, 35.30],
    [-106.88, 35.30],
    [-106.88, 34.95]
]])

# ── 1. Rebuild Heat Score (from heat_analysis.py) ───────────────────────────
print("Building heat score...")

landsat = (
    ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    .filterBounds(albuquerque)
    .filterDate('2023-06-01', '2023-09-01')
    .filter(ee.Filter.lt('CLOUD_COVER', 10))
)

def apply_scale(image):
    lst  = image.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST_Celsius')
    nir  = image.select('SR_B5').multiply(0.0000275).add(-0.2)
    red  = image.select('SR_B4').multiply(0.0000275).add(-0.2)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    return lst.addBands(ndvi)

composite = landsat.map(apply_scale).median().clip(albuquerque)
lst       = composite.select('LST_Celsius')
ndvi      = composite.select('NDVI')

lst_norm   = lst.subtract(20).divide(40).clamp(0, 1)
ndvi_inv   = ndvi.multiply(-1).add(1).clamp(0, 1)
heat_score = lst_norm.multiply(0.6).add(ndvi_inv.multiply(0.4)).rename('Heat_Score')

# Filter actionable zones using NLCD
nlcd = (
    ee.ImageCollection('USGS/NLCD_RELEASES/2021_REL/NLCD')
    .filter(ee.Filter.eq('system:index', '2021'))
    .first()
    .select('landcover')
    .clip(albuquerque)
)
non_actionable     = nlcd.eq(11).Or(nlcd.eq(41)).Or(nlcd.eq(42)).Or(nlcd.eq(43)).Or(nlcd.eq(52)).Or(nlcd.eq(71))
heat_score_actionable = heat_score.updateMask(non_actionable.Not())

print("Heat score ready")

# ── 2. Load Vulnerability Scores ─────────────────────────────────────────────
print("Loading vulnerability scores...")

vuln_csv = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'vulnerability_scores.csv')
vuln_df  = pd.read_csv(vuln_csv)

# Reload tract boundaries
shapefile_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'nm_tracts.zip')
tracts_gdf = gpd.read_file(f"zip://{shapefile_path}")
tracts_gdf = tracts_gdf[tracts_gdf['COUNTYFP'] == '001'].copy()
vuln_df['GEOID']    = vuln_df['GEOID'].astype(str)
tracts_gdf['GEOID'] = tracts_gdf['GEOID'].astype(str)
tracts_gdf = tracts_gdf.merge(vuln_df[['GEOID', 'vulnerability_score']], on='GEOID', how='left')
tracts_gdf = tracts_gdf.to_crs(epsg=4326)
tracts_gdf['vulnerability_score'] = tracts_gdf['vulnerability_score'].fillna(0)

print(f"Vulnerability scores loaded for {len(tracts_gdf)} tracts")

# ── 3. Convert Vulnerability to GEE Image ────────────────────────────────────
print("Sampling heat scores at hotspot locations...")

# Sample heat score pixels across actionable zones
samples = heat_score_actionable.sample(
    region=albuquerque,
    scale=30,
    numPixels=3000,
    seed=42,
    geometries=True
)

sample_list = samples.getInfo()['features']

# Build dataframe from samples
rows = []
for f in sample_list:
    coords = f['geometry']['coordinates']
    score  = f['properties'].get('Heat_Score', None)
    if score is not None:
        rows.append({'longitude': coords[0], 'latitude': coords[1], 'heat_score': score})

samples_df = pd.DataFrame(rows)
print(f"Sampled {len(samples_df)} hotspot pixels")

# ── 4. Spatial Join — Match Each Pixel to Its Census Tract ───────────────────
from shapely.geometry import Point

samples_gdf = gpd.GeoDataFrame(
    samples_df,
    geometry=gpd.points_from_xy(samples_df.longitude, samples_df.latitude),
    crs='EPSG:4326'
)

joined = gpd.sjoin(samples_gdf, tracts_gdf[['GEOID', 'vulnerability_score', 'geometry']], how='left', predicate='within')
joined['vulnerability_score'] = joined['vulnerability_score'].fillna(0)

# ── 5. Calculate Final Priority Index ────────────────────────────────────────
# Priority = 40% heat + 60% vulnerability (equity-weighted)
joined['priority_score'] = (
    joined['heat_score']         * 0.4 +
    joined['vulnerability_score'] * 0.6
)

# Estimate temperature drop: each tree cools ~2-4°C in immediate area
# Higher heat score = more cooling potential
joined['est_temp_drop_C'] = (joined['heat_score'] * 4).round(1)

# Sort by priority
results = joined[['latitude', 'longitude', 'heat_score', 'vulnerability_score', 'priority_score', 'est_temp_drop_C', 'GEOID']]
results = results.sort_values('priority_score', ascending=False).reset_index(drop=True)
results.index += 1

# ── 6. Print Top 20 ──────────────────────────────────────────────────────────
print(f"\n{'='*75}")
print(f"TOP 20 TREE PLANTING PRIORITY LOCATIONS — ALBUQUERQUE, NM")
print(f"{'='*75}")
print(f"{'Rank':<5} {'Latitude':<11} {'Longitude':<12} {'Heat':>6} {'Vuln':>6} {'Priority':>9} {'Est. Drop':>10}")
print(f"{'-'*75}")
for i, row in results.head(20).iterrows():
    print(f"{i:<5} {row.latitude:<11.5f} {row.longitude:<12.5f} {row.heat_score:>6.3f} {row.vulnerability_score:>6.3f} {row.priority_score:>9.3f} {row.est_temp_drop_C:>8.1f}°C")

# ── 7. Save CSV Output ───────────────────────────────────────────────────────
output_csv = os.path.join(os.path.dirname(__file__), '..', 'data', 'outputs', 'priority_locations.csv')
results.head(100).to_csv(output_csv, index_label='Rank')
print(f"\nTop 100 locations saved to: {output_csv}")

# ── 8. Build Final Priority Map ──────────────────────────────────────────────
print("Building final priority map...")

m = folium.Map(location=[35.10, -106.65], zoom_start=11, tiles='CartoDB positron')

# Vulnerability choropleth layer
folium.Choropleth(
    geo_data=tracts_gdf.__geo_interface__,
    data=tracts_gdf,
    columns=['GEOID', 'vulnerability_score'],
    key_on='feature.properties.GEOID',
    fill_color='YlOrRd',
    fill_opacity=0.5,
    line_opacity=0.2,
    legend_name='Vulnerability Score',
    name='Vulnerability by Census Tract'
).add_to(m)

# Top priority locations as colored circles
top_100 = results.head(100)
for i, row in top_100.iterrows():
    # Color by priority: red = highest, orange = medium, yellow = lower
    if row.priority_score >= top_100['priority_score'].quantile(0.75):
        color = 'red'
    elif row.priority_score >= top_100['priority_score'].quantile(0.5):
        color = 'orange'
    else:
        color = 'gold'

    folium.CircleMarker(
        location=[row.latitude, row.longitude],
        radius=6,
        color=color,
        fill=True,
        fill_opacity=0.9,
        popup=folium.Popup(
            f"<b>Rank #{i}</b><br>"
            f"Heat Score: {row.heat_score:.3f}<br>"
            f"Vulnerability: {row.vulnerability_score:.3f}<br>"
            f"Priority Score: {row.priority_score:.3f}<br>"
            f"Est. Temp Drop: {row.est_temp_drop_C}°C",
            max_width=200
        )
    ).add_to(m)

folium.LayerControl().add_to(m)

output_map = os.path.join(os.path.dirname(__file__), '..', 'data', 'outputs', 'priority_map.html')
m.save(output_map)
print(f"Priority map saved to: {output_map}")
print("\nDone. Open priority_map.html to see the final result.")
