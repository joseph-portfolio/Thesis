import os
from picamera2 import Picamera2
from datetime import datetime, timezone, timedelta
import boto3
import tempfile
from decimal import Decimal
from get_location import get_location
from flask import Flask
import json

app = Flask(__name__)

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

# Initialize SageMaker
runtime = boto3.client(
    'sagemaker-runtime',
    region_name='ap-southeast-1',
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key")
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

        # Call the inference endpoint
        payload = {
            "image_url": image_url,
            "sample_id": str(new_sample_id)
        }
        print(f"Calling inference endpoint with: {payload}")
        try:
            response = runtime.invoke_endpoint(
                EndpointName='detect-microplastics',
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            inference_result_stage1 = json.loads(response['Body'].read())
            print(f"Inference result: {inference_result_stage1}")
        except Exception as e:
            print(f"Error calling inference endpoint: {e}")
            inference_result_stage1 = None

        # Get latitude and longitude from GPS
        location = get_location()
        if location:
            latitude, longitude = location
            latitude = Decimal(str(round(latitude, 6)))
            longitude = Decimal(str(round(longitude, 6)))
        else:
            print("Failed to get GPS location. Placing it at center.")
            latitude = Decimal("14.37")
            longitude = Decimal("121.25")

        # Insert record into DynamoDB
        item = {
            "sampleID": new_sample_id,
            "imageURL": image_url,
            "datetime": timestamp,
            "latitude": latitude,
            "longitude": longitude,
        }
        if inference_result_stage1:
            annotated_url = inference_result_stage1.get("annotated_image_url")
            box_count = inference_result_stage1.get("box_count")
            if annotated_url is not None:
                item["annotatedImageURL"] = annotated_url
            if box_count is not None:
                item["boxCount"] = box_count
                try:
                    item["density"] = float(box_count) / 70 # Volume of water
                except Exception:
                    item["density"] = None

        # Only classify if at least one box is detected
        if box_count and box_count > 0:
            print(f"Calling classify-microplastics endpoint with: {payload}")
            try:
                classify_response = runtime.invoke_endpoint(
                    EndpointName='classify-microplastics',
                    ContentType='application/json',
                    Body=json.dumps(payload)
                )
                inference_result_stage2 = json.loads(classify_response['Body'].read())
                print(f"Classification result: {inference_result_stage2}")
                item["percent_PS"] = inference_result_stage2.get("percent_PS")
                item["percent_PP"] = inference_result_stage2.get("percent_PP")
                item["percent_PE"] = inference_result_stage2.get("percent_PE")
            except Exception as e:
                print(f"Error calling classify-microplastics endpoint: {e}")
        else:
            # No microplastics detected, set percent composition to zero
            item["percent_PS"] = 0.0
            item["percent_PP"] = 0.0
            item["percent_PE"] = 0.0

        table.put_item(Item=item)
        print(f"Image URL inserted into DynamoDB with sampleID {new_sample_id}!")

    finally:
        picam2.stop()
        picam2.close()

@app.route('/capture', methods=['POST'])
def capture_image_endpoint():
    try:
        capture_image_and_upload()
        return {"message": "Image captured and uploaded successfully!"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)