import ee
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import requests
import os
import numpy as np
from PIL import Image
from io import BytesIO

ee.Initialize(project='urban-heat-project-495712')

assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
os.makedirs(assets_dir, exist_ok=True)

albuquerque = ee.Geometry.Polygon([[
    [-106.88, 34.95], [-106.47, 34.95],
    [-106.47, 35.30], [-106.88, 35.30],
    [-106.88, 34.95]
]])

# ── 1. Export LST Heat Map as PNG via GEE Thumbnail ─────────────────────────
print("Exporting heat map image...")

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

thumb_url = lst.getThumbURL({
    'min': 20, 'max': 60,
    'palette': ['040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
                '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
                '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
                'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
                'ff0000', 'de0101', 'c21301'],
    'dimensions': 800,
    'region': albuquerque
})

r = requests.get(thumb_url)
img = Image.open(BytesIO(r.content))

fig, ax = plt.subplots(1, 1, figsize=(10, 8))
ax.imshow(img)
ax.set_title('Land Surface Temperature — Albuquerque, NM (Summer 2023)', fontsize=14, fontweight='bold', pad=15)
ax.axis('off')

# Add colorbar
cmap = plt.cm.get_cmap('RdYlBu_r')
norm = mcolors.Normalize(vmin=20, vmax=60)
sm   = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax, orientation='horizontal', fraction=0.03, pad=0.02)
cbar.set_label('Surface Temperature (°C)', fontsize=11)

plt.tight_layout()
plt.savefig(os.path.join(assets_dir, 'heat_map.png'), dpi=150, bbox_inches='tight')
plt.close()
print("heat_map.png saved")

# ── 2. Export Vulnerability Map as PNG ──────────────────────────────────────
print("Exporting vulnerability map image...")

shapefile_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'nm_tracts.zip')
vuln_csv       = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'vulnerability_scores.csv')

tracts_gdf = gpd.read_file(f"zip://{shapefile_path}")
tracts_gdf = tracts_gdf[tracts_gdf['COUNTYFP'] == '001'].copy()
tracts_gdf = tracts_gdf.to_crs(epsg=4326)

vuln_df            = pd.read_csv(vuln_csv)
vuln_df['GEOID']   = vuln_df['GEOID'].astype(str)
tracts_gdf['GEOID'] = tracts_gdf['GEOID'].astype(str)
merged             = tracts_gdf.merge(vuln_df[['GEOID', 'vulnerability_score']], on='GEOID', how='left')
merged['vulnerability_score'] = merged['vulnerability_score'].fillna(0)

fig = plt.figure(figsize=(10, 10))
ax  = fig.add_axes([0.1, 0.15, 0.8, 0.75])  # [left, bottom, width, height]

norm  = mcolors.Normalize(vmin=0, vmax=1)
cmap  = plt.cm.YlOrRd

merged['color'] = merged['vulnerability_score'].apply(lambda x: cmap(norm(x)))
merged.plot(
    color=merged['color'].tolist(),
    linewidth=0.5,
    edgecolor='white',
    ax=ax
)

ax.set_title('Community Vulnerability Score — Albuquerque, NM', fontsize=14, fontweight='bold', pad=12)
ax.set_xlabel('Longitude', fontsize=10)
ax.set_ylabel('Latitude', fontsize=10)
ax.set_xlim([-106.90, -106.45])
ax.set_ylim([34.93, 35.32])

# Colorbar in its own axis — completely separate from the map
cax  = fig.add_axes([0.1, 0.06, 0.8, 0.025])
sm   = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, cax=cax, orientation='horizontal')
cbar.set_label('Vulnerability Score  (0 = Low  →  1 = High)', fontsize=10)

plt.savefig(os.path.join(assets_dir, 'vulnerability_map.png'), dpi=150, bbox_inches='tight')
plt.close()
print("vulnerability_map.png saved")

# ── 3. Export Priority Map as PNG ────────────────────────────────────────────
print("Exporting priority map image...")

priority_csv = os.path.join(os.path.dirname(__file__), '..', 'data', 'outputs', 'priority_locations.csv')
priority_df  = pd.read_csv(priority_csv)

fig, ax = plt.subplots(1, 1, figsize=(10, 8))

merged.plot(
    column='vulnerability_score',
    cmap='YlOrRd',
    linewidth=0.5,
    edgecolor='white',
    alpha=0.5,
    ax=ax
)

# Plot priority dots colored by score
scatter = ax.scatter(
    priority_df['longitude'],
    priority_df['latitude'],
    c=priority_df['priority_score'],
    cmap='cool',
    s=30,
    zorder=5,
    edgecolors='black',
    linewidths=0.3
)

plt.colorbar(scatter, ax=ax, label='Priority Score', orientation='horizontal', fraction=0.03, pad=0.08)

ax.set_title('Tree Planting Priority Locations — Albuquerque, NM', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_xlim([-106.90, -106.45])
ax.set_ylim([34.93, 35.32])

# Legend
high   = mpatches.Patch(color='purple', label='High Priority')
medium = mpatches.Patch(color='cyan',   label='Medium Priority')
ax.legend(handles=[high, medium], loc='upper right', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(assets_dir, 'priority_map.png'), dpi=150, bbox_inches='tight')
plt.close()
print("priority_map.png saved")

print("\nAll images saved to assets/ folder")
