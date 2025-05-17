import os
from picamera2 import Picamera2
from datetime import datetime
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_{timestamp}.jpg"
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
    finally:
        picam2.stop()

if __name__ == "__main__":
    capture_image_and_upload()