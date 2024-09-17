import boto3
import pandas as pd
import googlemaps
import os
from io import StringIO
from datetime import datetime
import uuid  # For generating unique filenames
from dotenv import load_dotenv


df = pd.read_csv('filtered_road_names.csv')


def get_road_start_end(gmaps_client, road_name, city='Riyadh'):
    try:
        geocode_result = gmaps_client.geocode(f"{road_name}, {city}")
        if geocode_result and 'bounds' in geocode_result[0]['geometry']:
            start_point = geocode_result[0]['geometry']['bounds']['northeast']
            end_point = geocode_result[0]['geometry']['bounds']['southwest']
            return (start_point['lat'], start_point['lng']), (end_point['lat'], end_point['lng'])
        else:
            return None, None
    except Exception as e:
        print(f"Error getting start/end points for {road_name}: {e}")
        return None, None
    
    
# Function to determine traffic color
def determine_traffic_color(delay, duration):
    if delay < 0.05 * duration:
        return 'Blue'
    elif delay < 0.20 * duration:
        return 'Yellow'
    elif delay < 0.50 * duration:
        return 'Orange'
    elif delay < 1.00 * duration:
        return 'Red'
    else:
        return 'Dark Red'

# Function to get traffic data from Google Maps
def get_traffic_data(gmaps_client, road_name, city='Riyadh'):
    start_coords, end_coords = get_road_start_end(gmaps_client, road_name, city)
    
    if not start_coords or not end_coords:
        print(f"Could not retrieve start/end points for {road_name}.")
        return None

    origin = f"{start_coords[0]},{start_coords[1]}"
    destination = f"{end_coords[0]},{end_coords[1]}"
    
    try:
        directions_result = gmaps_client.directions(
            origin, destination, mode="driving", departure_time="now", traffic_model="best_guess"
        )

        if not directions_result:
            return None

        route = directions_result[0]['legs'][0]
        duration_in_traffic_min = route['duration_in_traffic']['value'] / 60
        distance_km = route['distance']['value'] / 1000
        speed_kmh = distance_km / (duration_in_traffic_min / 60)
        delay_min = (route['duration_in_traffic']['value'] - route['duration']['value']) / 60
        traffic_condition = determine_traffic_color(delay_min, route['duration']['value'] / 60)
        timestamp = datetime.now().isoformat()
        
        return {
            'road_name': road_name,
            'distance_km': distance_km,
            'duration_in_traffic_min': duration_in_traffic_min,
            'speed_kmh': speed_kmh,
            'delay_min': delay_min,
            'traffic_condition': traffic_condition,
            'timestamp': timestamp,
        }
    except Exception as e:
        print(f"Error fetching traffic data for {road_name}: {e}")
        return None

# Function to generate traffic data and save to S3 with unique filenames
def generate_data_for_first_10_roads(csv_file, gmaps_client):
    df = pd.read_csv(csv_file)
    road_names = df['Road Name']
    traffic_data_list = [get_traffic_data(gmaps_client, road, city='Riyadh') for road in road_names if get_traffic_data(gmaps_client, road, city='Riyadh')]

    if traffic_data_list:
        # Convert traffic data list to DataFrame
        traffic_df = pd.DataFrame(traffic_data_list)
        
        # Generate a unique filename using UUID and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"traffic_data_{timestamp}_{uuid.uuid4()}.csv"
        
        # Write to in-memory CSV buffer
        csv_buffer = StringIO()
        traffic_df.to_csv(csv_buffer, index=False)

        # Upload to S3
        s3 = boto3.client('s3')
        s3.put_object(Bucket='savingbuckett5', Key=unique_filename, Body=csv_buffer.getvalue())
        
        print(f"Traffic data saved to S3 as '{unique_filename}'.")


API_KEY = os.environ['GOOGLE_MAPS_API_KEY']
gmaps = googlemaps.Client(key=API_KEY)
generate_data_for_first_10_roads('filtered_road_names.csv', gmaps)