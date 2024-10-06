import boto3
import googlemaps
import pandas as pd
import io
import ast
import uuid
from datetime import datetime
import os

s3Client = boto3.client('s3')
gmaps = googlemaps.Client(key=os.getenv('API_KEY'))

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

def get_traffic_data_from_dataframe(gmaps_client, start_lat, start_lng, end_lat, end_lng, road_name, city='Riyadh'):
    origin = f"{start_lat},{start_lng}"
    destination = f"{end_lat},{end_lng}"
    
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
            'start_point': (start_lat, start_lng),
            'end_point': (end_lat, end_lng),
        }
    except Exception as e:
        print(f"Error fetching traffic data for {road_name}: {e}")
        return None

def generate_data_from_dataframe(s3_bucket, s3_key, gmaps_client):
    # Fetch the CSV from S3
    obj = s3Client.get_object(Bucket=s3_bucket, Key=s3_key)
    df = pd.read_csv(io.BytesIO(obj['Body'].read()))
    
    traffic_data_list = []
    df['start_point'] = df['start_point'].apply(ast.literal_eval)
    df['end_point'] = df['end_point'].apply(ast.literal_eval)
    
    for _, row in df.iterrows():
        road_name = row['road_name']
        start_lat, start_lng = row['start_point']
        end_lat, end_lng = row['end_point']
        
        traffic_data = get_traffic_data_from_dataframe(gmaps_client, start_lat, start_lng, end_lat, end_lng, road_name)
        
        if traffic_data:
            traffic_data_list.append(traffic_data)

    if traffic_data_list:
        traffic_df = pd.DataFrame(traffic_data_list)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"traffic_data_{timestamp}_{uuid.uuid4()}.csv"
        
        # Save the file to S3
        s3Client.put_object(Bucket=s3_bucket, Key=unique_filename, Body=traffic_df.to_csv(index=False))
        
        print(f"Traffic data saved as '{unique_filename}' in S3.")

def lambda_handler(event, context):
    s3_bucket = "savingbuckett5"
    s3_key = "segmented_dataset.csv"
    
    generate_data_from_dataframe(s3_bucket, s3_key, gmaps)
    
    return {
        'statusCode': 200,
        'body': 'Traffic data processed successfully'
    }