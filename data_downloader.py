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
import matplotlib.pyplot as plt
import pickle
import os

def load_data():
    file_path = './data/joblibs/labels.joblib'
    gdf = joblib.load(file_path)
    gdf = gdf.to_crs(crs='EPSG:4326')
    return gdf


def filter_gdf_by_state_logic(gdf):
    unique_states = gdf['State'].unique()
    selected_state = st.selectbox('Select State', unique_states, index=2)
    gdf = gdf[gdf['State'] == selected_state]
    return gdf, selected_state


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
    d = st.date_input("Select Imagery Capture Date", datetime.date(2021, 7, 6))
    st.write('The Selected Date is:', d)
    dates = get_avilable_dates(gdf, d.year)
    dates = dates_close_to_target_date(dates, str(d))
    st.write(f'Closest Dates: {dates}')
    date = st.selectbox('Select Date', dates, index=0)
    st.write(f'Selected Date: {date}')
    return date


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


def download_images_logic(total_polygon, date, location_name, gdf):
    download_images = st.button('Download Images', key='download_images')
    if download_images:
        images_dict = get_dictionary_of_images_from_evalscripts(total_polygon, date, location_name)
        tc = images_dict['tc']
        tc_dir = images_dict['tc_dir']
        clp = images_dict['clp']
        fcover = images_dict['fcover']
        st.write(f'CLP Average Value: {np.mean(clp)}')
        st.write(f'FCOVER Average Value: {np.mean(fcover)}')
        st.write(f'True Color Image Downloaded to: {tc_dir}')
        st.image(tc)


def download_preselected_dates_images_logic(total_polygon, location_name):
    pre_selsected_dates = [
        '2021-06-01',
        '2021-07-16',
        '2021-08-05',
        '2021-09-19',
        '2021-10-29',
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


def plot_cloud_coverage_averages_through_time(polygon, location_name, gdf, year='2021'):
    saved_path = f'./avg_cloud_coverage/{location_name}_avg_cloud_coverage_{year}.pickle'
    dates = get_avilable_dates(gdf, year)
    if os.path.exists(saved_path):
        st.write('Loading Cloud Coverage Averages Through Time')
        with open(saved_path, 'rb') as f:
            clp_averages = pickle.load(f)
    else:
        st.write('Calculating Cloud Coverage Averages Through Time')
        dates = get_avilable_dates(gdf, year)
        num_dates = len(dates)
        clp_averages = []
        my_bar = st.progress(0)
        i= 0
        for date in dates:
            i += 1
            clp, _ = new_app.get_any_image_from_sentinelhub(polygon, date, 'CLP', location_name)
            clp_averages.append(np.mean(clp))
            my_bar.progress(i/num_dates)
        save_dir = './avg_cloud_coverage'
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f'{location_name}_avg_cloud_coverage_{year}.pickle')
        with open(save_path, 'wb') as f:
            pickle.dump(clp_averages, f)
    #Filter dates to be only in the months between April and October
    months = [date[5:7] for date in dates]
    keep_indices = [i for i, month in enumerate(months) if int(month) >= 5 and int(month) <= 10]
    st.write(f'Keeping {len(keep_indices)} dates')
    dates = [dates[i] for i in keep_indices]
    clp_averages = [clp_averages[i] for i in keep_indices]
    #Plot Cloud Coverage Averages Through Time
    fig, ax = plt.subplots(figsize=(30, 8))
    ax.plot(dates, clp_averages)
    ax.set_xticks(dates)
    ax.set_xticklabels(dates, rotation=90)
    ax.set_xlabel('Dates')
    ax.set_ylabel('Cloud Coverage')
    #increase font size in x and y ticks
    ax.tick_params(axis='x', labelsize=25)
    ax.tick_params(axis='y', labelsize=25)
    #Add grid lines
    ax.grid(True)
    ax.set_title('Cloud Coverage Averages Through Time')
    months = [date[5:7] for date in dates]
    months_clp_averages = {}
    for month in set(months):
        months_clp_averages[month] = {
            'dates': [],
            'clp_averages': [],
            'indices': [],
        }
    for i, month in enumerate(months):
        months_clp_averages[month]['dates'].append(dates[i])
        months_clp_averages[month]['clp_averages'].append(clp_averages[i])
        months_clp_averages[month]['indices'].append(i)
    for month in months_clp_averages:
        months_clp_averages[month]['min_clp_average'] = min(months_clp_averages[month]['clp_averages'])
        months_clp_averages[month]['min_clp_average_index'] = months_clp_averages[month]['clp_averages'].index(months_clp_averages[month]['min_clp_average'])
        months_clp_averages[month]['min_clp_average_date'] = months_clp_averages[month]['dates'][months_clp_averages[month]['min_clp_average_index']]
    min_clp_averages = []
    for month in months_clp_averages:
        min_clp_averages.append(months_clp_averages[month]['min_clp_average'])
    min_clp_averages_dates = []
    for month in months_clp_averages:
        min_clp_averages_dates.append(months_clp_averages[month]['min_clp_average_date'])
    ax.scatter(min_clp_averages_dates, min_clp_averages, marker='o', color='red', s=100)
    for i, txt in enumerate(min_clp_averages):
        txt = f'{txt:.2f}@{min_clp_averages_dates[i]}'
        ax.annotate(txt, (min_clp_averages_dates[i], min_clp_averages[i]), fontsize=20)
    st.pyplot(fig)


def cloud_coverage_averages_through_time_logic(total_polygon, location_name, gdf):
    cloud_coverage_averages_through_time = st.button('Cloud Coverage Averages Through Time', key='cloud_coverage_averages_through_time')
    if cloud_coverage_averages_through_time:
        plot_cloud_coverage_averages_through_time(total_polygon, location_name, gdf)

def main():
    gdf = load_data()
    gdf, selected_state = filter_gdf_by_state_logic(gdf)
    centroid = get_centroid_of_gdf(gdf)
    m = get_folium_map(center=centroid, zoom_start=10, basemap='Google Satellite')
    gdf.explore(m=m)
    width, height, area, perimeter, state_bbox = get_bbox_info(gdf)
    folium.Rectangle(bounds=state_bbox, color='red').add_to(m)
    gdf.explore(m=m, color='blue', name='Fields')
    #add layer control
    folium.LayerControl().add_to(m)
    st_folium(m, width=1200, height=600)
    date = date_selection_logic(gdf)
    
    location_name = st.text_input('Enter Location Name', selected_state)
    total_bounds = gdf.total_bounds
    total_polygon = shapely.geometry.box(*total_bounds, ccw=True)

    cloud_coverage_averages_through_time_logic(total_polygon, location_name, gdf)
    images_dict = download_images_logic(total_polygon, date, location_name, gdf)
    download_preselected_dates_images_logic(total_polygon, location_name)

    ###############################################
    #Download Images for Preselected Dates for All States starting with 'gaziera_other'

    # gdf = load_data()
    # all_states = gdf['State'].unique()
    # gaziera_other_states = [state for state in all_states if state.startswith('gaziera_other')]
    # for selected_state in gaziera_other_states:
    #     st.write(f'Selected State: {selected_state}')
    #     gdf = load_data()
    #     gdf = gdf[gdf['State'] == selected_state]
    #     total_bounds = gdf.total_bounds
    #     total_polygon = shapely.geometry.box(*total_bounds, ccw=True)
    #     pre_selsected_dates = [
    #         '2021-06-01',
    #         '2021-07-16',
    #         '2021-08-05',
    #         '2021-09-19',
    #         '2021-10-29',
    #     ]
    #     st.write(f'Preselected Dates: {pre_selsected_dates}')
    #     for date in pre_selsected_dates:
    #         images_dict = get_dictionary_of_images_from_evalscripts(total_polygon, date, selected_state)
    #         tc = images_dict['tc']
    #         tc_dir = images_dict['tc_dir']
    #         clp = images_dict['clp']
    #         fcover = images_dict['fcover']
    #         st.write(f'CLP Average Value: {np.mean(clp)}')
    #         st.write(f'FCOVER Average Value: {np.mean(fcover)}')
    #         st.write(f'True Color Image Downloaded to: {tc_dir}')
    #         st.image(tc)









