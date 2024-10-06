from flask import Flask, render_template, jsonify, request
import googlemaps
from polyline import decode
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup  # To clean HTML tags
import pymysql
import pandas as pd

load_dotenv()
API_KEY = 'AIzaSyBvsVrsscV50q6bVV7ofEm2tzCz08F1k1A'
gmaps = googlemaps.Client(key=API_KEY)

app = Flask(__name__)

# Define avoided segments globally
avoid_list = [
    [(24.761297, 46.647798), (24.790838, 46.717976)],
    [(24.585388, 46.709163), (24.611205, 46.764367)],
    [(24.676630, 46.641683), (24.713557, 46.759786)],
    [(24.883136, 46.585421), (24.680947, 46.687711)],
    [(24.704598, 46.623868), (24.796673, 46.817037)],
    [(24.785575, 46.568700), (24.869630, 46.803826)],
    [(24.789092, 46.724027), (24.633372, 46.801978)],
]

def data_retreival():
    RDS_HOST = "database-2.cnqamusmkwon.eu-north-1.rds.amazonaws.com"
    RDS_PORT = 3306  # MySQL default port
    DB_USER = "root"
    DB_PASSWORD = "mkmk162345"
    DB_NAME = "traffic"

    # SQL Query to retrieve data
    query = "SELECT * FROM traffic_counter_road"  # Replace with your table name

    # Connect to the RDS MySQL instance
    try:
        connection = pymysql.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor  # Fetches the result as a dictionary
        )

        # Execute the query and fetch the data
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()  # Fetch all rows from the table
            
            # Convert the query results into a Pandas DataFrame
            df = pd.DataFrame(results)

        # Show the first 5 rows of the DataFrame
        return df.iloc[1]

    except pymysql.MySQLError as e:
        print(f"Error: {e}")

    finally:
        if connection:
            connection.close()


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

RIYADH_BOUNDING_BOX = {
    'north': 25.0885,   # Northernmost latitude in Riyadh
    'south': 24.3246,   # Southernmost latitude in Riyadh
    'west': 46.2613,    # Westernmost longitude in Riyadh
    'east': 47.0484     # Easternmost longitude in Riyadh
}

def is_within_bounds(lat, lng):
    """Check if a given latitude and longitude are within the Riyadh bounding box."""
    return (RIYADH_BOUNDING_BOX['south'] <= lat <= RIYADH_BOUNDING_BOX['north'] and
            RIYADH_BOUNDING_BOX['west'] <= lng <= RIYADH_BOUNDING_BOX['east'])

def is_route_within_bounds(route):
    """Check if the entire route stays within the Riyadh bounding box."""
    # Go through each step in the route and check the start and end locations
    for leg in route['legs']:
        for step in leg['steps']:
            start_lat = step['start_location']['lat']
            start_lng = step['start_location']['lng']
            end_lat = step['end_location']['lat']
            end_lng = step['end_location']['lng']

            if not is_within_bounds(start_lat, start_lng) or not is_within_bounds(end_lat, end_lng):
                return False
    return True

def find_mid_point_between(start, end):
    """Finds a mid-point between start and end, ensuring it is within Riyadh."""
    start_lat, start_lng = map(float, start.split(','))
    end_lat, end_lng = map(float, end.split(','))

    mid_lat = (start_lat + end_lat) / 2
    mid_lng = (start_lng + end_lng) / 2

    # Check if the mid-point is within the Riyadh bounding box
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

def merge_segments(first_segment, second_segment):
    """Merges two route segments into one."""
    merged_route = {
        'legs': first_segment['legs'] + second_segment['legs'],
        'overview_polyline': {
            'points': first_segment['overview_polyline']['points'] + second_segment['overview_polyline']['points']
        }
    }
    return merged_route
def find_valid_route(start, end, avoid_list):
    """Attempts to find a valid route from start to end, avoiding specific segments."""
    # Get routes from A to B (with alternatives)
    routes = get_directions(start, end, alternatives=True)

    if not routes:
        return None

    # Iterate through all available routes
    for route in routes:
        route_a_b_points = decode_polyline_to_points(route['overview_polyline']['points'])

        # Ensure the entire route stays within bounds
        if not is_route_within_bounds(route):
            continue  # Skip this route if it goes outside the bounding box

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
    fastest_route = get_directions(start, end, alternatives=False)

    if not route:
        # If no valid direct route is found, try to find an alternative recursively
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
        print(fastest_route)
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

# Define vehicle costs as functions
def get_truck_cost():
    data = data_retreival()
    return data['truck_cost']  # Example cost for truck, can be dynamic

def get_car_cost():
    data = data_retreival()
    return data['car_cost']  # Example cost for truck, can be dynamic

def get_motorbike_cost():
    data = data_retreival()
    return data['motorbike_cost']  # Example cost for truck, can be dynamic

# Define a function to return the total number of vehicles
def get_total_vehicles():
    data = data_retreival()
    return data['road_current']  # Example cost for truck, can be dynamic

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


@app.route('/get-vehicle-info', methods=['GET'])
def get_vehicle_info():
    return jsonify({
        'truck_cost': get_truck_cost(),
        'car_cost': get_car_cost(),
        'motorbike_cost': get_motorbike_cost(),
        'total_vehicles': get_total_vehicles()
    })

@app.route('/get-fastest-route', methods=['POST'])
def get_fastest_route():
    data = request.json
    start = data['start']
    end = data['end']
    
    # Fetch the fastest route from start to end
    fastest_route = get_directions(start, end, alternatives=False)

    if fastest_route:
        route_json = format_route_to_json(fastest_route[0])
        return jsonify({
            'status': 'success',
            'route': route_json
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'No fastest route found.'
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
