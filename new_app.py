import streamlit as st
import new_utils
import numpy as np
import pandas as pd
import geopandas as gpd
import os
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from senHub import SenHub
from sentinelhub import SHConfig
from sentinelhub import MimeType


def get_sentinelhub_api_config():
    config = SHConfig()
    config.instance_id       = 'a2624765-c205-4c43-9ad0-ef0c412e4ecc'   
    config.sh_client_id      = '281a304c-4b24-4834-88a9-67716cb53b5f' 
    config.sh_client_secret  = '->i.[t4J@Qo/-m#O+O@oyiJJG9f?d:GOHYOh[C^K'
    return config


def get_sentinelhub_api_token():
    config = get_sentinelhub_api_config()
    token = SenHub(config).token
    return token

def get_centroid_of_polygon(polygon):
    centroid = polygon.centroid
    centroid = [centroid.y, centroid.x]
    return centroid

def get_area_of_polygon(polygon):
    return polygon.area

def get_bounds_of_polygon(polygon):
    bounds = polygon.bounds
    # bounds = [bounds[1], bounds[0], bounds[3], bounds[2]]
    bounds = [bounds[0], bounds[1], bounds[2], bounds[3]]
    return bounds

def get_folium_map(center = [15,32], zoom_start = 12, basemap = 'Google Satellite'):
    m = folium.Map(location=center, zoom_start=zoom_start)
    base_map = new_utils.get_folium_basemap(basemap)
    base_map.add_to(m)
    return m


def get_available_dates_from_sentinelhub(polygon, year='2023'):
    bounds = get_bounds_of_polygon(polygon)
    token = get_sentinelhub_api_token()
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    dates = new_utils.get_available_dates_from_sentinelhub(bounds, token, start_date, end_date)
    return dates


def get_final_dir(location_name, date, evalscript):
    data_dir = './data/satellite_images'
    os.makedirs(data_dir, exist_ok=True)
    target_date_dir = os.path.join(data_dir, date)
    os.makedirs(target_date_dir, exist_ok=True)
    location_dir = os.path.join(target_date_dir, location_name)
    os.makedirs(location_dir, exist_ok=True)
    evalscript_dir = os.path.join(location_dir, evalscript)
    os.makedirs(evalscript_dir, exist_ok=True)
    final_dir = evalscript_dir
    return final_dir


def get_true_color_image_from_sentinelhub(polygon, date, location='unknown'):
    final_dir = get_final_dir(location, date, 'TRUECOLOR')
    bbox = get_bounds_of_polygon(polygon)
    evalscript_true_color = new_utils.get_sentinelhub_api_evalscript('TRUECOLOR')
    config = get_sentinelhub_api_config()
    sen_obj = SenHub(config, mime_type = MimeType.PNG)
    sen_obj.set_dir(final_dir)
    sen_obj.make_bbox(bbox)
    sen_obj.make_request(evalscript_true_color, date)
    imgs = sen_obj.download_data()
    return imgs[0], final_dir

def get_fcover_image_from_sentinelhub(polygon, date, location='unknown'):
    final_dir = get_final_dir(location, date, 'FCOVER')
    bbox = get_bounds_of_polygon(polygon)
    evalscript_fcover = new_utils.get_sentinelhub_api_evalscript('FCOVER')
    config = get_sentinelhub_api_config()
    sen_obj = SenHub(config)
    sen_obj.set_dir(final_dir)
    sen_obj.make_bbox(bbox)
    sen_obj.make_request(evalscript_fcover, date)
    imgs = sen_obj.download_data()
    return imgs[0], final_dir

def get_cloud_coverage_from_sentinelhub(polygon, date, location='unknown'):
    final_dir = get_final_dir(location, date, 'CLP')
    bbox = get_bounds_of_polygon(polygon)
    evalscript_cloud_coverage = new_utils.get_sentinelhub_api_evalscript('CLP')
    config = get_sentinelhub_api_config()
    sen_obj = SenHub(config)
    sen_obj.set_dir(final_dir)
    sen_obj.make_bbox(bbox)
    sen_obj.make_request(evalscript_cloud_coverage, date)
    imgs = sen_obj.download_data()
    return imgs[0], final_dir

def get_ndvi_image_from_sentinelhub(polygon, date, location='unknown'):
    final_dir = get_final_dir(location, date, 'NDVI')
    bbox = get_bounds_of_polygon(polygon)
    evalscript_ndvi = new_utils.get_sentinelhub_api_evalscript('NDVI')
    config = get_sentinelhub_api_config()
    sen_obj = SenHub(config)
    sen_obj.set_dir(final_dir)
    sen_obj.make_bbox(bbox)
    sen_obj.make_request(evalscript_ndvi, date)
    imgs = sen_obj.download_data()
    return imgs[0], final_dir

def get_all_bands_image_from_sentinelhub(polygon, date, location='unknown'):
    final_dir = get_final_dir(location, date, 'ALL')
    bbox = get_bounds_of_polygon(polygon)
    evalscript_all = new_utils.get_sentinelhub_api_evalscript('ALL')
    config = get_sentinelhub_api_config()
    sen_obj = SenHub(config)
    sen_obj.set_dir(final_dir)
    sen_obj.make_bbox(bbox)
    sen_obj.make_request(evalscript_all, date)
    imgs = sen_obj.download_data()
    return imgs[0], final_dir

def get_any_image_from_sentinelhub(polygon, date, evalscript, location='unknown'):
    if evalscript == 'TRUECOLOR':
        return get_true_color_image_from_sentinelhub(polygon, date, location)
    elif evalscript == 'FCOVER':
        return get_fcover_image_from_sentinelhub(polygon, date, location)
    elif evalscript == 'CLP':
        return get_cloud_coverage_from_sentinelhub(polygon, date, location)
    elif evalscript == 'ALL':
        return get_all_bands_image_from_sentinelhub(polygon, date, location)
    elif evalscript == 'NDVI':
        return get_ndvi_image_from_sentinelhub(polygon, date, location)
    else:
        return None, None
    

def display_true_color_image(image, image_save_path=None):
    factor = 3.5/255
    clip_range = (0, 1)
    fig, ax = plt.subplots(figsize=(15, 15))
    ax.imshow(np.clip(image * factor, *clip_range))
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    
    if image_save_path is not None:
        plt.savefig(image_save_path)

    st.pyplot(fig)

def get_all_image_names_years_dict(image_save_dir):
    image_names = os.listdir(image_save_dir)
    image_names = np.array(image_names)
    image_names_years_dict = {}
    for image_name in image_names:
        year = image_name.split('-')[0][-4:]
        if year not in image_names_years_dict.keys():
            image_names_years_dict[year] = []
        image_names_years_dict[year].append(image_name)
    years = image_names_years_dict.keys()
    years = list(years)
    years.sort()
    return image_names_years_dict, years

def process_years(image_names_years_dict, years):
    last_year = years[-1]
    last_year_images = image_names_years_dict[last_year]
    for year in years:
        if year == last_year:
            continue
        else:
            year_images = image_names_years_dict[year]
            year_images = year_images[:len(last_year_images)]
            image_names_years_dict[year] = year_images
    return image_names_years_dict
















def main():
    khartoum_square = new_utils.read_geojson(
        geojson_folder='khartoum',
        geojson_name='square.geojson'
    )
    ids = khartoum_square.index.values
    khartoum_square['id'] = ids
    st.write(khartoum_square.head(2))

    polygon_index = 1
    location_name = f'khartoum_square_{polygon_index+1}'

    polygon = khartoum_square['geometry'][polygon_index]
    centroid = get_centroid_of_polygon(polygon)
    m = get_folium_map(center=centroid, zoom_start=12)
    folium.GeoJson(khartoum_square).add_to(m)
    st_folium(m)

    dates = get_available_dates_from_sentinelhub(polygon, year='2023')
    # dates = dates[:27]

    target_evalscript = 'CLP'

    download_dates_button = st.button('Download Dates')
    if download_dates_button:
        for target_date in dates:
            with st.empty():
                st.write(target_date)
                image_save_dir = f'./images_{target_evalscript}'
                os.makedirs(image_save_dir, exist_ok=True)
                image_name = f'{location_name}_{target_date}.png'
                image_save_path = os.path.join(image_save_dir, image_name)
                if os.path.exists(image_save_path):
                    continue
                img,final_dir = get_any_image_from_sentinelhub(polygon, target_date, target_evalscript, location=location_name)
                display_true_color_image(img, image_save_path)

    #Read all .png files in the images folder
    image_save_dir = './images_FCOVER'
    image_names_years_dict, years = get_all_image_names_years_dict(image_save_dir)
    image_names_years_dict = process_years(image_names_years_dict, years)
    len_of_images = len(image_names_years_dict[years[0]])

    plot_images_button = st.button('Plot Images')
    if plot_images_button:
        st.write('Plotting Images...')
        my_bar = st.progress(0)
        image_avarage = []
        for i in range(len_of_images):
            images = []
            captions = []
            for year in years:
                image_name = image_names_years_dict[year][i]
                image_path = os.path.join(image_save_dir, image_name)
                image = plt.imread(image_path)
                images.append(image)
                captions.append(image_name[:-4])
            caption = f'{"--- "*(4-len(years))}'.join(captions)
            images = np.array(images)
            images = np.concatenate(images, axis=1)
            #set images to be only the second channel
            images = images[:,:,1]
            image_mean = images.mean()
            image_avarage.append(image_mean)
            fig, ax = plt.subplots(figsize=(15, 15))
            #plot the image in grayscale with a colorbar
            ax.imshow(images, cmap='gray')
            ax.set_xticks([])
            ax.set_yticks([])
            fig.tight_layout()
            #add the colorbar
            cax = fig.add_axes([0.95, 0.25, 0.03, 0.5])
            cax.set_title('Image Mean')
            
            st.pyplot(fig)
            st.write(caption, f'Image Mean: {image_mean}')
            my_bar.progress(i/len_of_images)
            break