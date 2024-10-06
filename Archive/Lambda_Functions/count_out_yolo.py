import boto3
from gradio_client import Client, handle_file

s3 = boto3.client('s3')

S3_BUCKET_NAME = 'savingbuckett5'
S3_VIDEO_FOLDER = 'Videos/'

client = Client("coolfrxcrazy/YOLO_MODEL_DETECTION")

def lambda_handler(event, context):
    video_filename = 'IMG_9462.MOV'

    presigned_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET_NAME, 'Key': f"{S3_VIDEO_FOLDER}{video_filename}"},
        ExpiresIn=3600
    )

    result_in = client.predict(
        video={"video": handle_file(presigned_url)},
        api_name="/count_out"
    )

    return {
        'statusCode': 200,
        'body': result_in
    }
