from sentinelhub import SHConfig
import datetime
from sentinelhub import MimeType, CRS, BBox, SentinelHubRequest, DataCollection, bbox_to_dimensions

config = SHConfig()

config.instance_id      = "19e335ae-5825-448f-a6ea-0b5dbe5c6468"
config.sh_client_id     = "ad568507-ef49-48ff-9bdb-90368803ce50"
config.sh_client_secret = "9<9(+SV[%jwr7..<jFCDgt[Hj{W;40>@x,uGBkdO"


evalscript_all_bands = """
    //VERSION=3
    function setup() {
        return {
            input: [{
                bands: ["B01","B04","B03","B02","B05","B06","B07","B08","B8A","B09","B11","B12", "CLD", "SCL", "AOT"],
                units: ["REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "REFLECTANCE", "PERCENT", "DN", "OPTICAL_DEPTH" ]

            }],
            output: {
                bands: 14,
                sampleType: "FLOAT32" // 32-bit floating point
            }
        };
    }

    function evaluatePixel(sample) {
        return [sample.B01,
                sample.B02,
                sample.B03,
                sample.B04,
                sample.B05,
                sample.B06,
                sample.B07,
                sample.B08,
                sample.B8A,
                sample.B09,
                sample.B11,
                sample.B12,
                sample.CLD,
                sample.SCL,
                sample.AOT];
    }
"""


def get_all_bands_response(bbox, start_date, end_date='', output_dir='outputs',
                           es = evalscript_all_bands,
                           order_type='leastCC', upsampling_type='BILINEAR',
                           data_source=DataCollection.SENTINEL2_L2A, resolution=10,
                           identifier='default', response_format=MimeType.TIFF,
                           save_data=True):
    if end_date == '':
        date_1 = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = (date_1 + datetime.timedelta(days=6)).strftime("%Y-%m-%d")
    bbox_hub = BBox(bbox=bbox, crs=CRS.WGS84)
    bbox_size = bbox_to_dimensions(bbox_hub, resolution=resolution)
    interval = (start_date, end_date)
    inputs = SentinelHubRequest.input_data(data_collection=data_source, time_interval=interval,
                                           mosaicking_order=order_type, upsampling=upsampling_type)
    outputs = SentinelHubRequest.output_response(identifier=identifier, response_format=response_format)
    request_all_bands = SentinelHubRequest(
        data_folder=output_dir,
        evalscript=es,
        input_data=[inputs],
        responses=[outputs],
        bbox=bbox_hub,
        size=bbox_size,
        config=config)
    all_bands_response = request_all_bands.get_data(save_data=save_data, max_threads=100)
    return all_bands_response
