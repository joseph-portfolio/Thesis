import torch
import torchvision
from torchvision.models.detection import FasterRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms import functional as F
from PIL import Image
import io
import boto3
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def model_fn(model_dir):
    num_classes = 2
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=weights)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    model_path = os.path.join(model_dir, "model.pth")
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    return model

def input_fn(request_body, request_content_type):
    import json
    if request_content_type == "application/json":
        return json.loads(request_body)
    raise ValueError("Unsupported content type: {}".format(request_content_type))

def predict_fn(input_data, model):
    s3_image_url = input_data["s3_image_url"]
    sample_id = input_data.get("sample_id", "sample")
    # Download image from S3
    s3 = boto3.client("s3")
    bucket, key = s3_image_url.replace("s3://", "").split("/", 1)
    response = s3.get_object(Bucket=bucket, Key=key)
    image_bytes = response["Body"].read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_tensor = F.to_tensor(image).unsqueeze(0)
    with torch.no_grad():
        prediction = model(image_tensor)
    # Draw boxes on image
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(image)
    boxes = prediction[0]['boxes'].cpu().numpy()
    scores = prediction[0]['scores'].cpu().numpy()
    for box, score in zip(boxes, scores):
        if score > 0.5:
            x_min, y_min, x_max, y_max = box
            ax.add_patch(plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                                       linewidth=2, edgecolor='r', facecolor='none'))
    ax.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='PNG', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    # Upload annotated image to S3
    annotated_key = f"annotated/{sample_id}_annotated.png"
    s3.upload_fileobj(buf, bucket, annotated_key, ExtraArgs={"ContentType": "image/png"})
    annotated_url = f"s3://{bucket}/{annotated_key}"
    return {"annotated_image_url": annotated_url}

def output_fn(prediction, accept):
    import json
    if accept == "application/json":
        return json.dumps(prediction), "application/json"
    raise ValueError("Unsupported accept type: {}".format(accept))
