import torch
import torchvision
from torchvision.models.detection import FasterRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms import functional as F
import matplotlib.pyplot as plt
from PIL import Image
import os
import boto3
from io import BytesIO

# AWS S3 settings
BUCKET_NAME = "rpi-upload-bucket"
INPUT_PREFIX = "Dataset/samples/stage_2"
OUTPUT_PREFIX = "Dataset/output/stage_2"
SUPPORTED_EXTS = (".jpg", ".jpeg", ".png")

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key"),
    region_name='ap-southeast-1'
)

# Load Faster R-CNN with ResNet-50 backbone
def get_model(num_classes):
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=weights)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    return model

def load_image_from_s3(s3_key):
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    image_bytes = response['Body'].read()
    return Image.open(BytesIO(image_bytes)).convert("RGB")

def prepare_image(image, device):
    image_tensor = F.to_tensor(image).unsqueeze(0)
    return image_tensor.to(device)

def get_class_name(class_id):
    COCO_CLASSES = {0: "Background", 1: "Polyethylene", 2: "Polypropylene", 3: "Polystyrene"}
    return COCO_CLASSES.get(class_id, "Unknown")

def draw_boxes_and_save(image, s3_key, prediction, fig_size=(10, 10), threshold=0.5):
    from io import BytesIO
    image_name = os.path.basename(s3_key)
    base_name = os.path.splitext(image_name)[0]

    plt.figure(figsize=fig_size)
    plt.imshow(image)
    ax = plt.gca()

    boxes = prediction[0]['boxes'].cpu().numpy()
    labels = prediction[0]['labels'].cpu().numpy()
    scores = prediction[0]['scores'].cpu().numpy()

    for box, label, score in zip(boxes, labels, scores):
        if score > threshold:
            x_min, y_min, x_max, y_max = box
            class_name = get_class_name(label)
            ax.add_patch(plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                                       linewidth=2, edgecolor='r', facecolor='none'))
            ax.text(x_min, y_min, f"{class_name} ({score:.2f})", color='r', backgroundcolor='white')

    ax.axis('off')

    buffer = BytesIO()
    plt.savefig(buffer, format='PNG', bbox_inches='tight')
    buffer.seek(0)
    plt.close()

    s3_output_key = f"{OUTPUT_PREFIX}/annotated_all/{base_name}_all_boxes.png"
    s3.upload_fileobj(buffer, BUCKET_NAME, s3_output_key)
    print(f"Uploaded annotated image to S3: {s3_output_key}")

def save_image_per_box(image, s3_key, prediction, threshold=0.5):
    from io import BytesIO
    image_name = os.path.basename(s3_key)
    base_name = os.path.splitext(image_name)[0]

    boxes = prediction[0]['boxes'].cpu()
    labels = prediction[0]['labels'].cpu()
    scores = prediction[0]['scores'].cpu()

    for i, (box, label, score) in enumerate(zip(boxes, labels, scores)):
        if score >= threshold:
            fig, ax = plt.subplots(figsize=(12, 10))
            ax.imshow(image)

            box = box.tolist()
            x_min, y_min, x_max, y_max = box
            class_name = get_class_name(label.item())

            ax.add_patch(plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                                       linewidth=2, edgecolor='r', facecolor='none'))
            ax.text(x_min, y_min, f"{class_name} ({score:.2f})", color='r', backgroundcolor='white')

            ax.axis('off')

            buffer = BytesIO()
            plt.savefig(buffer, format='PNG', bbox_inches='tight')
            buffer.seek(0)
            plt.close()

            s3_output_key = f"{OUTPUT_PREFIX}/annotated_per_box/{base_name}_box_{i}.png"
            s3.upload_fileobj(buffer, BUCKET_NAME, s3_output_key)
            print(f"Uploaded box {i} to S3: {s3_output_key}")

def save_cropped_boxes(image, s3_key, prediction, threshold=0.5):
    from io import BytesIO
    image_name = os.path.basename(s3_key)
    base_name = os.path.splitext(image_name)[0]

    boxes = prediction[0]['boxes'].cpu()
    scores = prediction[0]['scores'].cpu()

    for i, (box, score) in enumerate(zip(boxes, scores)):
        if score >= threshold:
            box = box.int().tolist()
            cropped_img = image.crop(box)

            buffer = BytesIO()
            cropped_img.save(buffer, format='PNG')
            buffer.seek(0)

            s3_output_key = f"{OUTPUT_PREFIX}/cropped_boxes/{base_name}_crop_{i}.png"
            s3.upload_fileobj(buffer, BUCKET_NAME, s3_output_key)
            print(f"Uploaded cropped box {i} to S3: {s3_output_key}")

def main():
    num_classes = 4
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

    model = get_model(num_classes)
    model.load_state_dict(torch.load("faster_rcnn/models/fasterrcnn_resnet50_epoch_2.pth"))
    model.to(device)
    model.eval()

    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=INPUT_PREFIX)
    if 'Contents' not in response:
        print("No images found in S3 bucket.")
        return

    for obj in response['Contents']:
        key = obj['Key']
        if key.lower().endswith(SUPPORTED_EXTS):
            image_name = os.path.basename(key)
            print(f"Processing: {image_name}")

            image = load_image_from_s3(key)
            image_tensor = prepare_image(image, device)

            with torch.no_grad():
                prediction = model(image_tensor)

                draw_boxes_and_save(image, key, prediction, fig_size=(12, 10), threshold=0.5)
                save_image_per_box(image, key, prediction, threshold=0.5)
                save_cropped_boxes(image, key, prediction, threshold=0.5)

if __name__ == "__main__":
    main()
