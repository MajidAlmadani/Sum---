import gradio as gr
from ultralytics import YOLO
import cv2
import os
import pymysql
import boto3
from io import BytesIO
import io
from PIL import Image
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np

aws_access_key = ""
aws_secret_key = ""
aws_region = "eu-west-3"

s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region
)

S3_BUCKET_NAME = 'savingbuckett5'  # S3 bucket where frames are uploaded
S3_FOLDER = 'Video-Processing/'  # Folder inside the S3 bucket

model = YOLO("./YOLO_Model_v5.pt")

# Database connection details for RDS MySQL
RDS_HOST = ""
RDS_PORT = 3306 
DB_USER = ""
DB_PASSWORD = ""
DB_NAME = ""

def get_connection():
    """
    Establish a connection to the RDS MySQL database.
    
    Returns:
    - A connection object to the MySQL database.
    """
    return pymysql.connect(
        host=RDS_HOST,
        port=RDS_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def increment_road(id_value, increment_value, is_in=True):
    """
    Update the road traffic counter in the database for either 'in' or 'out' traffic.
    
    Args:
    - id_value (int): The road ID to update.
    - increment_value (int): The amount by which to increment the counter.
    - is_in (bool): Whether the traffic is counting 'in' (True) or 'out' (False).
    """
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            select_sql = "SELECT id, road_in, road_out, road_current FROM traffic_counter_road WHERE id = %s"
            cursor.execute(select_sql, (id_value,))
            result = cursor.fetchone()
        
        if result:
            with connection.cursor() as cursor:
                if is_in:
                    # Increment road_in counter and calculate current traffic
                    new_road_in = result['road_in'] + increment_value
                    new_road_current = new_road_in - result['road_out']
                    update_sql = """
                    UPDATE traffic_counter_road
                    SET road_in = %s, road_current = %s
                    WHERE id = %s
                    """
                    cursor.execute(update_sql, (new_road_in, new_road_current, id_value))
                else:
                    # Increment road_out counter and calculate current traffic
                    new_road_out = result['road_out'] + increment_value
                    new_road_current = result['road_in'] - new_road_out
                    update_sql = """
                    UPDATE traffic_counter_road
                    SET road_out = %s, road_current = %s
                    WHERE id = %s
                    """
                    cursor.execute(update_sql, (new_road_out, new_road_current, id_value))
            
            connection.commit()
    except pymysql.MySQLError as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()

def upload_frame_to_s3(frame, frame_number):
    """
    Upload a cropped frame (license plate) to an S3 bucket.
    
    Args:
    - frame: The cropped frame to upload.
    - frame_number (int): The frame number used to generate a unique S3 key.
    """
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image)

    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG")
    buffer.seek(0)

    # Define the S3 object key (file name)
    s3_key = f"{S3_FOLDER}frame_{frame_number}.jpg"

    # Upload the image to S3
    s3.upload_fileobj(buffer, S3_BUCKET_NAME, s3_key)

    print(f"Uploaded frame {frame_number} to S3 at {S3_BUCKET_NAME}/{s3_key}")

def process_video(video_path, count_type):
    """
    Process a video file and detect vehicles using the YOLO model.
    
    Args:
    - video_path (str): The path to the video file.
    - count_type (str): Either 'in' or 'out' to specify the type of traffic counting.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Error opening video file.")
    
    box = (1650, 900, 2816, 1500)  # Define the area for license plates
    counter = 0
    License_plate = set()
    class_names = ['License Plate', 'Car', 'Motorcycle', 'Truck']

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Use YOLO model to detect objects in the frame
        results = model.track(frame, persist=True)
        for result in results:
            for boxes in result.boxes:
                bbox = boxes.xyxy[0].cpu().numpy()  # Get bounding box
                class_id = int(boxes.cls[0].cpu().numpy())  # Get class ID
                conf = boxes.conf[0].cpu().numpy()  # Get confidence score
                id = int(boxes.id[0].cpu().numpy()) if boxes.id is not None else -1

                # Crop the detected object
                x1, y1, x2, y2 = map(int, bbox)
                cropped_object = frame[y1:y2, x1:x2]

                # Check if the object is inside the license plate detection box
                if x1 >= box[0] and y1 >= box[1] and x2 <= box[2] and y2 <= box[3]:
                    if id not in License_plate:
                        License_plate.add(id)
                        if count_type == "in":
                            print("It's counting IN")
                            increment_road(1, 1, is_in=True)
                        elif count_type == "out":
                            print("It's counting OUT")
                            increment_road(1, 1, is_in=False)

                        upload_frame_to_s3(cropped_object, counter)
                        counter += 1

def insert_data(license_value):
    """
    Insert a new license plate entry into the MySQL database.
    
    Args:
    - license_value (str): The license plate value to insert into the database.
    """
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            insert_sql = """
            INSERT INTO license_plates (license_plate)
            VALUES (%s)
            """
            cursor.execute(insert_sql, (license_value,))
        
        connection.commit()
    except pymysql.MySQLError as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()

def count_in(video):
    """
    Gradio interface function for processing 'in' traffic videos.
    Args:
    - video: The uploaded video file.
    
    Returns:
    - A success message after processing.
    """
    process_video(video, count_type="in")
    return "Processed vehicles counting 'in' successfully."

def count_out(video):
    """
    Gradio interface function for processing 'out' traffic videos.
    Args:
    - video: The uploaded video file.
    
    Returns:
    - A success message after processing.
    """
    process_video(video, count_type="out")
    return "Processed vehicles counting 'out' successfully."

def ocr(image):
    """
    Perform OCR (Optical Character Recognition) on an uploaded image.
    
    Args:
    - image: The uploaded image for OCR.
    
    Returns:
    - Extracted text from the image or an error message in case of failure.
    """
    try:
        # Convert image to PIL Image if it's a NumPy array
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        tokenizer = AutoTokenizer.from_pretrained('ucaslcl/GOT-OCR2_0', trust_remote_code=True)
        model = AutoModel.from_pretrained('ucaslcl/GOT-OCR2_0', trust_remote_code=True, low_cpu_mem_usage=True, use_safetensors=True, pad_token_id=tokenizer.eos_token_id).to(device)

        temp_image_path = os.path.join("/tmp", "temp_image.jpg")
        image.save(temp_image_path, format='JPEG')

        res = model.chat(tokenizer=tokenizer, image=temp_image_path, ocr_type='ocr')
        output_text = tokenizer.decode(res[0], skip_special_tokens=True)
        return output_text
    except Exception as e:
        return str(e)

# Gradio interfaces for counting in, out, and OCR
iface_in = gr.Interface(fn=count_in, inputs="video", outputs=None, api_name="count_in", title="YOLO Video Object Detection (Count In)", description="Upload a video to count vehicles 'in' and save frames to S3.")
iface_out = gr.Interface(fn=count_out, inputs="video", outputs=None, api_name="count_out", title="YOLO Video Object Detection (Count Out)", description="Upload a video to count vehicles 'out' and save frames to S3.")
iface_ocr = gr.Interface(fn=ocr, inputs="image", outputs="text", api_name="ocr", title="OCR Image Text Extraction")

# Create a tabbed interface for both endpoints
iface = gr.TabbedInterface([iface_in, iface_out, iface_ocr], ["Count In", "Count Out", "OCR"])

iface.launch()
