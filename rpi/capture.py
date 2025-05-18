import os
from picamera2 import Picamera2
from datetime import datetime, timezone, timedelta
import boto3
import tempfile

# Set raspberry pi datetime correctly first
# AWS S3 settings
BUCKET_NAME = "rpi-upload-bucket"
S3_SAVE_PREFIX = "Dataset/samples/stage_1"

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key"),
    region_name='ap-southeast-1'
)

# Initialize DynamoDB client
dynamodb = boto3.resource(
    'dynamodb',
    region_name='ap-southeast-1',
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key")
)
table = dynamodb.Table('MicroplasticData')

def capture_image_and_upload():
    # Initialize the camera
    picam2 = Picamera2()

    # Configure the camera
    config = picam2.create_still_configuration(main={"size": (1920, 1080)})  # Set resolution to 1080p
    picam2.configure(config)

    # Start the camera
    picam2.start()

    try:
        # Generate a timestamped filename
        now = datetime.now(timezone.utc).astimezone()  # local time with tz info
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')  # e.g., 2025-05-18 14:30:00
        filename = f"image_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
        print(f"Capturing image: {filename}")

        # Capture to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmpfile:
            picam2.capture_file(tmpfile.name)
            tmpfile.seek(0)
            s3_key = f"{S3_SAVE_PREFIX}/{filename}"
            print(f"Uploading image to S3: {s3_key}")
            with open(tmpfile.name, "rb") as data:
                s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=data, ContentType="image/jpeg")
        print("Image uploaded successfully!")
        os.remove(tmpfile.name)

        # Generate the S3 image URL
        image_url = f"https://{BUCKET_NAME}.s3.ap-southeast-1.amazonaws.com/{s3_key}"

        # Get the current highest sampleID
        response = table.scan(
            ProjectionExpression="sampleID"
        )
        items = response.get('Items', [])
        numeric_ids = []
        for item in items:
            sid = item.get('sampleID')
            try:
                numeric_ids.append(int(sid))
            except (ValueError, TypeError):
                continue
        if numeric_ids:
            max_id = max(numeric_ids)
            new_sample_id = max_id + 1
        else:
            new_sample_id = 1

        # Insert record into DynamoDB
        table.put_item(
            Item={
                "sampleID": new_sample_id,  # Number type
                "imageURL": image_url,
                "datetime": timestamp,
                # Add other attributes as needed
            }
        )
        print(f"Image URL inserted into DynamoDB with sampleID {new_sample_id}!")

    finally:
        picam2.stop()

if __name__ == "__main__":
    capture_image_and_upload()