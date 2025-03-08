import streamlit as st
import time
import geopandas as gpd
import pandas as pd
import folium
# from streamlit_folium import folium_static
from streamlit_folium import st_folium, folium_static
import json

from data_downloader import (
    states_gdf_from_geojson, 
    get_available_dates, 
    dates_close_to_target_date, 
    get_dictionary_of_images_from_evalscripts, 
    get_total_polygon_from_gdf
)
from data_inference_collector import (
    get_square_list_for_state, 
    convert_square_to_polygon, 
    calculate_area_in_square_meters
)
from new_app import mask_downloaded_image, convert_mask_image_to_gdf
from new_utils import gdf_from_geojson
from datetime import datetime


def get_month_name(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B")

CRS = "EPSG:4326"

# Set page config
st.set_page_config(
    page_title="Sudan Mapping Tool",
    page_icon="🌍",
    layout="wide"
)

# Initialize session state variables
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'state' not in st.session_state:
    st.session_state.state = None
if 'square_index' not in st.session_state:
    st.session_state.square_index = None
if 'date' not in st.session_state:
    st.session_state.date = "2024-09-01"
if 'gdf' not in st.session_state:
    st.session_state.gdf = None
if 'squares_gdf' not in st.session_state:
    st.session_state.squares_gdf = None
if 'mask_path' not in st.session_state:
    st.session_state.mask_path = "example.geojson"
if 'available_dates' not in st.session_state:
    st.session_state.available_dates = []

# Helper function to display maps
def display_map(gdf, title, column=None, m=None, show=True, use_static=False, opacity=0.6):
    if len(gdf)>1000:
        gdf = gdf.sample(1000)
    m = gdf.explore(column=column, style_kwds={"fillOpacity": opacity}, m=m)
    if show:
        st.subheader(title)
        if use_static:
            folium_static(m, width=1200, height=600)
        else:
            st_folium(m, width=1200, height=600)
    return m

# App header
st.title("Data acquisition demo")
st.write("Go through the download pipeline")

# Progress bar for steps
progress_bar = st.progress(st.session_state.step / 7)
st.caption(f"Step {st.session_state.step} of 7")

# STEP 1: Show Sudan map and select state
if st.session_state.step == 1:
    col1, col2 = st.columns([5,1])

    with col1:
        st.header("Step 1: Select a State in Sudan")
        
        # Load Sudan states
        sudan_gdf = states_gdf_from_geojson()
        # Display the map
        m= display_map(sudan_gdf, "Map of Sudan States", "State")
        
        # Create a selection box for states
        states_list = sorted(sudan_gdf["State"].unique().tolist())
        states_list = ["El Gazira", "Gedaref"]
    with col2: 
        selected_state = st.selectbox("Select a state:", states_list)
        if st.button("Continue to Next Step", type="primary"):
            st.session_state.state = selected_state
            st.session_state.step = 2
            st.rerun()

# STEP 2: Show selected state
elif st.session_state.step == 2:
    col1, col2 = st.columns([5,1])
    with col1:
        st.header(f"Step 2: Select Squares Size to cover {st.session_state.state} State")
        
        # Filter to show only the selected state
        sudan_gdf = states_gdf_from_geojson()
        state_gdf = sudan_gdf[sudan_gdf["State"] == st.session_state.state]
        st.session_state.gdf = state_gdf
        
        # Display the map of the selected state
        display_map(state_gdf, f"Map of {st.session_state.state} State")
    
    with col2:
        max_height = st.slider("Maximum Height (km)", 5, 50, 25)
        max_width = st.slider("Maximum Width (km)", 5, 50, 25)
        st.write("These parameters control the size of the grid squares used for analysis.")
        st.write("Smaller squares provide more detail but create more computational load.")
        if st.button("Continue to Generate Squares", type="primary"):
            st.session_state.step = 3
            st.session_state.max_height = max_height
            st.session_state.max_width = max_width
            st.rerun()
        st.markdown('---')
        if st.button("⬅️ Go Back"):
            st.session_state.step = 1
            st.rerun()

# STEP 3: Generate and display squares
elif st.session_state.step == 3:
    col1, col2 = st.columns([5,1])
    with col1:
        st.header(f"Step 3: Squares Generated. Select Specific one as Example (41)  {st.session_state.state}")
        if "square_index" not in  st.session_state:
            st.session_state.square_index = 41

        squares = get_square_list_for_state(gdf=st.session_state.gdf, max_height=st.session_state.max_height, max_width=st.session_state.max_height)
        geom = [convert_square_to_polygon(square) for square in squares]
        squares_gdf = gpd.GeoDataFrame(geometry=geom)
        squares_gdf.crs = CRS
        squares_gdf['square_id'] = [f'{st.session_state.state}_{i}' for i in range(len(squares_gdf))]
        squares_gdf['Area_M2'] = squares_gdf['geometry'].apply(calculate_area_in_square_meters)
        squares_gdf['Area_KM2'] = squares_gdf['Area_M2']/1000000
        squares_gdf['location'] = st.session_state.state
        squares_gdf['selected'] = [i== st.session_state.square_index for i in range(len(squares_gdf))]
        st.session_state.squares_gdf = squares_gdf
        # Display the map with squares
        state = display_map(gdf = st.session_state.gdf, title="", show=False)
        state_with_squares = display_map( gdf=squares_gdf, column="selected", title= f"{st.session_state.state} with Analysis Squares",)
        st.success(f"Successfully generated {len(squares_gdf)} analysis squares")
        
    if st.session_state.squares_gdf is not None:

        with col2:
            square_index = st.slider("Select a square by index:", 0, len(st.session_state.squares_gdf), 41)
            st.session_state.square_index = square_index

            st.write("Select A square to focus on, Number 41 works nicely with the sample data later !")
            if st.button("Continue to Select Square", type="primary"):
                st.session_state.step = 4
                st.session_state.square_index = square_index
                st.rerun()
            if st.button("⬅️ Go Back"):
                st.session_state.step = 2
                st.rerun()


# STEP 4: Select a specific square
elif st.session_state.step == 4:
    col1, col2 = st.columns([5,1])
    with col1:
        st.header(f"Step 4: Select an year for which we try to find the best days in months May-Oct (6 months)")
        selected_square_gdf = st.session_state.squares_gdf[
            st.session_state.squares_gdf['square_id'] == f"{st.session_state.state}_{st.session_state.square_index}"
        ]
        state = display_map(gdf = st.session_state.gdf, title="", show=False)
        display_map(selected_square_gdf, f"Selected Square: {st.session_state.state}_{st.session_state.square_index}", m=state)
        
    with col2:
        years = [2018, 2019, 2020, 2021, 2022, 2023, 20224]
        year = st.selectbox("Select a year:", years)
        pre_selected_dates = [
            f'{year}-06-01',
            f'{year}-07-16',
            f'{year}-08-05',
            f'{year}-09-19',
            f'{year}-10-29',
        ]
        if st.button("Get Dates", type="primary"):
            available_dates = get_available_dates(selected_square_gdf, year)
            with st.spinner("Getting dates"):
                target_dates = []
                for date in pre_selected_dates:
                    target_dates.append(dates_close_to_target_date(dates=available_dates, target_date=date)[0])
                    st.write(f"found {date} in {get_month_name(date)} for year {year}")
                    time.sleep(0.5)
                time.sleep(2)
                st.session_state.dates = target_dates
                st.session_state.available_dates = available_dates
                st.session_state.step = 5
                st.rerun()

        if st.button("⬅️ Go Back"):
            st.session_state.step = 3
            st.rerun()

# STEP 5: Select a date for image collection
elif st.session_state.step == 5:
    st.header(f"Step 5: Choose Labels GeoJson")
    col1, col2 = st.columns([5,1])
    with col1:

        c1, c2= st.columns(2)
        with c1:
            # Open and read the example GeoJSON file as text
            st.markdown("### Use pre defined example")
            with open("example.geojson", "r", encoding="utf-8") as file:
                geojson_text = file.read()
            st.code(body=geojson_text, language="json", line_numbers=True)
        with c2:
            st.markdown("### Copy and Paste GeoJson from [EO Browser](https://apps.sentinel-hub.com/eo-browser/?zoom=11&lat=14.558&lng=32.99469&themeId=DEFAULT-THEME&visualizationUrl=U2FsdGVkX19OB2t4BdO4os9NT%2BdSqrb14knDxsCkPAL821uNSYHg3qNv8Csuf9J0uy1EPpzVc5L33IfAOraa9r83uglOVLWary8W1bLtejqr1Sx%2B4f3CYCpfDnehd9nJ&datasetId=S2L2A&fromTime=2025-03-07T00%3A00%3A00.000Z&toTime=2025-03-07T23%3A59%3A59.999Z&layerId=1_TRUE_COLOR&demSource3D=%22MAPZEN%22), needs login")

            geojson_text = st.text_area("Paste your GeoJSON here:", height=300)
            if geojson_text:
                try:
                    geojson_data = json.loads(geojson_text)
                    st.json(geojson_data)
                except json.JSONDecodeError:
                    st.error("Invalid GeoJSON format. Please check your input.")


    with col2:
        if st.button("Continue to Upload Labels", type="primary"):
            if geojson_text:
                geojson_data = json.loads(geojson_text)
                with open("temp_mask.geojson", "w", encoding="utf-8") as file:
                    json.dump(geojson_data, file, indent=2)
                st.session_state.mask_path = "temp_mask.geojson"
                st.session_state.mask_name = "Copied from EO"

            else:
                st.session_state.mask_path = "example.geojson"
                st.session_state.mask_name = "from example Geojson"
            st.session_state.step = 6
            st.rerun()
    
        if st.button("⬅️ Go Back"):
            st.session_state.step = 4
            st.rerun()

# STEP 6: Upload mask GeoJSON
elif st.session_state.step == 6:
    col1, col2 = st.columns([5,3])
    with col1:
        st.header(f"Step 6: Show Labels ({st.session_state.mask_name}) with Selected Square")
        location_name = f'{st.session_state.state}_{st.session_state.square_index}'
        selected_square_gdf = st.session_state.squares_gdf[st.session_state.squares_gdf['square_id'] == location_name]
        try:
            mask_gdf = gdf_from_geojson(geojson_path=st.session_state.mask_path, crs=CRS)
            column_name = "label" if "label" in mask_gdf else None
            state = display_map(gdf = st.session_state.gdf, title="", show=False, opacity=0.0)
            square_map = display_map(selected_square_gdf, "", show=False, m=state, opacity=0.1)
            m = display_map(mask_gdf, "Uploaded Mask", m=square_map, column=column_name)
            st.success("Labels uploaded successfully")
        except:
            st.warning("Please upload a proper GeoJSON file or continue with the default example mask")
        
    with col2:
        st.markdown("### Current selections:")
        if st.session_state.state:
            st.markdown(f"**State:** {st.session_state.state}")
        if st.session_state.square_index is not None:
            st.markdown(f"**Location Name:** {st.session_state.state}_{st.session_state.square_index}")
        if st.session_state.dates:
            st.markdown(f"**Target Dates:** {st.session_state.dates}")
        if (st.session_state.mask_name):
            st.markdown(f"### Labels:")
            st.write(mask_gdf.to_wkt())
            
        if st.button("Continue to Processing", type="primary"):
            st.session_state.step = 7
            st.rerun()
        if st.button("⬅️ Go Back"):
            st.session_state.step = 5
            st.rerun()

# STEP 7: Process and display results
elif st.session_state.step == 7:
    st.header(f"Step 7: Process and View Results")
    
    location_name = f'{st.session_state.state}_{st.session_state.square_index}'
    dates = st.session_state.dates
    
    
    # Add a selectbox for evalscript
    # evalscript_options = ["ALL", "NDVI", "NDWI", "TRUE_COLOR"]
    # evalscript = st.selectbox("Select image processing type:", evalscript_options)
    evalscript = "ALL"
    
    # Get the selected square
    selected_square_gdf = st.session_state.squares_gdf[st.session_state.squares_gdf['square_id'] == location_name]
    total_polygon = get_total_polygon_from_gdf(gdf=selected_square_gdf)
    
    dates_bar = st.progress(value=0, text="Going Through Dates..")
    month_geojson_dict = {}
    for i,date in enumerate(dates):
        with st.empty():
            dates_bar.progress(i/len(dates), text=f"Processing {get_month_name(date)} imagery")
            # Download imagery
            st.text("Downloading satellite imagery...")
            download_dict = get_dictionary_of_images_from_evalscripts(total_polygon=total_polygon, date=date, location_name=location_name)
            # Apply mask
            st.text("Applying label mask to imagery...")
            mask_gdf = gdf_from_geojson(geojson_path=st.session_state.mask_path, crs=CRS)
            mask_path = mask_downloaded_image(mask_gdf=mask_gdf, location_name=location_name, date=date, evalscript=evalscript)
            # Convert mask to Dataframe
            st.text("Converting results to GeoJSON...")
            geojson_path = convert_mask_image_to_gdf(location_name=location_name, date=date, evalscript=evalscript, crs=CRS)
            month = get_month_name(date)
            month_geojson_dict[month] = geojson_path
    dates_bar.progress(100, text=f"Done")
    st.success("Done,  Aggregating results")
    # Display results
    gdfs = []
    for i, (month, geojson_path) in enumerate(month_geojson_dict.items()):
        gdf = gdf_from_geojson(geojson_path=geojson_path, crs=CRS)        
        for col in ['date', 'evalscript']:
            if col in gdf.columns:
                gdf = gdf.drop(columns=col)
        band_cols = [col for col in gdf.columns if 'band' in col]
        rename_dict = {col: f"{month}_{col}" for col in band_cols}
        gdf = gdf.rename(columns=rename_dict)
        if i > 0:
            if "location_name" in gdf.columns:
                gdf = gdf.drop(columns="location_name")
            if "geometry" in gdf.columns:
                gdf = gdf.drop(columns="geometry")
        gdfs.append(gdf)

    result_gdf = pd.concat(gdfs, axis=1)
    st.markdown(f"### Processed CSV:")
    st.write(result_gdf.to_wkt())

    state = display_map(gdf = st.session_state.gdf, title="", show=False, opacity=0.0)
    square_map = display_map(selected_square_gdf, "", show=False, m=state, opacity=0.1)
    display_map(result_gdf, f"Processed Labels for {location_name} on {dates}", use_static=True, m=square_map)

    
    # Display statistics
                
    
    # if st.button("⬅️ Go Back"):
    #     st.session_state.step = 6
    #     st.rerun()

# Add a sidebar with summary information
# with st.sidebar:
#     st.header("Analysis Summary")
#     st.write("Current selections:")
    
#     if st.session_state.state:
#         st.write(f"**State:** {st.session_state.state}")
    
#     if st.session_state.square_index is not None:
#         st.write(f"**Square:** {st.session_state.state}_{st.session_state.square_index}")
    
#     if st.session_state.date:
#         st.write(f"**Date:** {st.session_state.date}")
    
#     # Reset button
#     if st.button("Reset Analysis"):
#         for key in st.session_state.keys():
#             if key != 'step':
#                 st.session_state[key] = None
#         st.session_state.step = 1
#         st.session_state.date = "2024-09-01"
#         st.rerun()

# Update progress bar
# progress_bar.progress(st.session_state.step / 7)
