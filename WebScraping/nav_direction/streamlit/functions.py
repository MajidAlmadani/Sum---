import streamlit as st
import googlemaps
from polyline import decode
import os
# from dotenv import load_dotenv
from bs4 import BeautifulSoup  # To clean HTML tags
import json

# load_dotenv()
API_KEY = 'AIzaSyBvsVrsscV50q6bVV7ofEm2tzCz08F1k1A'
gmaps = googlemaps.Client(key=API_KEY)

# Define avoided segments globally
avoid_list = [
    [(24.7970264, 46.719939), (24.7388275, 46.59441409999999)],
    [(24.954535, 47.0142416), (24.7258606, 46.583506)],
    [(24.796827, 46.5643251), (24.7089077, 46.6195443)],
    [(24.9229714, 46.7204701), (24.796827, 46.5643251)],
    [(24.796827, 46.5643251), (24.6575642, 46.5630617)],
    [(24.7575596, 46.6895021), (24.70444, 46.6237931)],
]

# Fetch directions from Google Maps API
def get_directions(start, end, alternatives=False):
    directions_result = gmaps.directions(start, end, mode="driving", alternatives=alternatives)
    if directions_result:
        return directions_result
    return None

# Decode a Google Maps encoded polyline to latitude and longitude points
def decode_polyline_to_points(polyline):
    return decode(polyline)

# Check if two routes intersect based on their polylines
def do_routes_intersect(route_a_steps, route_b_steps):
    # Loop through steps of both routes
    for step_a in route_a_steps:
        for step_b in route_b_steps:
            if step_a == step_b:
                road_name_a = get_road_name_from_step(step_a)
                road_name_b = get_road_name_from_step(step_b)
                if road_name_a == road_name_b:
                    return True
    return False

def get_road_name_from_step(step):
    if 'html_instructions' in step:
        instruction = step['html_instructions']
        road_name = extract_road_name(instruction)
        return road_name
    return None

def extract_road_name(instruction):
    return BeautifulSoup(instruction, "html.parser").text

# Functions for avoiding segments
def find_route_avoiding_segments(start, end, avoid_list):
    directions_a_b = get_directions(start, end, alternatives=True)
    if not directions_a_b:
        return None, None
    avoided_routes = []
    for route in directions_a_b:
        route_a_b_points = decode_polyline_to_points(route['overview_polyline']['points'])
        avoid_crossing = False
        for avoid_start, avoid_end in avoid_list:
            directions_c_d = get_directions(avoid_start, avoid_end, alternatives=False)
            if directions_c_d:
                route_c_d_points = decode_polyline_to_points(directions_c_d[0]['overview_polyline']['points'])
                if do_routes_intersect(route_a_b_points, route_c_d_points):
                    avoid_crossing = True
                    avoided_routes.append(directions_c_d[0])
                    break
        if not avoid_crossing:
            return route, avoided_routes
    return None, None

def find_mid_point_between(start, end):
    start_lat, start_lng = map(float, start.split(','))
    end_lat, end_lng = map(float, end.split(','))
    mid_lat = (start_lat + end_lat) / 2
    mid_lng = (start_lng + end_lng) / 2
    if is_within_bounds(mid_lat, mid_lng):
        return f"{mid_lat},{mid_lng}"
    return None

def recursive_route_search(start, end, avoid_list, depth=0, max_depth=3):
    if depth > max_depth:
        return None
    mid_point = find_mid_point_between(start, end)
    if not mid_point:
        return None
    first_segment = find_valid_route(start, mid_point, avoid_list)
    if not first_segment:
        return recursive_route_search(start, mid_point, avoid_list, depth + 1, max_depth)
    second_segment = find_valid_route(mid_point, end, avoid_list)
    if not second_segment:
        return recursive_route_search(mid_point, end, avoid_list, depth + 1, max_depth)
    return merge_segments(first_segment, second_segment)

def merge_segments(first_segment, second_segment):
    merged_route = {
        'legs': first_segment['legs'] + second_segment['legs'],
        'overview_polyline': {
            'points': first_segment['overview_polyline']['points'] + second_segment['overview_polyline']['points']
        }
    }
    return merged_route

def find_valid_route(start, end, avoid_list):
    routes = get_directions(start, end, alternatives=True)
    if not routes:
        return None
    for route in routes:
        route_a_b_points = decode_polyline_to_points(route['overview_polyline']['points'])
        if not is_route_within_bounds(route):
            continue
        avoid_crossing = False
        for avoid_start, avoid_end in avoid_list:
            directions_c_d = get_directions(avoid_start, avoid_end, alternatives=False)
            if directions_c_d:
                route_c_d_points = decode_polyline_to_points(directions_c_d[0]['overview_polyline']['points'])
                if do_routes_intersect(route_a_b_points, route_c_d_points):
                    avoid_crossing = True
                    break
        if not avoid_crossing:
            return route
    return None

RIYADH_BOUNDING_BOX = {
    'north': 25.0885,
    'south': 24.3246,
    'west': 46.2613,
    'east': 47.0484
}

def is_within_bounds(lat, lng):
    return (RIYADH_BOUNDING_BOX['south'] <= lat <= RIYADH_BOUNDING_BOX['north'] and
            RIYADH_BOUNDING_BOX['west'] <= lng <= RIYADH_BOUNDING_BOX['east'])

def is_route_within_bounds(route):
    for leg in route['legs']:
        for step in leg['steps']:
            start_lat = step['start_location']['lat']
            start_lng = step['start_location']['lng']
            end_lat = step['end_location']['lat']
            end_lng = step['end_location']['lng']
            if not is_within_bounds(start_lat, start_lng) or not is_within_bounds(end_lat, end_lng):
                return False
    return True

# Helper functions for JSON formatting
def format_route_to_json(route):
    return {
        'start_address': route['legs'][0]['start_address'],
        'end_address': route['legs'][0]['end_address'],
        'distance': route['legs'][0]['distance']['text'],
        'duration': route['legs'][0]['duration']['text'],
        'overview_polyline': route['overview_polyline']['points']
    }

# Vehicle cost and total vehicle functions
def get_truck_cost():
    return 500

def get_car_cost():
    return 400

def get_motorbike_cost():
    return 100

def get_total_vehicles():
    return 150