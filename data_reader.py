import streamlit as st
import os
import pandas as pd
import rasterio
from rasterio import plot
import numpy as np
import matplotlib.pyplot as plt

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

def get_image_path_from_index(df, index):
    row = df.iloc[index]
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
    fig, ax = plt.subplots(figsize=(10,10))
    plot.show(img, ax=ax)
    st.pyplot(fig)

def image_bands_as_dataframe(img):
    bands = []
    for i in range(1, img.count + 1):
        band = img.read(i)
        bands.append(band)
    bands = np.array(bands)
    bands = bands.reshape(img.count, img.width * img.height)
    bands = bands.T
    bands = pd.DataFrame(bands)
    return bands

def main():
    st.write("Data Reader")
    downloaded_data = get_available_data_dataframe()
    st.write(downloaded_data)

    number_of_available_images = len(downloaded_data)
    st.write(f"Number of available images: {number_of_available_images}, Select one to view it")
    selected_image_index = st.number_input("Select image index", 0, number_of_available_images - 1)
    st.write(f"Selected image index: {selected_image_index}")
    selected_image_path = get_image_path_from_index(downloaded_data, selected_image_index)
    st.write(f"Selected image path: {selected_image_path}")
    img = read_image_with_rasterio(selected_image_path)
    image_info(img)
    bands_df = image_bands_as_dataframe(img)
    st.write(f'Bands dataframe shape: {bands_df.shape}')
    st.write(bands_df)




