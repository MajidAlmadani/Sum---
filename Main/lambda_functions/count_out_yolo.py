import boto3
from gradio_client import Client, handle_file

s3 = boto3.client('s3')

S3_BUCKET_NAME = 'savingbuckett5' 
S3_VIDEO_FOLDER = 'Videos/'

client = Client("coolfrxcrazy/YOLO_MODEL_DETECTION")

def lambda_handler(event, context):
    """
    AWS Lambda function to fetch a video from S3, send it to a YOLO detection model, and return the result.
    
    Args:
    - event: The event that triggered the Lambda function (e.g., an API Gateway request).
    - context: Lambda context object with metadata about the execution environment.
    
    Returns:
    - dict: A dictionary containing the HTTP status code and the YOLO detection results (if returned).
    """
    
    video_filename = ''  # Specify the video file name

    # Generate a presigned URL to access the video file from S3
    presigned_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET_NAME, 'Key': f"{S3_VIDEO_FOLDER}{video_filename}"},
        ExpiresIn=3600  # URL expires in 1 hour
    )

    # Call the YOLO detection API with the video file
    result_in = client.predict(
        video={"video": handle_file(presigned_url)},
        api_name="/count_out"
    )

    return {
        'statusCode': 200,
    }
