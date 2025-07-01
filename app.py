import os
import boto3
from flask import Flask, render_template, request, jsonify
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

def datetimeformat(value, format='%Y-%m-%d'):
    if isinstance(value, str):
        try:
            # Try parsing as YYYY-MM-DD
            dt = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    elif isinstance(value, datetime):
        dt = value
    else:
        return value
    
    # Replace format placeholders with strftime directives
    format = format.replace('%-d', '%d').replace('%-m', '%m')
    return dt.strftime(format)

# Register the filter with Jinja2
app.jinja_env.filters['datetimeformat'] = datetimeformat

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

@app.route("/chart")
def chart():
    return render_template("chart.html")

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
            "density": float(item['density']),
            # "type": item['polymerType'],
            "date": item['datetime'],
            "image": item['imageURL'],
            "annotatedimageurl": item['annotatedImageURL']
        }
        for item in items
    ]

    return jsonify(marker_data)

@app.route('/date_range', methods=['GET'])
def get_date_range():
    response = table.scan(
        ProjectionExpression="#dt",
        ExpressionAttributeNames={"#dt": "datetime"}
    )
    items = response.get('Items', [])
    if not items:
        return jsonify({"min_date": None, "max_date": None})

    # Filter out items without datetime and convert to datetime objects
    datetimes = []
    for item in items:
        if 'datetime' in item:
            try:
                dt = datetime.strptime(item['datetime'], '%Y-%m-%d %H:%M:%S')
                datetimes.append(dt)
            except (ValueError, TypeError):
                continue
    
    if not datetimes:
        return jsonify({"min_date": None, "max_date": None})
        
    min_date = min(datetimes).strftime('%Y-%m-%d %H:%M:%S')
    max_date = max(datetimes).strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        "min_date": min_date,
        "max_date": max_date
    })

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

@app.route('/average_density', methods=['POST'])
def get_average_density():
    data = request.get_json()
    min_date = data['min_date']
    max_date = data['max_date']

    response = table.scan(
        FilterExpression="#dt BETWEEN :min_date AND :max_date",
        ExpressionAttributeNames={"#dt": "datetime"},
        ExpressionAttributeValues={
            ":min_date": min_date,
            ":max_date": max_date
        }
    )
    items = response.get('Items', [])
    if not items:
        return jsonify({"average_density": 0})
    # Use float for density to support decimal values
    total_density = sum(float(item['density']) for item in items if 'density' in item)
    average_density = total_density / len(items)
    return jsonify({"average_density": average_density})

@app.route('/timeseries_data')
def timeseries_data():
    mode = request.args.get('mode', 'daily')
    response = table.scan()
    items = response.get('Items', [])
    data = defaultdict(list)

    for item in items:
        dt = item['datetime'][:10]  # 'YYYY-MM-DD'
        density = float(item['density'])
        if mode == 'weekly':
            # Find the Monday of the week
            date_obj = datetime.strptime(dt, "%Y-%m-%d")
            monday = date_obj - timedelta(days=date_obj.weekday())
            dt = monday.strftime("%Y-%m-%d")
        data[dt].append(density)

    result = []
    for date, densities in sorted(data.items()):
        avg = sum(densities) / len(densities)
        result.append({'date': date, 'average_density': avg, 'sample_count': len(densities)})

    return jsonify(result)

def format_date_display(start_date, end_date=None):
    """Format date or date range for display."""
    def format_single_date(date):
        day = str(date.day).lstrip('0')
        return f"{date.strftime('%B')} {day}, {date.year}"
    
    if not end_date or start_date == end_date:
        return format_single_date(start_date)
    
    start_day = str(start_date.day).lstrip('0')
    end_day = str(end_date.day).lstrip('0')
    
    if start_date.month == end_date.month and start_date.year == end_date.year:
        return f"{start_date.strftime('%B')} {start_day}-{end_day}, {start_date.year}"
    
    start_str = f"{start_date.strftime('%B')} {start_day}"
    end_str = f"{end_date.strftime('%B')} {end_day}, {end_date.year}"
    return f"{start_str} - {end_str}"

def filter_items_by_date_range(items, start_date, end_date):
    """Filter items that fall within the specified date range (inclusive)."""
    filtered = []
    for item in items:
        item_date = datetime.strptime(item['datetime'][:10], "%Y-%m-%d")
        if start_date <= item_date <= end_date:
            filtered.append(item)
    return filtered

@app.route('/detailed_data')
def detailed_data():
    # Get and validate parameters
    date_str = request.args.get('date')
    mode = request.args.get('mode', 'daily')
    
    if not date_str:
        return jsonify({'error': 'Date parameter is required'}), 400
    
    try:
        # Parse and validate date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Determine date range based on mode
    if mode == 'weekly':
        end_date = date_obj + timedelta(days=6)  # End of the week
        date_display = format_date_display(date_obj, end_date)
    else:  # daily
        end_date = date_obj
        date_display = format_date_display(date_obj)
    
    # Fetch and filter data
    try:
        response = table.scan()
        items = response.get('Items', [])
        filtered_items = filter_items_by_date_range(items, date_obj, end_date)
        
        # Calculate statistics
        sample_count = len(filtered_items)
        densities = [float(item['density']) for item in filtered_items]
        avg_density = sum(densities) / len(densities) if densities else 0
        
        # Prepare response data
        samples = [{
            'datetime': item['datetime'],
            'density': float(item['density']),
            'latitude': float(item['latitude']),
            'longitude': float(item['longitude']),
            'annotated_image_url': item.get('annotatedImageURL', '')  # Get the URL or empty string if not available
        } for item in filtered_items]
        
        return render_template('detailed_data.html', data={
            'date': date_display,
            'mode': mode,
            'samples': samples,
            'average_density': avg_density,
            'sample_count': sample_count
        })
        
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request'}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Default to 5000 for local testing
    app.run(host="0.0.0.0", port=port, debug=True)