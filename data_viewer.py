import joblib
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
from pyproj import Geod
from shapely import wkt


#==================================================================================================
#The contents of the requirements.txt file:
#streamlit
#geopandas
#pandas
#folium
#matplotlib
#pyproj
#shapely
#streamlit-folium





#==================================================================================================



def get_column_value_counts(df, column_name):
    value_counts = df[column_name].value_counts().to_frame()
    value_counts.reset_index(inplace=True)
    value_counts.rename(columns={'index':column_name, column_name:'Count'}, inplace=True)
    value_counts.sort_values(by='Count', ascending=False, inplace=True)
    value_counts.reset_index(inplace=True)
    value_counts.drop(columns='index', inplace=True)
    column_total_areas = []
    for column_value in value_counts[column_name]:
        column_total_area = df[df[column_name] == column_value]['Area_M2'].sum()
        column_total_areas.append(column_total_area)
    value_counts['Total_Area_M2'] = column_total_areas
    return value_counts

def calculate_area_in_square_meters(geometry):
    geod = Geod(ellps="WGS84")
    area = abs(geod.geometry_area_perimeter(geometry)[0])
    return area



def main():
    file_path = './data/joblibs/labels.joblib'
    gdf = joblib.load(file_path)
    gdf = gdf.to_crs(crs='EPSG:4326')
    gdf['Area_M2'] = gdf['geometry'].apply(calculate_area_in_square_meters)
    gdf_small = gdf.sample(1000)

    #Create a map with satellite imagery as the background
    m = folium.Map(location=[14.2, 33.2], zoom_start=8)
    tile = folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Esri Satellite',
        overlay = False,
        control = True
       ).add_to(m)
    gdf.explore(column='State', m=m)
    check_box = st.checkbox('Show Map')
    if check_box:
        st_folium(m, width=1200, height=600)
    st.write(gdf.head())


    #Select the one column to view
    column_names = ['State', 'Rainfed', 'Year', 'Crop_Type']
    selected_column = st.selectbox('Select column to view', column_names)
    column_value_counts = get_column_value_counts(gdf, selected_column)
    st.table(column_value_counts)

    # states_value_counts = get_column_value_counts(gdf, 'State')
    # rainfed_value_counts = get_column_value_counts(gdf, 'Rainfed')
    # year_value_counts = get_column_value_counts(gdf, 'Year')
    # crop_types_value_counts = get_column_value_counts(gdf, 'Crop_Type')
    # st.table(states_value_counts)
    # st.table(rainfed_value_counts)
    # st.table(year_value_counts)
    # st.table(crop_types_value_counts)


    #select the columns to group by
    groupby_columns = ['State', 'Rainfed', 'Year', 'Crop_Type']
    selected_columns = st.multiselect('Select columns to group by', groupby_columns, default=['State', 'Rainfed'])
    #select the columns to aggregate
    aggregate_columns = ['Area_M2']
    #groupby the data
    grouped_data = gdf.groupby(selected_columns)[aggregate_columns].sum()
    grouped_data.reset_index(inplace=True)
    grouped_data.sort_values(by='Area_M2', ascending=False, inplace=True)
    grouped_data.reset_index(inplace=True)
    grouped_data.drop(columns='index', inplace=True)
    st.table(grouped_data)
