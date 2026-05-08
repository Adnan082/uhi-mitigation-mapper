import ee
import geemap
import os

ee.Initialize(project='urban-heat-project-495712')

# Albuquerque city boundary
albuquerque = ee.Geometry.Polygon([[
    [-106.88, 34.95],
    [-106.47, 34.95],
    [-106.47, 35.30],
    [-106.88, 35.30],
    [-106.88, 34.95]
]])

# ── 1. Build median composite (same as data_fetch.py) ──────────────────────
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

lst  = composite.select('LST_Celsius')
ndvi = composite.select('NDVI')

# ── 2. Calculate Heat Score ─────────────────────────────────────────────────
# Normalize LST to 0-1 range (20°C = 0, 60°C = 1)
lst_norm  = lst.subtract(20).divide(40).clamp(0, 1).rename('LST_norm')

# Invert NDVI so bare/paved areas score high (low vegetation = high heat risk)
ndvi_inv  = ndvi.multiply(-1).add(1).clamp(0, 1).rename('NDVI_inv')

# Heat Score = 60% temperature + 40% lack of vegetation
heat_score = lst_norm.multiply(0.6).add(ndvi_inv.multiply(0.4)).rename('Heat_Score')

# ── 3. Filter Actionable Zones ──────────────────────────────────────────────
# Load NLCD land cover
nlcd = (
    ee.ImageCollection('USGS/NLCD_RELEASES/2021_REL/NLCD')
    .filter(ee.Filter.eq('system:index', '2021'))
    .first()
    .select('landcover')
    .clip(albuquerque)
)

# NLCD classes to REMOVE (not actionable):
# 11 = Open Water
# 41, 42, 43 = Forest (already has trees)
# 52 = Shrub/Scrub (existing vegetation)
# 71 = Grassland (existing vegetation)
non_actionable = nlcd.eq(11).Or(nlcd.eq(41)).Or(nlcd.eq(42)).Or(nlcd.eq(43)).Or(nlcd.eq(52)).Or(nlcd.eq(71))

# Keep only actionable zones (developed/impervious surfaces)
# 21=Developed Open, 22=Low Intensity, 23=Medium Intensity, 24=High Intensity
actionable_mask = non_actionable.Not()
heat_score_actionable = heat_score.updateMask(actionable_mask)

print("Heat score calculated and non-actionable zones filtered")

# ── 4. Find Top Hotspots ────────────────────────────────────────────────────
# Sample the top hotspot pixels across the city
hotspots = heat_score_actionable.sample(
    region=albuquerque,
    scale=30,
    numPixels=5000,
    seed=42,
    geometries=True
)

# Sort by heat score descending and take top 20
top_hotspots = hotspots.sort('Heat_Score', False).limit(20)

# Print top hotspots with coordinates
hotspot_list = top_hotspots.getInfo()
print(f"\nTop 20 Hotspots in Albuquerque:")
print(f"{'Rank':<6} {'Latitude':<12} {'Longitude':<13} {'Heat Score':<12} {'LST (°C)'}")
print("-" * 55)

features = hotspot_list['features']
for i, feature in enumerate(features):
    coords = feature['geometry']['coordinates']
    props  = feature['properties']
    lon, lat = coords[0], coords[1]
    score  = props.get('Heat_Score', 0)
    print(f"{i+1:<6} {lat:<12.5f} {lon:<13.5f} {score:<12.3f}")

# ── 5. Build the Output Map ─────────────────────────────────────────────────
Map = geemap.Map()
Map.centerObject(albuquerque, 11)

Map.addLayer(
    lst.clip(albuquerque),
    {'min': 20, 'max': 60, 'palette': ['blue', 'cyan', 'yellow', 'orange', 'red']},
    'Land Surface Temperature (°C)'
)

Map.addLayer(
    heat_score_actionable,
    {'min': 0, 'max': 1, 'palette': ['green', 'yellow', 'orange', 'red']},
    'Heat Score (Actionable Zones)',
)

Map.addLayer(
    ee.FeatureCollection(top_hotspots),
    {'color': 'purple'},
    'Top 20 Hotspots'
)

Map.addLayerControl()

output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'outputs', 'heat_analysis_map.html')
Map.save(output_path)
print(f"\nMap saved to: {output_path}")
