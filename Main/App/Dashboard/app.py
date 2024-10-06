from flask import Flask, render_template, jsonify, request
import googlemaps
from polyline import decode
import os
from bs4 import BeautifulSoup 
import pymysql
import pandas as pd

API_KEY = '' 
gmaps = googlemaps.Client(key=API_KEY)

app = Flask(__name__)

avoid_list = [
    [(24.763210, 46.652749),(24.790280, 46.717131)],
    [(24.790493, 46.716956),(24.763343, 46.652534)],
    [(24.611205, 46.764367),(24.585376, 46.710455)],
    [(24.585011, 46.710667),(24.608319, 46.761641)],
    [(24.680947, 46.687711),(24.985233, 46.533748)],
    [(24.985306, 46.533541),(24.680900, 46.687598)],
    [(24.796543, 46.817291),(24.707092, 46.626091)],
    [(24.706800, 46.625944),(24.796048, 46.817275)],
    [(24.882902, 46.806632),(24.811095, 46.671600)],
    [(24.810827, 46.671391),(24.882807, 46.806866)],
    [(24.635716, 46.800968),(24.712379, 46.763348)],
    [(24.713176, 46.762501),(24.636421, 46.800345)],
    [(24.712375, 46.758255), (24.676822, 46.641783)],
    [(24.712260, 46.758349), (24.676572, 46.641240 )],
]


RIYADH_BOUNDING_BOX = {
    'north': 25.0885,
    'south': 24.3246,
    'west': 46.2613,
    'east': 47.0484
}

def data_retreival():
    """
    Retrieve data from MySQL database hosted on RDS.
    The data contains traffic information such as the current number of vehicles on the road.
    """
    RDS_HOST = ""
    RDS_PORT = 3306  # MySQL default port
    DB_USER = ""
    DB_PASSWORD = ""
    DB_NAME = ""

    query = "SELECT * FROM traffic_counter_road"

    try:
        connection = pymysql.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()

            df = pd.DataFrame(results)

        return df.iloc[1]

    except pymysql.MySQLError as e:
        print(f"Error: {e}")

    finally:
        if connection:
            connection.close()

# Fetch directions from Google Maps API between two points
def get_directions(start, end, alternatives=False):
    directions_result = gmaps.directions(start, end, mode="driving", alternatives=alternatives)
    if directions_result:
        return directions_result
    return None

# Decode a Google Maps polyline into latitude and longitude points
def decode_polyline_to_points(polyline):
    return decode(polyline)

def do_routes_intersect(route_a_steps, route_b_steps):
    """
    Compare two routes' steps and check if they intersect at any point (same road).
    """
    for step_a in route_a_steps:
        for step_b in route_b_steps:
            # If the steps share the same point, check road names
            if step_a == step_b:
                road_name_a = get_road_name_from_step(step_a)
                road_name_b = get_road_name_from_step(step_b)
                if road_name_a == road_name_b:
                    return True  # Intersection found, return True
    return False  # No intersection found

# Extract road name from Google Maps direction step
def get_road_name_from_step(step):
    if 'html_instructions' in step:
        instruction = step['html_instructions']
        return extract_road_name(instruction)  # Extract and clean road name
    return None

# Clean HTML tags from Google Maps direction instruction
def extract_road_name(instruction):
    # Parse HTML to extract plain text (road name)
    return BeautifulSoup(instruction, "html.parser").text

# Find a route that avoids specific road segments in avoid_list
def find_valid_route(start, end, avoid_list):
    directions_a_b = get_directions(start, end, alternatives=True)
    if not directions_a_b:
        return None, None

    avoided_routes = []  # List to store avoided routes

    for route in directions_a_b:
        route_a_b_points = decode_polyline_to_points(route['overview_polyline']['points'])
        avoid_crossing = False

        # Check if the route intersects with any avoid_list segments
        for avoid_start, avoid_end in avoid_list:
            directions_c_d = get_directions(avoid_start, avoid_end, alternatives=False)
            if directions_c_d:
                route_c_d_points = decode_polyline_to_points(directions_c_d[0]['overview_polyline']['points'])
                if do_routes_intersect(route_a_b_points, route_c_d_points):
                    avoid_crossing = True
                    avoided_routes.append(directions_c_d[0])  # Save avoided route
                    break

        if not avoid_crossing:
            return route, avoided_routes  # Return valid route and avoided routes

    return None, None  # If all routes cross avoided segments

def is_within_bounds(lat, lng):
    """Check if a given latitude and longitude are within Riyadh's bounding box."""
    return (RIYADH_BOUNDING_BOX['south'] <= lat <= RIYADH_BOUNDING_BOX['north'] and
            RIYADH_BOUNDING_BOX['west'] <= lng <= RIYADH_BOUNDING_BOX['east'])

def is_route_within_bounds(route):
    """Ensure all steps in a route stay within Riyadh's bounding box."""
    for leg in route['legs']:
        for step in leg['steps']:
            start_lat = step['start_location']['lat']
            start_lng = step['start_location']['lng']
            end_lat = step['end_location']['lat']
            end_lng = step['end_location']['lng']

            if not is_within_bounds(start_lat, start_lng) or not is_within_bounds(end_lat, end_lng):
                return False
    return True

# Find a mid-point between start and end ensuring it lies within Riyadh
def find_mid_point_between(start, end):
    start_lat, start_lng = map(float, start.split(','))
    end_lat, end_lng = map(float, end.split(','))

    mid_lat = (start_lat + end_lat) / 2
    mid_lng = (start_lng + end_lng) / 2

    if is_within_bounds(mid_lat, mid_lng):
        return f"{mid_lat},{mid_lng}"
    else:
        return None

def recursive_route_search(start, end, avoid_list, depth=0, max_depth=3):
    """
    Recursively search for valid segments by calculating mid-points.
    """
    if depth > max_depth:
        return None

    mid_point = find_mid_point_between(start, end)
    if not mid_point:
        return None

    # Try to find a valid route between start and mid-point
    first_segment = find_valid_route(start, mid_point, avoid_list)
    if not first_segment:
        return recursive_route_search(start, mid_point, avoid_list, depth + 1, max_depth)

    # Try to find a valid route between mid-point and end
    second_segment = find_valid_route(mid_point, end, avoid_list)
    if not second_segment:
        return recursive_route_search(mid_point, end, avoid_list, depth + 1, max_depth)

    return merge_segments(first_segment, second_segment)

# Merge two route segments into one
def merge_segments(first_segment, second_segment):
    """Merge two route segments into a single route."""
    merged_route = {
        'legs': first_segment['legs'] + second_segment['legs'],
        'overview_polyline': {
            'points': first_segment['overview_polyline']['points'] + second_segment['overview_polyline']['points']
        }
    }
    return merged_route

@app.route('/calculate-route', methods=['POST'])
def calculate_route():
    data = request.json
    start = data['start']
    end = data['end']

    # Try to find a direct valid route
    route = find_valid_route(start, end, avoid_list)
    fastest_route = get_directions(start, end, alternatives=False)

    if not route:
        # If no valid direct route found, recursively search for one
        route = recursive_route_search(start, end, avoid_list)

    if route or fastest_route:
        fastest_route_json = format_route_to_json(fastest_route[0])
        if route:
            route_json = format_route_to_json(route)
            if route_json == fastest_route_json:
                return jsonify({
                    'status': 'success-one',
                    'normal_route': route_json,
                    'message': 'The fastest route is also the normal route.'
                })
            else:
                return jsonify({
                    'status': 'success-both',
                    'normal_route': route_json,
                    'fastest_route': fastest_route_json
                })
        else:
            return jsonify({
                'status': 'success-fastest',
                'fastest_route': fastest_route_json
            })
    else:
        return jsonify({
            'status': 'error',
            'message': 'All routes cross an avoided street or no valid route found.'
        })

# Format route into a JSON object for frontend consumption
def format_route_to_json(route):
    return {
        'start_address': route['legs'][0]['start_address'],
        'end_address': route['legs'][0]['end_address'],
        'distance': route['legs'][0]['distance']['text'],
        'duration': route['legs'][0]['duration']['text'],
        'overview_polyline': route['overview_polyline']['points']
    }

# Return the vehicle costs from the MySQL database
def get_truck_cost():
    data = data_retreival()
    return data['truck_cost']

def get_car_cost():
    data = data_retreival()
    return data['car_cost']

def get_motorbike_cost():
    data = data_retreival()
    return data['motorbike_cost']

def get_total_vehicles():
    data = data_retreival()
    return data['road_current']

# API to return vehicle costs and total vehicle count
@app.route('/get-vehicle-info', methods=['GET'])
def get_vehicle_info():
    return jsonify({
        'truck_cost': get_truck_cost(),
        'car_cost': get_car_cost(),
        'motorbike_cost': get_motorbike_cost(),
        'total_vehicles': get_total_vehicles()
    })

@app.route('/')
def index():
    return render_template(
        'index.html',
        truck_cost=get_truck_cost(),
        car_cost=get_car_cost(),
        motorbike_cost=get_motorbike_cost(),
        total_vehicles=get_total_vehicles()
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5858,debug=True)
