import json
import boto3
import urllib.parse

s3 = boto3.client('s3')
S3_BUCKET_NAME = 'savingbuckett5'
S3_IMAGE_FOLDER = 'Videos/'

def lambda_handler(event, context):
    object_key = event['Records'][0]['s3']['object']['key']
    
    presigned_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET_NAME, 'Key': f"{S3_IMAGE_FOLDER}{image_filename}"},
        ExpiresIn=3600
    )

    # Call the Hugging Face API for OCR processing (ocr endpoint)
    result_ocr = client.predict(
        image={"image": handle_file(presigned_url)},
        api_name="/ocr"
    )

    return {
        'statusCode': 200,
        'body': f"OCR result for image {image_filename}: {result_ocr}"
    }