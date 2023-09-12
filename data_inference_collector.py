import streamlit as st
import geopandas as gpd
from streamlit_folium import st_folium
from pyproj import Geod
import shapely.geometry
import folium
import numpy as np
import joblib



def calculate_area_in_square_meters(geometry):
    geod = Geod(ellps="WGS84")
    area = abs(geod.geometry_area_perimeter(geometry)[0])
    return area

def states_gdf_from_geojson(file_path = './data/geojsons/sudan_states.geojson'):
    gdf = gpd.read_file(file_path)
    gdf = gdf.to_crs(crs='EPSG:4326')
    gdf['Area_M2'] = gdf['geometry'].apply(calculate_area_in_square_meters)
    gdf.rename(columns={'admin1RefN':'State'}, inplace=True)
    gdf = gdf[['State', 'Area_M2', 'geometry']]
    return gdf

def filter_by_state(gdf, state_name='El Gazira'):
    gdf = gdf[gdf['State'] == state_name]
    gdf.reset_index(inplace=True)
    gdf.drop(columns='index', inplace=True)
    return gdf

def save_gdf_to_geojson(gdf, file_path='./data/geojsons/sudan_states_2.geojson'):
    gdf.to_file(file_path, driver='GeoJSON')




def get_bbox_info(gdf, verbose=False):
    geod = Geod(ellps="WGS84")
    bbox = gdf.total_bounds
    polygon = shapely.geometry.box(*bbox, ccw=True)
    area = abs(geod.geometry_area_perimeter(polygon)[0])
    perimeter = abs(geod.geometry_area_perimeter(polygon)[1])
    width_line_coords = [(bbox[1], bbox[0]), (bbox[1], bbox[2])]
    width_line = shapely.geometry.LineString(width_line_coords)
    width = abs(geod.geometry_area_perimeter(width_line)[1])
    height_line_coords = [(bbox[1], bbox[0]), (bbox[3], bbox[0])]
    height_line = shapely.geometry.LineString(height_line_coords)
    height = abs(geod.geometry_area_perimeter(height_line)[1])
    gdf_bbox = gdf.total_bounds
    gdf_bbox_polygon = shapely.geometry.box(*gdf_bbox, ccw=True)
    gdf_bbox = [(gdf_bbox[1], gdf_bbox[0]), (gdf_bbox[3], gdf_bbox[2])]
    if verbose:
        st.write(f'Area of State: {area/1000000} km2')
        st.write(f'Perimeter of State: {perimeter/1000} km')
        st.write(f'Width of Bounding Box: {width/1000} km')
        st.write(f'Height of Bounding Box: {height/1000} km')
        st.write(f'Area of Bounding Box: {(calculate_area_in_square_meters(gdf_bbox_polygon))/1000000} km2')
        st.write(f'Perimeter of Bounding Box: {(2 * (width + height))/1000} km')
    return width, height, area, perimeter, gdf_bbox 

def get_square_list_for_state(gdf, max_width=25, max_height=25):
    max_width = max_width*1000
    max_height = max_height*1000
    width, height, area, perimeter, state_bbox = get_bbox_info(gdf)
    bottom_left = state_bbox[0]
    top_right = state_bbox[1]
    y_axis_max = top_right[0]
    y_axis_min = bottom_left[0]
    x_axis_max = top_right[1]
    x_axis_min = bottom_left[1]
    width_ratio = width/max_width
    if width_ratio > 1:
        number_of_widths = np.ceil(width_ratio)
        distance_between_widths = (x_axis_max - x_axis_min)/number_of_widths
        new_ys = np.arange(y_axis_min, y_axis_max, distance_between_widths)
        new_xs_left = np.repeat(x_axis_min, len(new_ys))
        new_xs_right = np.repeat(x_axis_max, len(new_ys))
        new_points_left = list(zip(new_ys, new_xs_left))
        new_points_right = list(zip(new_ys, new_xs_right))
        # for left_point, right_point in zip(new_points_left, new_points_right):
        #     folium.PolyLine([left_point, right_point], color='blue').add_to(m)
    height_ratio = height/max_height
    if height_ratio > 1:
        number_of_heights = np.ceil(height_ratio)
        distance_between_heights = (y_axis_max - y_axis_min)/number_of_heights
        new_xs = np.arange(x_axis_min, x_axis_max, distance_between_heights)
        new_ys_bottom = np.repeat(y_axis_min, len(new_xs))
        new_ys_top = np.repeat(y_axis_max, len(new_xs))
        new_points_bottom = list(zip(new_ys_bottom, new_xs))
        new_points_top = list(zip(new_ys_top, new_xs))
        # for bottom_point, top_point in zip(new_points_bottom, new_points_top):
        #     folium.PolyLine([bottom_point, top_point], color='blue').add_to(m)
    intersection_rows = []
    for x in new_xs:
        intersection_points = []
        for y in new_ys:
            p = (y, x)
            intersection_points.append(p)
            # folium.CircleMarker(location=p, radius=1, color='red').add_to(m2)
        intersection_rows.append(intersection_points)
    new_squares = []
    for row_index in range(len(intersection_rows)-1):
        row = intersection_rows[row_index]
        next_row = intersection_rows[row_index+1]
        for point_index in range(len(row)-1):
            point = row[point_index]
            next_point = row[point_index+1]
            next_row_point = next_row[point_index]
            next_row_next_point = next_row[point_index+1]
            square = [point, next_point, next_row_next_point, next_row_point]
            new_squares.append(square)
    return new_squares


def convert_square_to_polygon(square):
    new_points = []
    for point in square:
        new_point = (point[1], point[0])
        new_points.append(new_point)
    new_points.append(new_points[0])
    polygon = shapely.geometry.Polygon(new_points)
    return polygon


def main():
    gdf = states_gdf_from_geojson(file_path='./data/geojsons/sudan_states_gaziera.geojson')
    st.write(gdf)
    m = gdf.explore()
    max_width = 25
    max_height = 25
    new_squares = get_square_list_for_state(gdf, max_width=max_width, max_height=max_height)
    square_area = max_height * max_width
    number_of_squares = len(new_squares)
    #set np seed
    np_seed = 42
    np.random.seed(np_seed)
    target_number_of_squares = st.slider('Select number of squares', 0, number_of_squares, 50)
    random_indices = np.random.choice(number_of_squares, target_number_of_squares, replace=False)
    for index in random_indices:
        square = new_squares[index]
        folium.Polygon(square, color='blue').add_to(m)
    width, height, area, perimeter, state_bbox = get_bbox_info(gdf, verbose=True)
    folium.Rectangle(bounds=state_bbox, color='red').add_to(m)
    st.write(f'Number of Selected Squares: {target_number_of_squares}')
    st.write(f'Area of each square: {square_area} km2')
    st.write(f'Total area of selected squares: {square_area * target_number_of_squares} km2')
    st_folium(m)
    geom = [convert_square_to_polygon(square) for square in new_squares]
    gdf_sq = gpd.GeoDataFrame(geometry=geom)
    gdf_sq.crs = "EPSG:4326"
    gdf_sq['square_id'] = [f'gaizera_{i}' for i in range(len(gdf_sq))]
    gdf_sq['Area_M2'] = gdf_sq['geometry'].apply(calculate_area_in_square_meters)
    gdf_sq['Area_KM2'] = gdf_sq['Area_M2']/1000000
    gdf_sq['location'] = 'gaizera'
    gdf_sq['width'] = max_width
    gdf_sq['height'] = max_height
    st.write(gdf_sq)
    m2 = gdf_sq.explore()
    width, height, area, perimeter, state_bbox = get_bbox_info(gdf_sq, verbose=True)
    st_folium(m2)
    
    file_name = f'./data/joblibs/squares_{target_number_of_squares}_{max_width}x{max_height}_gaizera.joblib'
    save_data_bool = st.button('Save Data')
    if save_data_bool:
        joblib.dump(gdf_sq, file_name)
        st.write('Data Saved')

