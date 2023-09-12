import geopandas as gpd
import os
import folium
import requests
import jsonlines as jsonl
import glob
from PIL import Image


def make_gif(frame_folder, gif_name):
    frames = [Image.open(image) for image in glob.glob(f"{frame_folder}/*.png")]
    frame_one = frames[0]
    frame_one.save(gif_name, format="GIF", append_images=frames, save_all=True, duration=100, loop=0)
    


# data = gpd.read_file(fp)

def read_shapefile(shapefile_folder, shapefile_name):
    '''
    Read a shapefile and return a geopandas dataframe
    args:
        shapefile_folder: the folder that contains the shapefile
        shapefile_name: the name of the shapefile
    return:
        data: a geopandas dataframe
    '''
    shapefiels_parent_dirs = './shapefiles/'
    shapefile_path = os.path.join(shapefiels_parent_dirs, shapefile_folder, shapefile_name)
    data = gpd.read_file(shapefile_path)
    return data

def read_geojson(geojson_folder, geojson_name):
    '''
    Read a geojson file and return a geopandas dataframe
    args:
        geojson_folder: the folder that contains the geojson file
        geojson_name: the name of the geojson file
    return:
        data: a geopandas dataframe
    '''
    geojson_parent_dirs = './geojsons/'
    geojson_path = os.path.join(geojson_parent_dirs, geojson_folder, geojson_name)
    data = gpd.read_file(geojson_path)
    return data



def get_available_dates_from_sentinelhub(bbox, token, start_date, end_date):
    '''
    Get a list of dates that have available images for a specific bounding box and time period
    from the SentinelHub API
    args:
        bbox: the bounding box of the area of interest
        token: the SentinelHub API token
        start_date: the start date of the time period
        end_date: the end date of the time period
    return:
        dates: a list of dates that have available images
    '''
    dates = get_cached_available_dates_from_sentinelhub(bbox, start_date, end_date)
    if dates is not None:
        print('dates fetched from cache')
        return dates
    headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer '+ token,
    }
    data = f'{{ "collections": [ "sentinel-2-l2a" ], "datetime": "{start_date}T00:00:00Z/{end_date}T23:59:59Z", "bbox": {bbox}, "limit": 100, "distinct": "date" }}'
    response = requests.post('https://services.sentinel-hub.com/api/v1/catalog/search', headers=headers, data=data)
    dates = response.json()['features']
    cache_available_dates_from_sentinelhub(bbox, start_date, end_date, dates)
    print('dates fetched from api')
    return dates



def cache_available_dates_from_sentinelhub(bbox, start_date, end_date, dates):
    '''
    Cache a list of dates that have already been fetched from the SentinelHub API.
    This is to avoid making repeated requests to the API. The cached dates are stored
    in a jsonl file called cached_dates.jsonl in a folder called cache/cached_dates.
    args:
        bbox: the bounding box of the area of interest
        start_date: the start date of the time period
        end_date: the end date of the time period
        dates: a list of dates that have available images
    return:
        None
    '''

    #create cache folder if it doesn't exist
    cache_folder = './cache'
    os.makedirs(cache_folder, exist_ok=True)
    cache_dates_folder = os.path.join(cache_folder, 'cached_dates')
    os.makedirs(cache_dates_folder, exist_ok=True)
    cache_dates_file = os.path.join(cache_dates_folder, 'cached_dates.jsonl')
    
    #create cache_dates_file if it doesn't exist
    if not os.path.exists(cache_dates_file):
        with open(cache_dates_file, 'w') as f:
            f.write('')

    #create dictonary for current entry to be cached
    current_entry = {
        'bbox': bbox,
        'start_date': start_date,
        'end_date': end_date,
        'dates': dates
    }

    #write current entry to jsonl file
    with jsonl.open(cache_dates_file, mode='a') as writer:
        writer.write(current_entry)


def get_cached_available_dates_from_sentinelhub(bbox, start_date, end_date):
    '''
    Get a list of dates that have available images for a specific bounding box and time period
    that have already been fetched from the SentinelHub API. if the dates have not been fetched
    before, return None.
    args:
        bbox: the bounding box of the area of interest
        start_date: the start date of the time period
        end_date: the end date of the time period
    return:
        dates: a list of dates that have available images
    '''

    #cache file path
    cache_dates_file = './cache/cached_dates/cached_dates.jsonl'
    if not os.path.exists(cache_dates_file):
        return None
    

    #create dictonary for current entry to be cached
    current_entry = {
        'bbox': bbox,
        'start_date': start_date,
        'end_date': end_date,
        'dates': []
    }

    #read cached dates file
    with jsonl.open(cache_dates_file, mode='r') as reader:
        for entry in reader:
            if entry['bbox'] == bbox and entry['start_date'] == start_date and entry['end_date'] == end_date:
                return entry['dates']
    

    return None













def get_folium_basemap(basemap_name):
    '''
    Get a folium basemap based on the name of the basemap
    args:
        basemap_name: the name of the basemap
    return:
        basemap: a folium basemap
    '''
    basemaps = {
        'Google Maps': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Maps',
            overlay = True,
            control = True
        ),
        'Google Satellite': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Satellite',
            overlay = True,
            control = True
        ),
        'Google Terrain': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Terrain',
            overlay = True,
            control = True
        ),
        'Google Satellite Hybrid': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Satellite',
            overlay = True,
            control = True
        ),
        'Esri Satellite': folium.TileLayer(
            tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr = 'Esri',
            name = 'Esri Satellite',
            overlay = True,
            control = True
        ),
        'openstreetmap': folium.TileLayer('openstreetmap'),
        'cartodbdark_matter': folium.TileLayer('cartodbdark_matter')
    }
    if basemap_name in basemaps.keys():
        return basemaps[basemap_name]
    else:
        keys = basemaps.keys()
        keys = list(keys)
        print(f'Basemap name must be one of the following: {keys}')
        return None



def get_sentinelhub_api_evalscript(script_name):
    '''
    Get a SentinelHub API evalscript based on the name of the script
    args:
        script_name: the name of the script
    return:
        evalscript: a SentinelHub API evalscript
    '''
    
    # Open and Read The Javascripts that will be passed to the SentinelHub API
    if os.path.exists('./scripts/cab.js'):
        with open('./scripts/cab.js') as f:
            evalscript_cab = f.read()
    else:
        evalscript_cab = None

    if os.path.exists('./scripts/fcover.js'):
        with open('./scripts/fcover.js') as f:
            evalscript_fcover = f.read()
    else:
        evalscript_fcover = None

    if os.path.exists('./scripts/lai.js'):
        with open('./scripts/lai.js') as f:
            evalscript_lai = f.read()
    else:
        evalscript_lai = None

    if os.path.exists('./scripts/truecolor.js'):
        with open('./scripts/truecolor.js') as f:
            evalscript_truecolor = f.read()
    else:
        evalscript_truecolor = None

    if os.path.exists('./scripts/clp.js'):
        with open('./scripts/clp.js') as f:
            evalscript_clp = f.read()
    else:
        evalscript_clp = None

    if os.path.exists('./scripts/all.js'):
        with open('./scripts/all.js') as f:
            evalscript_all = f.read()
    else:
        evalscript_all = None

    if os.path.exists('./scripts/ndvi.js'):
        with open('./scripts/ndvi.js') as f:
            evalscript_ndvi = f.read()
    else:
        evalscript_ndvi = None

    # Dictionry of JavaScript files
    Scripts = {
        'CAB': evalscript_cab,
        'FCOVER': evalscript_fcover,
        'LAI': evalscript_lai,
        'TRUECOLOR': evalscript_truecolor,
        'CLP': evalscript_clp,
        'ALL': evalscript_all,
        'NDVI': evalscript_ndvi
    }
    

    if script_name in Scripts.keys():
        return Scripts[script_name]
    else:
        keys = Scripts.keys()
        keys = list(keys)
        print(f'Script name must be one of the following: {keys}')
        return None

