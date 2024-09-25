from flask import Flask, render_template, jsonify, request
import googlemaps
from polyline import decode
import os
import time
from datetime import datetime
from dotenv import load_dotenv

import googlemaps
import gmplot

import pandas as pd

from io import StringIO
import uuid
import ast

import requests
from geopy.distance import geodesic


load_dotenv()
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY_3')
gmaps = googlemaps.Client(key=API_KEY)


app = Flask(__name__)


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
def do_routes_intersect(route_points_a, route_points_b):
    # Compare points in both routes to see if any points are near each other
    for point_a in route_points_a:
        for point_b in route_points_b:
            if point_a == point_b:  # Check if the routes share a point
                return True  # Routes intersect at some point
    return False  # No intersection

# Find a route that avoids all segments in avoid_list
def find_route_avoiding_segments(start, end, avoid_list):
    directions_a_b = get_directions(start, end, alternatives=True)

    if not directions_a_b:
        return None, None

    # Check each route from A to B
    for route in directions_a_b:
        route_a_b_points = decode_polyline_to_points(route['overview_polyline']['points'])

        # Check this route against all avoidable segments in avoid_list
        avoid_crossing = False
        for avoid_start, avoid_end in avoid_list:
            directions_c_d = get_directions(avoid_start, avoid_end, alternatives=False)
            if directions_c_d:
                route_c_d_points = decode_polyline_to_points(directions_c_d[0]['overview_polyline']['points'])
                if do_routes_intersect(route_a_b_points, route_c_d_points):
                    avoid_crossing = True
                    break  # This route crosses an avoidable segment, so skip it

        if not avoid_crossing:
            # Found a valid route that doesn't cross any avoidable segments
            return route['legs'][0]

    return None

# Generate Google Maps Directions link for a valid route
def generate_google_maps_link(route):
    start_location = route['start_location']
    end_location = route['end_location']

    gmaps_link = f"https://www.google.com/maps/dir/?api=1&origin={start_location['lat']},{start_location['lng']}&destination={end_location['lat']},{end_location['lng']}&travelmode=driving"

    return gmaps_link

# List of avoidable segments (C -> D pairs)
avoid_list = [
    [(24.7970264, 46.719939), (24.7388275, 46.59441409999999)],
    [(24.954535, 47.0142416), (24.7258606, 46.583506)],
    [(24.796827, 46.5643251), (24.7089077, 46.6195443)],
    [(24.9229714, 46.7204701), (24.796827, 46.5643251)],
    [(24.796827, 46.5643251), (24.6575642, 46.5630617)],
    [(24.7575596, 46.6895021), (24.70444, 46.6237931)],
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate-route', methods=['POST'])
def calculate_route():
    data = request.json
    start = data['start']
    end = data['end']
    
    # Find a route from the provided start and end points that avoids crossing any avoidable segments
    route = find_route_avoiding_segments(start, end, avoid_list)

    if route:
        gmaps_link = generate_google_maps_link(route)
        return jsonify({'status': 'success', 'gmaps_link': gmaps_link})
    else:
        return jsonify({'status': 'error', 'message': 'No valid route found that avoids crossing the segments in avoid_list.'})

if __name__ == "__main__":
    app.run(debug=True)
