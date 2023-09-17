import streamlit as st
import os
import pandas as pd
import rasterio
from rasterio import plot
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
import pickle
import geopandas as gpd
from shapely.geometry import Point

def get_available_data_dataframe():
    satellite_images_dir = './data/satellite_images'
    downloaded_dates = os.listdir(satellite_images_dir)
    #remove dates if they are not in YYYY-MM-DD format
    downloaded_dates = [date for date in downloaded_dates if len(date) == 10]
    downloaded_dates = sorted(downloaded_dates)
    downloaded_data_dict = {
        'date': [],
        'location': [],
        'evalscript': [],
        'identifier': [],
        'file_name': []
    }
    for date in downloaded_dates:
        date_dir = os.path.join(satellite_images_dir, date)
        locations = os.listdir(date_dir)
        for location in locations:
            location_dir = os.path.join(date_dir, location)
            evalscripts = os.listdir(location_dir)
            for evalscript in evalscripts:
                evalscript_dir = os.path.join(location_dir, evalscript)
                identifiers = os.listdir(evalscript_dir)
                for identifier in identifiers:
                    identifier_dir = os.path.join(evalscript_dir, identifier)
                    file_names = os.listdir(identifier_dir)
                    for file_name in file_names:
                        if file_name.startswith('response'):
                            downloaded_data_dict['date'].append(date)
                            downloaded_data_dict['location'].append(location)
                            downloaded_data_dict['evalscript'].append(evalscript)
                            downloaded_data_dict['identifier'].append(identifier)
                            downloaded_data_dict['file_name'].append(file_name)
    downloaded_data = pd.DataFrame(downloaded_data_dict)
    return downloaded_data

def get_image_path_from_row(row):
    date = row['date']
    location = row['location']
    evalscript = row['evalscript']
    identifier = row['identifier']
    file_name = row['file_name']
    image_path = f'./data/satellite_images/{date}/{location}/{evalscript}/{identifier}/{file_name}'
    return image_path

def read_image_with_rasterio(image_path):
    img = rasterio.open(image_path)
    return img

def image_info(img):
    st.write(f'Image shape: {img.shape}')
    st.write(f'Image number of bands:{img.count}')
    st.write(f'Image number of columns: {img.width}')
    st.write(f'Image number of rows: {img.height}')
    st.write(f'Image number of pixels: {img.width * img.height}')
    #plotting the image
    if img.count == 3:
        array = img.read((1,2,3))

        #Scale the bands and convert to 8-bit for display and reordering
        array = array / array.max()
        array = (array * 255).astype(np.uint8)
        array = array.transpose(1, 2, 0) # Reorder the bands to 3, 712, 477
        fig, ax = plt.subplots(figsize=(30, 30))
        plt.imshow(array, interpolation='nearest')
        st.pyplot(fig)
    else:
        fig, ax = plt.subplots(figsize=(10,10))
        plot.show(img, ax=ax)
        st.pyplot(fig)


def image_13_bands_as_dataframe(img):
    bands = []
    bands_names = ["B01", "B02", "B03","B04","B05","B06","B07","B08","B8A","B09","B10","B11","B12"]
    add_names = False
    if img.count == len(bands_names):
        add_names = True
    for i in range(1, img.count + 1):
        band = img.read(i)
        bands.append(band)
    bands = np.array(bands)
    bands = bands.reshape(img.count, img.width * img.height)
    bands = bands.T
    if add_names:
        bands = pd.DataFrame(bands, columns=bands_names)
    else:
        bands = pd.DataFrame(bands)
    latitudes = []
    longitudes = []
    for i in range(img.height):
        for j in range(img.width):
            lon, lat = img.xy(i, j)
            latitudes.append(lat)
            longitudes.append(lon)
    bands['latitude'] = latitudes
    bands['longitude'] = longitudes
    return bands

def image_NDVI_as_dataframe(img):
    st.write('Getting NDVI image as dataframe')
    bands = []
    bands_names = ["NDVI"]
    add_names = False
    st.write(f'Bands Names: {bands_names}')
    st.write(f'Image count: {img.count}')
    if img.count == len(bands_names):
        add_names = True
    for i in range(1, img.count + 1):
        band = img.read(i)
        bands.append(band)
    bands = np.array(bands)
    bands = bands.reshape(img.count, img.width * img.height)
    bands = bands.T
    if add_names:
        bands = pd.DataFrame(bands, columns=bands_names)
    else:
        bands = pd.DataFrame(bands)
    latitudes = []
    longitudes = []
    for i in range(img.height):
        for j in range(img.width):
            lon, lat = img.xy(i, j)
            latitudes.append(lat)
            longitudes.append(lon)
    bands['latitude'] = latitudes
    bands['longitude'] = longitudes
    return bands

def image_FCOVER_as_dataframe(img):
    st.write('Getting FCOVER image as dataframe')
    bands = []
    bands_names = ["FCOVER"]
    add_names = False
    st.write(f'Bands Names: {bands_names}')
    st.write(f'Image count: {img.count}')
    if img.count == len(bands_names):
        add_names = True
    for i in range(1, img.count + 1):
        band = img.read(i)
        bands.append(band)
    bands = np.array(bands)
    bands = bands.reshape(img.count, img.width * img.height)
    bands = bands.T
    if add_names:
        bands = pd.DataFrame(bands, columns=bands_names)
    else:
        bands = pd.DataFrame(bands)
    latitudes = []
    longitudes = []
    for i in range(img.height):
        for j in range(img.width):
            lon, lat = img.xy(i, j)
            latitudes.append(lat)
            longitudes.append(lon)
    bands['latitude'] = latitudes
    bands['longitude'] = longitudes
    return bands

def image_CLP_as_dataframe(img):
    bands = []
    bands_names = ["CLP"]
    add_names = False
    if img.count == len(bands_names):
        add_names = True
    for i in range(1, img.count + 1):
        band = img.read(i)
        bands.append(band)
    bands = np.array(bands)
    bands = bands.reshape(img.count, img.width * img.height)
    bands = bands.T
    if add_names:
        bands = pd.DataFrame(bands, columns=bands_names)
    else:
        bands = pd.DataFrame(bands)
    latitudes = []
    longitudes = []
    for i in range(img.height):
        for j in range(img.width):
            lon, lat = img.xy(i, j)
            latitudes.append(lat)
            longitudes.append(lon)
    bands['latitude'] = latitudes
    bands['longitude'] = longitudes
    return bands


def plot_lat_lon_on_folium_map(bands, sample_size=10, value_column=None):
    bands = bands.sample(sample_size)
    latitudes = bands['latitude'].values
    longitudes = bands['longitude'].values
    min_lat = min(latitudes)
    max_lat = max(latitudes)
    min_lon = min(longitudes)
    max_lon = max(longitudes)
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    if value_column is None:
        for i in range(len(latitudes)):
            lat = latitudes[i]
            lon = longitudes[i]
            # folium.Marker([lat, lon]).add_to(m)
            # folium.CircleMarker([lat, lon], radius=5, color='red', fill=True, fill_color='red').add_to(m)
            folium.CircleMarker([lat, lon], radius=5, color='red', fill=True, fill_color='red').add_to(m)
    else:
        values = bands[value_column].values
        min_value = min(values)
        max_value = max(values)
        for i in range(len(latitudes)):
            lat = latitudes[i]
            lon = longitudes[i]
            value = values[i]
            color = (value - min_value) / (max_value - min_value)
            color = int(color * 255)
            color = f'#{color:02x}{color:02x}{color:02x}'
            folium.CircleMarker([lat, lon], radius=5, color=color, fill=True, fill_color=color).add_to(m)
    return m


def get_bands_gdf(row, script='ALL'):
    date = row['date']
    selected_image_path = get_image_path_from_row(row)
    img = read_image_with_rasterio(selected_image_path)
    if script == 'ALL':
        bands_df = image_13_bands_as_dataframe(img)
    elif script == 'NDVI':
        bands_df = image_NDVI_as_dataframe(img)
    elif script == 'CLP':
        bands_df = image_CLP_as_dataframe(img)
    elif script == 'FCOVER':
        bands_df = image_FCOVER_as_dataframe(img)
    else:
        raise Exception('Invalid Script')
    geometry = [Point(xy) for xy in zip(bands_df['longitude'], bands_df['latitude'])]
    bands_gdf = gpd.GeoDataFrame(bands_df, geometry=geometry)
    bands_gdf.crs = {'init': 'epsg:4326'}
    bands_gdf = bands_gdf.to_crs(crs='EPSG:4326')
    bands_gdf.columns = [f'{col}_{date}' for col in bands_gdf.columns]
    return bands_gdf, img



def get_training_data_evalscript(location='gaziera', evalscript='ALL', dates=None, year='2021'):
    data_dir = 'data/training_data/'
    os.makedirs(data_dir, exist_ok=True)
    final_dir = data_dir + location+ '_'+ year + '/'
    os.makedirs(final_dir, exist_ok=True)
    filename = final_dir + 'training_data_' + evalscript + '.pkl'
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            training_data = pickle.load(f)
    else:
        downloaded_data = get_available_data_dataframe()
        downloaded_data = downloaded_data[downloaded_data['evalscript'] == evalscript]
        downloaded_data = downloaded_data[downloaded_data['location'] == location]
        if dates is not None:
            downloaded_data = downloaded_data[downloaded_data['date'].isin(dates)]
        st.write(f'Final Dataframe for {evalscript} in {location}')
        st.write(downloaded_data)
        total_images = len(downloaded_data.index)
        bands_gdf_list = []
        for index, row in downloaded_data.iterrows():
            st.write(f'Processing Image {index + 1} of {total_images}')
            bands_gdf, img = get_bands_gdf(row, script=evalscript)
            bands_gdf_list.append(bands_gdf)
        training_data = pd.concat(bands_gdf_list,axis=1,ignore_index=False)
        with open(filename, 'wb') as f:
            pickle.dump(training_data, f)
    return training_data

def main():
    st.write("Data Reader")
    st.write("Getting Available Data")
    downloaded_data = get_available_data_dataframe()
    all_locations = downloaded_data['location'].values
    wanted_locations_indices = []
    for i in range(len(all_locations)):
        loc = all_locations[i]
        if loc.startswith('gaizera_square_45X45_'):
            wanted_locations_indices.append(i)
    downloaded_data = downloaded_data.iloc[wanted_locations_indices]
    st.write(downloaded_data)
    year ='2023'
    dates = [
        f'{year}-06-01',
        f'{year}-07-16',
        f'{year}-08-15',
        f'{year}-09-09',
    ]
    # st.write("Getting Training Data")
    # training_data = get_training_data_evalscript(location='gaizera_square_45X45_10', evalscript='ALL', dates=dates, year=year)
    # st.write('Training Data')
    # st.write(training_data)
    # st.write("Getting Training Data FCOVER")
    # training_data_FCOVER = get_training_data_evalscript(location='Gaziera', evalscript='FCOVER', dates=dates, year=year)
    # st.write(training_data_FCOVER)

    # Training Data for gaizera_square_45X45_0, gaizera_square_45X45_1, ... gaziera_square_45X45_80
    for i in range(81):
        location = f'gaizera_square_45X45_{i}'
        st.write(f'Getting Training Data for {location}')
        training_data = get_training_data_evalscript(location=location, evalscript='ALL', dates=dates, year=year)
        st.write(f'Getting Training Data for {location} FCOVER')
        training_data_FCOVER = get_training_data_evalscript(location=location, evalscript='FCOVER', dates=dates, year=year)



