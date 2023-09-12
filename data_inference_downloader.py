import streamlit as st
import geopandas as gpd
from streamlit_folium import st_folium
from pyproj import Geod
import shapely.geometry
import folium
import numpy as np
import joblib
import new_app


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



def get_centroid_of_gdf(gdf):
    gdf = gdf.iloc[0]
    centroid = gdf.geometry.centroid
    centroid = [centroid.y, centroid.x]
    return centroid


def get_folium_map(center = [15,32], zoom_start = 12, basemap = 'Google Satellite'):
    m = folium.Map(location=center, zoom_start=zoom_start)
    base_map = get_folium_basemap(basemap)
    base_map.add_to(m)
    return m



def get_dictionary_of_images_from_evalscripts(total_polygon, date, location_name):
    eval_true_color = 'TRUECOLOR'
    eval_CLP = 'CLP'
    eval_FCOVER = 'FCOVER'
    eval_all = 'ALL'
    eval_ndvi = 'NDVI'
    all, all_dir = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_all, location_name)
    tc, tc_dir = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_true_color, location_name)
    clp, clp_dir = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_CLP, location_name)
    fcover, fcover_dir = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_FCOVER, location_name)
    ndvi, ndvi_dir = new_app.get_any_image_from_sentinelhub(total_polygon, date, eval_ndvi, location_name)
    images_dict = {
        'all': all,
        'all_dir': all_dir,
        'tc': tc,
        'tc_dir': tc_dir,
        'clp': clp,
        'clp_dir': clp_dir,
        'fcover': fcover,
        'fcover_dir': fcover_dir,
        'ndvi': ndvi,
        'ndvi_dir': ndvi_dir
    }
    return images_dict


def download_preselected_dates_images_logic(total_polygon, location_name, year='2021'):
    pre_selsected_dates = [
        f'{year}-06-01',
        f'{year}-07-16',
        f'{year}-08-05',
        f'{year}-09-19',
        f'{year}-10-29',
    ]
    st.write(f'Preselected Dates: {pre_selsected_dates}')
    download_images_for_preselected_dates = st.button('Download Images for Preselected Dates', key='download_images_for_preselected_dates')
    if download_images_for_preselected_dates:
        for date in pre_selsected_dates:
            images_dict = get_dictionary_of_images_from_evalscripts(total_polygon, date, location_name)
            tc = images_dict['tc']
            tc_dir = images_dict['tc_dir']
            clp = images_dict['clp']
            fcover = images_dict['fcover']
            st.write(f'CLP Average Value: {np.mean(clp)}')
            st.write(f'FCOVER Average Value: {np.mean(fcover)}')
            st.write(f'True Color Image Downloaded to: {tc_dir}')
            st.image(tc)



def main():
    target_number_of_squares = 255
    max_width = 25
    max_height = 25
    file_name = f'./data/joblibs/squares_{target_number_of_squares}_{max_width}x{max_height}_gaizera.joblib'
    gdf = joblib.load(file_name)
    gdf = gdf.sample(10, random_state=42)
    st.write(gdf)
    centroid = get_centroid_of_gdf(gdf)
    m = get_folium_map(center=centroid, zoom_start=9, basemap='Google Satellite')
    gdf.explore(m=m)
    folium.LayerControl().add_to(m)
    st_folium(m, width=1200, height=600)


    # index = st.number_input('Index', min_value=0, max_value=len(gdf)-1, value=0, step=1)
    # confirm_index = st.button('Confirm Index', key='confirm_index')
    # if confirm_index:
    indexs = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    years = ['2021']
    for index in indexs:
        for year in years:
            current_gdf = gdf.iloc[[index]]
            square_id = current_gdf['square_id'].values[0]
            st.write(f'Square ID: {square_id}, Year: {year}')
            total_bounds = current_gdf.total_bounds
            total_polygon = shapely.geometry.box(*total_bounds, ccw=True)
            location_name = f'gaizera_inference_data_{square_id}'
            pre_selsected_dates = [
                f'{year}-06-01',
                f'{year}-07-16',
                f'{year}-08-05',
                f'{year}-09-19',
                f'{year}-10-29',
            ]
            st.write(f'Preselected Dates: {pre_selsected_dates}')
            for date in pre_selsected_dates:
                images_dict = get_dictionary_of_images_from_evalscripts(total_polygon, date, location_name)
                tc = images_dict['tc']
                tc_dir = images_dict['tc_dir']
                clp = images_dict['clp']
                fcover = images_dict['fcover']
                st.write(f'CLP Average Value: {np.mean(clp)}')
                st.write(f'FCOVER Average Value: {np.mean(fcover)}')
                st.write(f'True Color Image Downloaded to: {tc_dir}')
                st.image(tc)
