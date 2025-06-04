import os
import boto3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

dynamodb = boto3.resource(
    'dynamodb',
    region_name='ap-southeast-1',
    aws_access_key_id=os.getenv('aws_access_key_id'),
    aws_secret_access_key=os.getenv('aws_secret_access_key')
)
table = dynamodb.Table('MicroplasticData')

# Adding alias for reserved keyword
ExpressionAttributeNames = {"#dt": "datetime"}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/filter_markers", methods=["POST"])
def filter_markers():
    data = request.get_json()
    min_date = data['min_date']
    max_date = data['max_date']

    # Scan DynamoDB for markers within the date range
    response = table.scan(
        FilterExpression="#dt BETWEEN :min_date AND :max_date",
        ExpressionAttributeNames={"#dt": "datetime"},
        ExpressionAttributeValues={
            ":min_date": min_date,
            ":max_date": max_date
        }
    )
    items = response['Items']

    # Convert marker data to the required format
    marker_data = [
        {
            "lat": float(item['latitude']),
            "lon": float(item['longitude']),
            # "density": int(item['density']),
            # "type": item['polymerType'],
            "date": item['datetime'],
            "image": item['imageURL']
        }
        for item in items
    ]

    return jsonify(marker_data)

@app.route('/latest_date', methods=['GET'])
def get_latest_date():
    response = table.scan(
        ProjectionExpression="#dt",
        ExpressionAttributeNames={"#dt": "datetime"}
    )
    items = response.get('Items', [])
    if not items:
        return jsonify({"latest_date": None})

    # Ensure 'datetime' is present in the items
    latest_date = max(item.get('datetime') for item in items if 'datetime' in item)
    return jsonify({"latest_date": latest_date})

@app.route('/total_samples', methods=['POST'])
def get_total_samples():
    data = request.get_json()
    min_date = data['min_date']
    max_date = data['max_date']

    # Scan DynamoDB for items within the date range
    response = table.scan(
        FilterExpression="#dt BETWEEN :min_date AND :max_date",
        ExpressionAttributeNames={"#dt": "datetime"},
        ExpressionAttributeValues={
            ":min_date": min_date,
            ":max_date": max_date
        }
    )
    items = response.get('Items', [])
    total_samples = len(items)
    return jsonify({"total_samples": total_samples})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Default to 5000 for local testing
    app.run(host="0.0.0.0", port=port, debug=True)