import joblib
import streamlit as st
import folium
from streamlit_folium import st_folium
from pyproj import Geod
import geopandas as gpd


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


def update_label_joblib_from_file(file_path, state_name, rainfed=-1, crop_type='Other', year=2021):
    if file_path.endswith('.joblib'):
        gdf = joblib.load(file_path)
        gdf = gdf.to_crs(crs='EPSG:4326')
        state = []
        for index in range(len(gdf)):
            state.append(f'{state_name}_{index}')
        gdf['State'] = state
        gdf['Year'] = year
        gdf['Rainfed'] = rainfed
        gdf['Crop_Type'] = crop_type
        gdf.drop(columns=['Width', 'Height', 'location', 'Area_KM2', 'square_id'], inplace=True)
        return gdf
    elif file_path.endswith('.geojson'):
        gdf = gpd.read_file(file_path)
        gdf = gdf.to_crs(crs='EPSG:4326')
        geom = gdf['geometry']
        multipolygons_indices = geom[geom.geom_type == 'MultiPolygon'].index
        polygons_from_multipolygons = []
        for multipolygon in geom[multipolygons_indices]:
            for polygon in multipolygon.geoms:
                polygons_from_multipolygons.append(polygon)
        gdf = gdf.drop(multipolygons_indices)
        index = 0
        for polygon in polygons_from_multipolygons:
            index += 1
            polygon_name = f'Polygon_{index}'
            current_state_name = f'{state_name}_{index}'
            new_row = gpd.GeoDataFrame({'geometry': [polygon], 'Name': [polygon_name], 'State': [current_state_name]})
            gdf = gdf.append(new_row, ignore_index=True)
        gdf['Area_M2'] = gdf['geometry'].apply(calculate_area_in_square_meters)
        gdf['Rainfed'] = rainfed
        gdf['Crop_Type'] = crop_type
        gdf['Year'] = year
    return gdf

def save_label_joblib(gdf, file_path='./data/joblibs/labels.joblib'):
    joblib.dump(gdf, file_path)

def main():
    file_path = './data/joblibs/labels.joblib'
    gdf = joblib.load(file_path)
    gdf = gdf.to_crs(crs='EPSG:4326')
    gdf['Area_M2'] = gdf['geometry'].apply(calculate_area_in_square_meters)
    
    
    # file_path_other = 'data/geojsons/other_gaziera_2021_75Km.geojson'
    file_path_other = './data/joblibs/squares_81_45x45_gaizera.joblib'
    # file_path_other = './data/joblibs/squares_2000_0.5x0.5_gaizera.joblib'
    update_labels_from_geojson = st.button(f'Update Labels from GeoJSON {file_path_other}')
    if update_labels_from_geojson:
        state_name = file_path_other.split('/')[-1]
        state_name = state_name[:-7]
        gdf_other = update_label_joblib_from_file(
            file_path=file_path_other,
            state_name= state_name,
            rainfed=-1,
            crop_type='Other',
            year=2023)
        gdf = gdf.append(gdf_other, ignore_index=True)
        save_label_joblib(gdf, './data/joblibs/labels.joblib')
        st.write('Labels Updated')

    #Create a map with satellite imagery as the background
    m = folium.Map(location=[14.2, 33.2], zoom_start=8)
    folium.TileLayer(
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
    # Select the one column to view
    column_names = ['State', 'Rainfed', 'Year', 'Crop_Type']
    selected_column = st.selectbox('Select column to view', column_names)
    column_value_counts = get_column_value_counts(gdf, selected_column)
    st.table(column_value_counts)
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
