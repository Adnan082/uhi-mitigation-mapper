import ee
import geemap
import os

ee.Initialize(project='urban-heat-project-495712')

# Albuquerque city boundary as a precise polygon
albuquerque = ee.Geometry.Polygon([[
    [-106.88, 34.95],
    [-106.47, 34.95],
    [-106.47, 35.30],
    [-106.88, 35.30],
    [-106.88, 34.95]
]])

# Date range — peak summer heat
START_DATE = '2023-06-01'
END_DATE   = '2023-09-01'

# Load Landsat 9 Surface Temperature collection
landsat = (
    ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    .filterBounds(albuquerque)
    .filterDate(START_DATE, END_DATE)
    .filter(ee.Filter.lt('CLOUD_COVER', 10))
)

print(f"Images found: {landsat.size().getInfo()}")

# Apply scale factors to each image then create median composite
def apply_scale(image):
    lst = image.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST_Celsius')
    nir = image.select('SR_B5').multiply(0.0000275).add(-0.2)
    red = image.select('SR_B4').multiply(0.0000275).add(-0.2)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    return lst.addBands(ndvi)

# Median composite — averages out cloud shadows and noise across all 12 images
composite = landsat.map(apply_scale).median().clip(albuquerque)
print("Median composite created from all clear images")

# Load NLCD 2021 land cover (pre-classified, no ML needed)
# Classes: 21=Developed Open, 22=Low Intensity, 23=Medium Intensity, 24=High Intensity
# 41/42/43=Forest, 52=Shrub, 71=Grass, 11=Water
nlcd = (
    ee.ImageCollection('USGS/NLCD_RELEASES/2021_REL/NLCD')
    .filter(ee.Filter.eq('system:index', '2021'))
    .first()
    .select('landcover')
    .clip(albuquerque)
)
print("NLCD 2021 land cover loaded")

# Build the map
Map = geemap.Map()
Map.centerObject(albuquerque, 11)

Map.addLayer(
    composite.select('LST_Celsius'),
    {'min': 20, 'max': 60, 'palette': ['blue', 'cyan', 'yellow', 'orange', 'red']},
    'Land Surface Temperature (°C)'
)

Map.addLayer(
    composite.select('NDVI'),
    {'min': -0.1, 'max': 0.6, 'palette': ['brown', 'yellow', 'green']},
    'NDVI (Vegetation)'
)

Map.addLayer(
    nlcd,
    {'min': 11, 'max': 95, 'palette': [
        '466b9f', 'd1def8', 'dec5c5', 'd99282', 'eb0000', 'ab0000',
        'b3ac9f', '68ab5f', '1c5f2c', 'b5c58f', 'af963c', 'ccb879',
        'dfdfc2', 'd1d182', 'a3cc51', '82ba9e', 'dcd939', 'ab6c28',
        'b8d9eb', '6c9fb8'
    ]},
    'NLCD Land Cover 2021',
    shown=False
)

Map.addLayerControl()

output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'outputs', 'albuquerque_heat_map.html')
Map.save(output_path)
print(f"Heat map saved to: {output_path}")
