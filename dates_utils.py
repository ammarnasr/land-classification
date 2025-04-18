
import os
import requests
import shapely.geometry
import jsonlines as jsonl
from senHub import SenHub, get_sentinelhub_api_config

import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



# SenHub API Setup
def get_sentinelhub_api_token():
    config = get_sentinelhub_api_config()
    token = SenHub(config).token
    return token


def get_bounds_of_polygon(polygon):
    bounds = polygon.bounds
    # bounds = [bounds[1], bounds[0], bounds[3], bounds[2]]
    bounds = [bounds[0], bounds[1], bounds[2], bounds[3]]
    return bounds


def get_available_dates(gdf, year):
    total_bounds = gdf.total_bounds
    total_polygon = shapely.geometry.box(*total_bounds, ccw=True)
    dates = get_available_dates_from_sentinelhub_by_year(total_polygon, year=year)
    return dates

def get_available_dates_from_sentinelhub_by_year(polygon, year='2023'):
    bounds = get_bounds_of_polygon(polygon)
    token = get_sentinelhub_api_token()
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    dates = get_available_dates_from_sentinelhub(bounds, token, start_date, end_date)
    return dates

# def get_available_dates_from_sentinelhub(bbox, token, start_date, end_date):
#     '''
#     Get a list of dates that have available images for a specific bounding box and time period
#     from the SentinelHub API
#     args:
#         bbox: the bounding box of the area of interest
#         token: the SentinelHub API token
#         start_date: the start date of the time period
#         end_date: the end date of the time period
#     return:
#         dates: a list of dates that have available images
#     '''
#     dates = get_cached_available_dates_from_sentinelhub(bbox, start_date, end_date)
#     if dates is not None:
#         print('dates fetched from cache')
#         return dates
#     headers = {
#     'Content-Type': 'application/json',
#     'Authorization': 'Bearer '+ token,
#     }
#     data = f'{{ "collections": [ "sentinel-2-l2a" ], "datetime": "{start_date}T00:00:00Z/{end_date}T23:59:59Z", "bbox": {bbox}, "limit": 100, "distinct": "date" }}'
#     response = requests.post('https://services.sentinel-hub.com/api/v1/catalog/search', headers=headers, data=data)
#     dates = response.json()['features']
#     cache_available_dates_from_sentinelhub(bbox, start_date, end_date, dates)
#     print('dates fetched from api')
#     return dates

def get_available_dates_from_sentinelhub(bbox, token, start_date, end_date):
    """
    Get a list of dates that have available images for a specific bounding box and time period from the SentinelHub API.

    Args:
        bbox (list or tuple): Bounding box [minx, miny, maxx, maxy] of the area of interest.
        token (str): SentinelHub API token.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
        list: A list of dates (or feature items) with available images, or an empty list if an error occurred.
    """
    try:
        # Check if cached data exists first
        dates = get_cached_available_dates_from_sentinelhub(bbox, start_date, end_date)
        if dates is not None:
            logging.info("Dates fetched from cache.")
            return dates

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        payload = {
            "collections": ["sentinel-2-l2a"],
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "bbox": bbox,
            "limit": 100,
            "distinct": "date"
        }

        response = requests.post(
            'https://services.sentinel-hub.com/api/v1/catalog/search',
            headers=headers,
            data=json.dumps(payload)
        )
        # Raise an error if the HTTP request returned an unsuccessful status code
        response.raise_for_status()

        response_data = response.json()
        if 'features' not in response_data:
            logging.error("API response missing 'features' key.")
            return []

        dates = response_data['features']
        cache_available_dates_from_sentinelhub(bbox, start_date, end_date, dates)
        logging.info("Dates fetched from API.")

        return dates

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err} for request with headers: {headers} and payload: {payload}")
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Error during request: {req_err}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    return []


def cache_available_dates_from_sentinelhub(bbox, start_date, end_date, dates):
    '''
    Cache a list of dates that have already been fetched from the SentinelHub API.
    This is to avoid making repeated requests to the API. The cached dates are stored
    in a jsonl file called cached_dates.jsonl in a folder called cache/cached_dates.
    args:
        bbox: the bounding box of the area of interest
        start_date: the start date of the time period
        end_date: the end date of the time period
        dates: a list of dates that have available images
    return:
        None
    '''
    cache_folder = './cache'
    os.makedirs(cache_folder, exist_ok=True)
    cache_dates_folder = os.path.join(cache_folder, 'cached_dates')
    os.makedirs(cache_dates_folder, exist_ok=True)
    cache_dates_file = os.path.join(cache_dates_folder, 'cached_dates.jsonl')
    if not os.path.exists(cache_dates_file):
        with open(cache_dates_file, 'w') as f:
            f.write('')
    current_entry = {
        'bbox': bbox,
        'start_date': start_date,
        'end_date': end_date,
        'dates': dates
    }
    with jsonl.open(cache_dates_file, mode='a') as writer:
        writer.write(current_entry)

def get_cached_available_dates_from_sentinelhub(bbox, start_date, end_date):
    '''
    Get a list of dates that have available images for a specific bounding box and time period
    that have already been fetched from the SentinelHub API. if the dates have not been fetched
    before, return None.
    args:
        bbox: the bounding box of the area of interest
        start_date: the start date of the time period
        end_date: the end date of the time period
    return:
        dates: a list of dates that have available images
    '''
    cache_dates_file = './cache/cached_dates/cached_dates.jsonl'
    if not os.path.exists(cache_dates_file):
        return None
    current_entry = {
        'bbox': bbox,
        'start_date': start_date,
        'end_date': end_date,
        'dates': []
    }
    with jsonl.open(cache_dates_file, mode='r') as reader:
        for entry in reader:
            if entry['bbox'] == bbox and entry['start_date'] == start_date and entry['end_date'] == end_date:
                return entry['dates']
    return None

