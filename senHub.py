from sentinelhub import (
    MimeType,
    CRS,
    BBox,
    SentinelHubRequest,
    DataCollection,
    bbox_to_dimensions,
)
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from sentinelhub import SHConfig
import os
from dotenv import load_dotenv
import streamlit as st
load_dotenv()


def get_sentinelhub_api_config():
    config = SHConfig()
    config.instance_id = st.secrets["instance_id"]
    config.sh_client_id = st.secrets["sh_client_id"]
    config.sh_client_secret = st.secrets["sh_client_secret"]
    return config



class SenHub:
    ''' 
    Class For handling requests to Senhub API.
    '''
    def __init__(self,config,  resolution = 10,
                data_source = DataCollection.SENTINEL2_L1C,
                identifier ='default', mime_type = MimeType.TIFF):
        self.resolution = resolution
        self.config = config
        self.setInputParameters(data_source)
        self.setOutputParameters(identifier, mime_type)
        self.set_token()
        
        self.processing_units_consumed = 0 

    def setInputParameters(self, data_source):
        '''
        Select Source Satellite 
        '''
        self.data_source = data_source
    
    def setOutputParameters(self,identifier, mime_type):
        '''
        Select The return Type of request format and identifier
        '''
        self.identifier = identifier
        self.mime_type = mime_type

    def set_token(self):
        '''
        Fetch Token from sentinelhub api to be used for available dates 
        '''
        client_id = self.config.sh_client_id
        client_secret = self.config.sh_client_secret
        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(token_url='https://services.sentinel-hub.com/oauth/token',client_secret=client_secret)
        self.token =  token['access_token']

    def get_input_data(self, date, search_window_days=10):
        '''
        Wrap input_data to provide to the sentinelhub API, searching for the least cloudy image
        within a specified window, ensuring the window stays within the target month.
        '''
        from datetime import timedelta, date as date_obj
        import datetime

        if isinstance(date, str):
            target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = date

        year = target_date.year
        month = target_date.month

        first_day_of_month = date_obj(year, month, 1)
        if month == 12:
            last_day_of_month = date_obj(year, month, 31)
        else:
            last_day_of_month = date_obj(year, month + 1, 1) - timedelta(days=1)

        start_offset = timedelta(days=search_window_days)
        end_offset = timedelta(days=search_window_days)

        potential_start_date = target_date - start_offset
        potential_end_date = target_date + end_offset

        start_date = max(potential_start_date, first_day_of_month)
        end_date = min(potential_end_date, last_day_of_month)


        return SentinelHubRequest.input_data(
            data_collection=self.data_source,
            time_interval=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
            mosaicking_order='leastCC'
        )

    def get_output_data(self):
        '''
        Wrap output_data to provide to the sentinelhub API
        '''
        return SentinelHubRequest.output_response(self.identifier, self.mime_type)
        
    def set_dir(self, dir_path):
        '''
        Set The Target Download Directory Path
        '''
        self.dir_path = dir_path

    def make_bbox(self, bbox):
        '''
        Wrap bbox to provide to the sentinelhub API.
        '''
        self.bbox = BBox(bbox=bbox, crs=CRS.WGS84)
        self.bbox_size = bbox_to_dimensions(self.bbox, resolution=self.resolution)
                
    def make_request(self, metric, date, search_window_days=10):
        '''
        Setup the Sentinel Hub Request, finding the least cloudy scene within a window.
        '''
        input_data = self.get_input_data(date, search_window_days)
        output_data = self.get_output_data()
        self.request = SentinelHubRequest(
            data_folder=self.dir_path,
            evalscript=metric,
            input_data=[input_data],
            responses=[output_data],
            bbox=self.bbox,
            size=self.bbox_size,
            config=self.config,
        )

    def download_data(self, save=True , redownload=False, **kwargs):
        '''
        Make The Request and download the data
        '''
        response =  self.request.get_data(save_data=save, redownload=redownload, max_threads=64,decode_data=False,  **kwargs)
        total_pu = response[0].headers['x-processingunits-spent']
        self.processing_units_consumed += round(float(total_pu), 3)
        print(f"\nProcessing units spent so far: {self.processing_units_consumed :.2f}")
        return response
        




