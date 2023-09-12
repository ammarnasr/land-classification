import streamlit as st
import pickle
import joblib
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
import os
from tqdm import tqdm
import geopandas as gpd
import pandas as pd

def load_raw_data(location='gaziera', evalscript= 'ALL'):
    data_path = f'data/training_data/{location}/training_data_{evalscript}.pkl'
    with open(data_path, 'rb') as f:
        raw_data = pickle.load(f)
    return raw_data

def saved_processed_data(processed_data, file_path):
    with open(file_path, 'wb') as f:
        pickle.dump(processed_data, f)

def get_labels_gdf(location='gaziera', binary=True):
    file_path = './data/joblibs/labels.joblib'
    gdf = joblib.load(file_path)
    labels_gdf = gdf.to_crs(crs='EPSG:4326')
    if location == 'gaziera':
        location = 'Gaziera'
    labels_gdf = labels_gdf[labels_gdf['State'] == location]
    if binary:
        crop_types = labels_gdf['Crop_Type']
        crop_types_binary = ['Uncultivated' if x == 'Uncultivated' else 'Cultivated' for x in crop_types]
        labels_gdf['Crop_Type_Binary'] = crop_types_binary
    else:
        labels_gdf['Crop_Type_Binary'] = 'Other'
    return labels_gdf

def get_points_list_from_raw_data(raw_data):
    points_list = []
    columns = raw_data.columns
    latitudes = [col for col in columns if 'latitude' in col]
    longitudes = [col for col in columns if 'longitude' in col]
    latitudes = latitudes[0]
    longitudes = longitudes[0]
    latitudes = raw_data[latitudes].values
    longitudes = raw_data[longitudes].values
    for i in range(len(latitudes)):
        point = Point(longitudes[i], latitudes[i])
        points_list.append(point)
    return points_list

def point_in_gdf(point, gdf):
    in_gdf = gdf.geometry.contains(point)
    if in_gdf.sum() > 0:
        return True    
    return False

def get_points_labels(points_list, labels_gdf):
    points_labels = []
    labels_gdf_cultivated = labels_gdf[labels_gdf['Crop_Type_Binary'] == 'Cultivated']
    labels_gdf_uncultivated = labels_gdf[labels_gdf['Crop_Type_Binary'] == 'Uncultivated']
    labels_gdf_other = labels_gdf[labels_gdf['Crop_Type_Binary'] == 'Other']
    with st.spinner('Getting points labels...'):
        for point in tqdm(points_list):
            if point_in_gdf(point, labels_gdf_cultivated):
                points_labels.append(1)
            elif point_in_gdf(point, labels_gdf_uncultivated):
                points_labels.append(0)
            elif point_in_gdf(point, labels_gdf_other):
                points_labels.append(2)
            else:
                points_labels.append(-1)
    return points_labels

def get_processed_data(raw_data , location='gaziera', evalscript='ALL'):
    processed_data_path = f'./data/training_data/{location}/processed_data_{evalscript}.pkl'
    if os.path.exists(processed_data_path):
        with open(processed_data_path, 'rb') as f:
            processed_data = pickle.load(f)
    else:
        binary = True
        if 'other' in location:
            binary = False
        st.write(f'Getting labels for {location} and {evalscript} with binary={binary}')  
        labels_gdf = get_labels_gdf(location=location, binary=binary)
        st.write(f'Labels shape: {labels_gdf.shape}')
        st.write(labels_gdf)
        
        points_list = get_points_list_from_raw_data(raw_data)
        points_labels = get_points_labels(points_list, labels_gdf)
        raw_data['Labels'] = points_labels
        processed_data = raw_data
        saved_processed_data(processed_data, processed_data_path)
    return processed_data

def convert_to_gdf(processed_data):
    geometry_columns = [col for col in processed_data.columns if 'geometry' in col]
    geometry_columns = geometry_columns[0]
    geometry = processed_data[geometry_columns]
    processed_data['geometry'] = geometry
    processed_data_gdf = gpd.GeoDataFrame(processed_data, geometry='geometry')
    return processed_data_gdf

def get_labels_gdf_maps(labels_gdf):
    labels_gdf_cultivated = labels_gdf[labels_gdf['Crop_Type_Binary'] == 'Cultivated']
    labels_gdf_uncultivated = labels_gdf[labels_gdf['Crop_Type_Binary'] == 'Uncultivated']
    labels_gdf_other = labels_gdf[labels_gdf['Crop_Type_Binary'] == 'Other']
    p = labels_gdf_cultivated.geometry.centroid
    x = p.x.mean()
    y = p.y.mean()
    m = folium.Map(location=[y, x], zoom_start=12)
    labels_gdf_cultivated.explore(m=m, color='green')
    labels_gdf_uncultivated.explore(m=m, color='red')
    labels_gdf_other.explore(m=m, color='yellow')
    return m

def read_all_processed_data(data_dir = './data/training_data/gaziera/', evalscript=None):
    files = os.listdir(data_dir)
    files = [file for file in files if 'processed' in file]
    if evalscript is not None:
        files = [file for file in files if evalscript in file]
    processed_data = []
    for file in files:
        with open(data_dir + file, 'rb') as f:
            df = pickle.load(f)
            labels = df['Labels']
            df = df.drop(columns=['Labels'])
            processed_data.append(df)
    processed_data = pd.concat(processed_data, axis=1)
    columns = processed_data.columns
    geometry_columns = [col for col in columns if 'geometry' in col]
    latitudes_cols = [col for col in columns if 'latitude' in col]
    longitudes_cols = [col for col in columns if 'longitude' in col]
    labels_cols = [col for col in columns if 'Labels' in col]
    geom = processed_data[geometry_columns[0]].values
    lat = processed_data[latitudes_cols[0]]
    long = processed_data[longitudes_cols[0]]
    processed_data = processed_data.drop(columns=geometry_columns)
    processed_data = processed_data.drop(columns=latitudes_cols)
    processed_data = processed_data.drop(columns=longitudes_cols)
    processed_data = processed_data.drop(columns=labels_cols)
    processed_data = pd.DataFrame(processed_data)
    processed_data_gdf = gpd.GeoDataFrame(processed_data, geometry=geom)
    processed_data_gdf['latitude'] = lat
    processed_data_gdf['longitude'] = long
    processed_data_gdf['Labels'] = labels
    return processed_data_gdf


def main():
    locations = [ f'gaziera_other_{i}' for i in range(1, 17)]
    locations.append('gaziera')
    evalscripts = ['ALL', 'FCOVER']
    location_gdfs = []
    for location in locations:
        evalscript_gdfs = {}
        for evalscript in evalscripts:
            st.write(f'Getting processed data for {location} and {evalscript}')
            raw_data = load_raw_data(location=location, evalscript=evalscript)
            processed_data = get_processed_data(raw_data, location=location, evalscript=evalscript)
            data_dir = f'./data/training_data/{location}/'
            final_processed_data = read_all_processed_data(data_dir=data_dir, evalscript=evalscript)
            st.write(f'Final processed data shape: {final_processed_data.shape}')
            labels = final_processed_data['Labels']
            value_counts_dict = labels.value_counts().to_dict()
            st.write(labels.value_counts())
            evalscript_gdfs[evalscript] = final_processed_data

        gdf_fcovers = evalscript_gdfs['FCOVER']
        gdf_all = evalscript_gdfs['ALL']
        gdf_fcover = gdf_fcovers.drop(columns=['Labels'])
        gdf_fcover = gdf_fcovers.drop(columns=['latitude'])
        gdf_fcover = gdf_fcovers.drop(columns=['longitude'])
        gdf_fcover = gdf_fcovers.drop(columns=['geometry'])
        focver_columns = gdf_fcover.columns
        for col in focver_columns:
            gdf_all[col] = gdf_fcover[col]
        gdf_all['location'] = location
        location_gdfs.append(gdf_all)

    gdf = pd.concat(location_gdfs)
    st.write(gdf.shape)
    st.write(gdf)
    file_path = './data/joblibs/processed_data.joblib'
    joblib.dump(gdf, file_path)
    
 


    


