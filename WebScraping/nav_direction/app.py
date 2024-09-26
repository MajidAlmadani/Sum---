from flask import Flask, render_template, jsonify, request
import googlemaps
from polyline import decode
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup  # To clean HTML tags

load_dotenv()
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY_3')
gmaps = googlemaps.Client(key=API_KEY)

app = Flask(__name__)

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
            # Check if the routes share the same point (latitude and longitude)
            if step_a == step_b:
                road_name_a = get_road_name_from_step(step_a)
                road_name_b = get_road_name_from_step(step_b)
                if road_name_a == road_name_b:
                    return True 

    # No intersection found
    return False

def get_road_name_from_step(step):
    # The road name is usually part of 'html_instructions'
    if 'html_instructions' in step:
        instruction = step['html_instructions']
        # Optionally: Clean up the instruction to extract only the road name (e.g., remove HTML tags)
        road_name = extract_road_name(instruction)
        return road_name
    return None

def extract_road_name(instruction):
    # Here you can implement more complex logic if needed to extract the road name from the instruction
    # e.g., remove HTML tags, get the road name from the instructions
    return BeautifulSoup(instruction, "html.parser").text


# Find a route that avoids all segments in avoid_list and return the avoided routes
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
                    avoided_routes.append(directions_c_d[0])  # Save the avoided route
                    break  # This route crosses an avoidable segment, so skip it

        if not avoid_crossing:
            return route, avoided_routes  # Return the valid route and avoided routes

    return None, None

SAUDI_BOUNDING_BOX = {
    'north': 32.1546,   # Northernmost latitude in Saudi Arabia
    'south': 16.0036,   # Southernmost latitude in Saudi Arabia
    'west': 34.4956,    # Westernmost longitude in Saudi Arabia
    'east': 55.6667     # Easternmost longitude in Saudi Arabia
}

def is_within_bounds(lat, lng):
    """Check if a given latitude and longitude are within Saudi Arabia."""
    return (SAUDI_BOUNDING_BOX['south'] <= lat <= SAUDI_BOUNDING_BOX['north'] and
            SAUDI_BOUNDING_BOX['west'] <= lng <= SAUDI_BOUNDING_BOX['east'])

def find_mid_point_between(start, end):
    """Finds a mid-point between start and end, ensuring it is within Saudi Arabia."""
    start_lat, start_lng = map(float, start.split(','))
    end_lat, end_lng = map(float, end.split(','))

    mid_lat = (start_lat + end_lat) / 2
    mid_lng = (start_lng + end_lng) / 2

    # Check if the mid-point is within the valid range (Saudi Arabia bounds)
    if is_within_bounds(mid_lat, mid_lng):
        return f"{mid_lat},{mid_lng}"
    else:
        # If the mid-point is outside bounds, return None
        return None

def recursive_route_search(start, end, avoid_list, depth=0, max_depth=3):
    """
    Helper function that determines whether we can find valid segments
    by recursively calculating mid-points.
    """
    if depth > max_depth:
        return None

    # Calculate the mid-point between start and end
    mid_point = find_mid_point_between(start, end)
    
    if not mid_point:
        # If the mid-point is outside valid bounds, stop recursion
        return None

    # Check if direct route from start to mid-point is valid
    first_segment = find_valid_route(start, mid_point, avoid_list)
    
    if not first_segment:
        # If we can't find a valid first segment, try smaller segments
        return recursive_route_search(start, mid_point, avoid_list, depth + 1, max_depth)

    # Check if direct route from mid-point to end is valid
    second_segment = find_valid_route(mid_point, end, avoid_list)
    
    if not second_segment:
        # If we can't find a valid second segment, try smaller segments
        return recursive_route_search(mid_point, end, avoid_list, depth + 1, max_depth)

    # If both segments are valid, merge them and return
    return merge_segments(first_segment, second_segment)

def find_valid_route(start, end, avoid_list):
    """Attempts to find a valid route from start to end, avoiding specific segments."""
    # Get routes from A to B (with alternatives)
    routes = get_directions(start, end, alternatives=True)

    if not routes:
        return None

    # Iterate through all available routes
    for route in routes:
        route_a_b_points = decode_polyline_to_points(route['overview_polyline']['points'])

        # Assume this route is valid until proven otherwise
        avoid_crossing = False

        # Check if it crosses any avoided routes
        for avoid_start, avoid_end in avoid_list:
            directions_c_d = get_directions(avoid_start, avoid_end, alternatives=False)
            if directions_c_d:
                route_c_d_points = decode_polyline_to_points(directions_c_d[0]['overview_polyline']['points'])
                if do_routes_intersect(route_a_b_points, route_c_d_points):
                    avoid_crossing = True
                    break  # Exit loop since the route crosses an avoided route

        if not avoid_crossing:
            # Found a valid route that doesn't cross any avoided segments
            return route

    return None  # No valid route found


@app.route('/calculate-route', methods=['POST'])
def calculate_route():
    data = request.json
    start = data['start']
    end = data['end']
    
    # Try to find a direct route first
    route = find_valid_route(start, end, avoid_list)

    if not route:
        # If no valid direct route is found, try to find an alternative recursively
        route = recursive_route_search(start, end, avoid_list)

    if route:
        route_json = format_route_to_json(route)
        return jsonify({
            'status': 'success',
            'route': route_json
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'All routes cross an avoided street or no valid route found.'
        })

# Helper function to format the route into JSON format
def format_route_to_json(route):
    return {
        'start_address': route['legs'][0]['start_address'],
        'end_address': route['legs'][0]['end_address'],
        'distance': route['legs'][0]['distance']['text'],
        'duration': route['legs'][0]['duration']['text'],
        'overview_polyline': route['overview_polyline']['points']
    }

# Return avoided routes on map initialization
@app.route('/get-avoided-routes', methods=['GET'])
def get_avoided_routes():
    avoided_routes_json = []
    
    # Retrieve directions for each avoid list pair and add to the JSON
    for avoid_start, avoid_end in avoid_list:
        directions = get_directions(avoid_start, avoid_end, alternatives=False)
        if directions:
            avoided_routes_json.append(format_route_to_json(directions[0]))

    return jsonify({
        'status': 'success',
        'avoided_routes': avoided_routes_json
    })


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5858,debug=True)
