import joblib
import streamlit as st
import folium
from streamlit_folium import st_folium
from pyproj import Geod
import shapely.geometry
import geopandas as gpd
import datetime
import new_app
import numpy as np

def load_data():
    file_path = './data/joblibs/labels.joblib'
    gdf = joblib.load(file_path)
    gdf = gdf.to_crs(crs='EPSG:4326')
    return gdf

def filter_gdf_by_state(gdf):
    unique_states = gdf['State'].unique()
    selected_state = st.selectbox('Select State', unique_states, index=2)
    gdf = gdf[gdf['State'] == selected_state]
    return gdf

def get_centroid_of_gdf(gdf):
    gdf = gdf.iloc[0]
    centroid = gdf.geometry.centroid
    centroid = [centroid.y, centroid.x]
    return centroid

def get_folium_basemap(basemap):
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
    }
    return basemaps[basemap]

def get_folium_map(center = [15,32], zoom_start = 12, basemap = 'Google Satellite'):
    m = folium.Map(location=center, zoom_start=zoom_start)
    base_map = get_folium_basemap(basemap)
    base_map.add_to(m)
    return m

def get_bbox_info(gdf):
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
    gdf_bbox = [(gdf_bbox[1], gdf_bbox[0]), (gdf_bbox[3], gdf_bbox[2])]
    st.write(f'Area of Fields: {area/1000000} km2')
    st.write(f'Perimeter of Fields: {perimeter/1000} km')
    st.write(f'Width of Bounding Box: {width/1000} km')
    st.write(f'Height of Bounding Box: {height/1000} km')
    st.write(f'Area of Bounding Box: {(width * height)/1000000} km2')
    st.write(f'Perimeter of Bounding Box: {(2 * (width + height))/1000} km')
    st.write(f'Bounding Box: {gdf_bbox}')
    return width, height, area, perimeter, gdf_bbox 


def get_avilable_dates(gdf, year):
    total_bounds = gdf.total_bounds
    total_polygon = shapely.geometry.box(*total_bounds, ccw=True)
    dates = new_app.get_available_dates_from_sentinelhub(total_polygon, year=year)
    return dates

def dates_close_to_target_date(dates, target_date):
    '''
    Find dates that are close to the target date within a 15 day window moving forward and backward in time
    '''
    target_date = datetime.datetime.strptime(target_date, '%Y-%m-%d')
    dates = [datetime.datetime.strptime(date, '%Y-%m-%d') for date in dates]
    dates = [date for date in dates if date.year == target_date.year]
    dates = [date for date in dates if date.month == target_date.month]
    dates = [date for date in dates if date.day >= target_date.day - 15]
    dates = [date for date in dates if date.day <= target_date.day + 15]
    dates = [date.strftime('%Y-%m-%d') for date in dates]
    return dates

def date_selection_logic(gdf):
    d = st.date_input("Select Imagery Capture Date", datetime.date(2019, 7, 6))
    st.write('The Selected Date is:', d)
    dates = get_avilable_dates(gdf, d.year)
    dates = dates_close_to_target_date(dates, str(d))
    st.write(f'Closest Dates: {dates}')
    date = st.selectbox('Select Date', dates, index=0)
    st.write(f'Selected Date: {date}')
    return date


def main():
    gdf = load_data()
    gdf = filter_gdf_by_state(gdf)
    centroid = get_centroid_of_gdf(gdf)
    m = get_folium_map(center=centroid, zoom_start=10, basemap='Google Satellite')
    gdf.explore(m=m)
    width, height, area, perimeter, state_bbox = get_bbox_info(gdf)
    folium.Rectangle(bounds=state_bbox, color='red').add_to(m)
    st_folium(m, width=1200, height=600)
    date = date_selection_logic(gdf)
    
    location_name = st.text_input('Enter Location Name', 'unknown')
    eval_true_color = 'TRUECOLOR'
    eval_CLP = 'CLP'
    eval_FCOVER = 'FCOVER'
    eval_all = 'ALL'
    total_bounds = gdf.total_bounds
    total_polygon = shapely.geometry.box(*total_bounds, ccw=True)

    download_images = st.button('Download Images')

    if download_images:
        _, _ = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_all, location_name)
        tc, tc_dir = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_true_color, location_name)
        clp, _ = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_CLP, location_name)
        fcover, _ = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_FCOVER, location_name)
        st.write(f'CLP Average Value: {np.mean(clp)}')
        st.write(f'FCOVER Average Value: {np.mean(fcover)}')
        st.write(f'True Color Image Downloaded to: {tc_dir}')
        st.image(tc)
        







