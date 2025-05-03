import os
import glob
import folium
import numpy as np
import pandas as pd
from PIL import Image
import shapely.geometry
import geopandas as gpd
from pyproj import Geod
from tqdm.auto import tqdm
from datetime import datetime
from shapely.geometry import Point
from dates_utils import get_available_dates
from senHub import SenHub, get_sentinelhub_api_config
# from data_downloader import get_dictionary_of_images_from_evalscripts
# from new_app import mask_downloaded_image, convert_mask_image_to_gdf, get_any_image_from_sentinelhub
from constants import SATELLITE_DIR


# Conversions
def get_total_polygon_from_gdf(gdf):
    total_bounds = gdf.total_bounds
    total_polygon = shapely.geometry.box(*total_bounds, ccw=True)
    return total_polygon

def get_bounds_of_polygon(polygon):
    bounds = polygon.bounds
    # bounds = [bounds[1], bounds[0], bounds[3], bounds[2]]
    bounds = [bounds[0], bounds[1], bounds[2], bounds[3]]
    return bounds

def convert_square_to_polygon(square):
    new_points = []
    for point in square:
        new_point = (point[1], point[0])
        new_points.append(new_point)
    new_points.append(new_points[0])
    polygon = shapely.geometry.Polygon(new_points)
    return polygon

def concat_gdfs(gdfs, axis=0):
    crs = gdfs[0].crs
    gdf = pd.concat(gdfs, axis=axis)
    gdf = gpd.GeoDataFrame(gdf, crs=crs)
    return gdf


def tiff_to_gdf(im, crs):
    '''
    Convert a TIFF image (xarray DataArray) to a GeoDataFrame efficiently,
    creating separate columns for each band.

    Args:
        im (xr.DataArray): The input TIFF image as an xarray DataArray
                          with 'band', 'x', and 'y' coordinates.
        crs: The Coordinate Reference System for the GeoDataFrame.

    Returns:
        gpd.GeoDataFrame: The resulting GeoDataFrame.
    '''
    # Convert the xarray DataArray to a pandas DataFrame
    # This flattens the 'x' and 'y' dimensions and keeps bands as columns
    df = im.to_dataframe(name='value').reset_index()

    # Pivot the DataFrame to have bands as separate columns
    # The 'value' column from to_dataframe contains the pixel values
    df_pivot = df.pivot_table(index=['y', 'x'], columns='band', values='value')
    df_pivot = df_pivot.reset_index() # Reset index to make 'y' and 'x' columns again

    # Rename columns to a more user-friendly format (e.g., band_0, band_1, ...)
    band_names = [f'band_{band}' for band in im.coords['band'].values]
    df_pivot.columns = ['y', 'x'] + band_names

    # Drop rows where all band values are NaN
    df_pivot.dropna(subset=band_names, how='all', inplace=True)

    # Create Point geometries from 'x' and 'y' columns
    geometry = gpd.points_from_xy(df_pivot['x'], df_pivot['y'])

    # Create the GeoDataFrame
    gdf = gpd.GeoDataFrame(df_pivot, geometry=geometry, crs=crs)

    # Drop the separate 'x' and 'y' columns as they are now in the geometry
    gdf = gdf.drop(columns=['x', 'y'])

    return gdf



def gdf_from_geojson(geojson_path, crs):
    gdf = gpd.read_file(filename=geojson_path)
    gdf.crs = crs
    return gdf

def squares_list_to_gdf(squares_list, square_name):
    geom = [convert_square_to_polygon(square) for square in squares_list]
    gdf = gpd.GeoDataFrame(geometry=geom)
    gdf.crs = "EPSG:4326"
    gdf['square_id'] = [f'{square_name}_{i}' for i in range(len(gdf))]
    gdf['Area_M2'] = gdf['geometry'].apply(calculate_area_in_square_meters)
    gdf['Area_KM2'] = gdf['Area_M2']/1000000
    gdf['location'] = square_name
    return gdf

def explode_multipolygons(gdf, year, label):
    """
    Convert rows with MultiPolygon geometries into multiple rows with Polygon geometries.
    
    Parameters:
    -----------
    gdf : geopandas.GeoDataFrame
        Input GeoDataFrame that may contain MultiPolygon geometries
        
    Returns:
    --------
    geopandas.GeoDataFrame
        GeoDataFrame with MultiPolygons exploded into separate Polygon rows.
        A 'Name' column is added to identify the source MultiPolygon and Polygon index.
    """
    gdf = gdf.copy()
    multipolygon_mask = gdf.geometry.geom_type == 'MultiPolygon'
    # If no MultiPolygons found, just add the Name column and return
    if not multipolygon_mask.any():
        gdf['Name'] = [f"multiPolygon_none_polygon_{i}_{year}_{label}" for i in range(len(gdf))]
        return gdf
    # Split into MultiPolygons and non-MultiPolygons
    multipoly_gdf = gdf.loc[multipolygon_mask].copy()
    single_poly_gdf = gdf.loc[~multipolygon_mask].copy()
    # Add Name column to single polygons
    if len(single_poly_gdf) > 0:
        single_poly_gdf['Name'] = [f"multiPolygon_none_polygon_{i}_{year}_{label}" for i in range(len(single_poly_gdf))]
    # Process each MultiPolygon
    exploded_gdfs = []
    for idx, row in multipoly_gdf.iterrows():
        multipolygon = row.geometry
        polygon_rows = []
        # Extract all attributes to preserve them
        attributes = {col: row[col] for col in multipoly_gdf.columns}
        for i, polygon in enumerate(multipolygon.geoms):
            new_row = attributes.copy()
            new_row['geometry'] = polygon
            new_row['Name'] = f"multiPolygon_{idx}_polygon_{i}_{year}_{label}"
            polygon_rows.append(new_row)
        if polygon_rows:
            poly_gdf = gpd.GeoDataFrame(polygon_rows, crs=gdf.crs)
            exploded_gdfs.append(poly_gdf)
    if exploded_gdfs:
        result_gdf = pd.concat([single_poly_gdf] + exploded_gdfs, ignore_index=True)
    else:
        result_gdf = single_poly_gdf
    return result_gdf



# Area
def calculate_area_in_square_meters(geometry):
    geod = Geod(ellps="WGS84")
    area = abs(geod.geometry_area_perimeter(geometry)[0])
    return area



#  I/O operation (read and write)
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

def get_satellite_image_dir(location_name, date, evalscript):
    final_dir = os.path.join(SATELLITE_DIR, location_name, evalscript, date)
    os.makedirs(final_dir, exist_ok=True)
    return final_dir




# SenHub API Setup
def get_sentinelhub_api_token():
    config = get_sentinelhub_api_config()
    token = SenHub(config).token
    return token

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




# Maps
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




# Dates Selection
def get_same_month_dates(target_date, available_dates):
    target_month = datetime.strptime(target_date, "%Y-%m-%d").month
    target_year = datetime.strptime(target_date, "%Y-%m-%d").year
    same_month_dates = [
        date for date in available_dates
        if datetime.strptime(date, "%Y-%m-%d").month == target_month
        and datetime.strptime(date, "%Y-%m-%d").year == target_year
    ]
    return same_month_dates


def get_cloud_coverage_from_sentinelhub(polygon, date, location='unknown'):
    final_dir = get_satellite_image_dir(location, date, 'CLP')
    bbox = get_bounds_of_polygon(polygon)
    evalscript_cloud_coverage = get_sentinelhub_api_evalscript('CLP')
    config = get_sentinelhub_api_config()
    sen_obj = SenHub(config)
    sen_obj.set_dir(final_dir)
    sen_obj.make_bbox(bbox)
    sen_obj.make_request(evalscript_cloud_coverage, date)
    imgs = sen_obj.download_data()
    return imgs[0], final_dir

def get_best_date_in_month_for_gdf(target_date, gdf, location_name=None, find_least_cloud_cover=True):
    year = target_date.split("-")[0]
    available_dates_year = get_available_dates(gdf, year)
    available_dates_month = get_same_month_dates(target_date, available_dates_year)
    if find_least_cloud_cover:
        location_name =  f'cloud_cover_{datetime.now().strftime("%Y%m%d_%H%M%S")}' if location_name is None else location_name
        clp_averages = []
        for date in tqdm(available_dates_month, "Calculating Cloud Cover ..."):
            clp, _ = get_cloud_coverage_from_sentinelhub(get_total_polygon_from_gdf(gdf), date,  location_name)
            clp_averages.append(np.mean(clp))
        min_cloud_index = np.argmin(clp_averages)
        least_cloud_cover_date = available_dates_month[min_cloud_index]
        return least_cloud_cover_date
    else:
        return available_dates_month
    


# Download Tools
def combine_months_geojsons(month_geojson_dict, evalscript=None):
    gdfs = []
    for i, (month, geojson_path) in enumerate(month_geojson_dict.items()):
        gdf = gdf_from_geojson(geojson_path=geojson_path, crs="EPSG:4326")
        for col in ['date', 'evalscript']:
            if col in gdf.columns:
                gdf = gdf.drop(columns=col)
        band_cols = [col for col in gdf.columns if 'band' in col]
        if evalscript == None:
            rename_dict = {col: f"{month}_{col}" for col in band_cols}
        else:
            rename_dict = {col: f"{month}_{evalscript}" for col in band_cols}

        gdf = gdf.rename(columns=rename_dict)
        if i > 0:
            if "location_name" in gdf.columns:
                gdf = gdf.drop(columns="location_name")
            if "geometry" in gdf.columns:
                gdf = gdf.drop(columns="geometry")
        gdfs.append(gdf)
    combined_gdf = pd.concat(gdfs, axis=1)
    return combined_gdf

# def get_geojsons_data_dict_by_month(total_polygon, mask_gdf, dates, location_name, evalscript):
#     month_geojson_dict = {}
#     for date in tqdm(dates, f"Processing dates for {location_name}"): # dates should be selected to align with how the model was trained and what imagery is available with lowest Cloud Cover
#         download_dict = get_dictionary_of_images_from_evalscripts(total_polygon=total_polygon, date=date, location_name=location_name)
#         mask_path = mask_downloaded_image(mask_gdf=mask_gdf, location_name=location_name, date=date, evalscript=evalscript)
#         geojson_path = convert_mask_image_to_gdf(location_name=location_name, date=date, evalscript=evalscript, crs="EPSG:4326")
#         month = get_month_name(date)
#         month_geojson_dict[month] = geojson_path
#         print(f"Saved output for {month} to {geojson_path}")
#     return month_geojson_dict





# Random Utils
def make_gif(frame_folder, gif_name):
    frames = [Image.open(image) for image in glob.glob(f"{frame_folder}/*.png")]
    frame_one = frames[0]
    frame_one.save(gif_name, format="GIF", append_images=frames, save_all=True, duration=100, loop=0)

def get_month_name(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B")

def get_bbox_info(gdf, verbose=False):
    geod = Geod(ellps="WGS84")
    bbox = gdf.total_bounds
    polygon = shapely.geometry.box(*bbox, ccw=True)
    area = abs(geod.geometry_area_perimeter(polygon)[0])
    perimeter = abs(geod.geometry_area_perimeter(polygon)[1])
    width_line_coords = [(bbox[1], bbox[0]), (bbox[1], bbox[2])]
    width_line = shapely.geometry.LineString(width_line_coords)
    width = abs(geod.geometry_area_perimeter(width_line)[1])
    height_line_coords = [(bbox[1], bbox[0]), (bbox[3], bbox[0])]
    height_line = shapely.geometry.LineString(height_line_coords)
    height = abs(geod.geometry_area_perimeter(height_line)[1])
    gdf_bbox = gdf.total_bounds
    gdf_bbox_polygon = shapely.geometry.box(*gdf_bbox, ccw=True)
    gdf_bbox = [(gdf_bbox[1], gdf_bbox[0]), (gdf_bbox[3], gdf_bbox[2])]
    if verbose:
        print(f'Area of State: {area/1000000} km2')
        print(f'Perimeter of State: {perimeter/1000} km')
        print(f'Width of Bounding Box: {width/1000} km')
        print(f'Height of Bounding Box: {height/1000} km')
        print(f'Area of Bounding Box: {(calculate_area_in_square_meters(gdf_bbox_polygon))/1000000} km2')
        print(f'Perimeter of Bounding Box: {(2 * (width + height))/1000} km')
    return width, height, area, perimeter, gdf_bbox 


