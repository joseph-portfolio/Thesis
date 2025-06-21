import json
import torch
import torchvision
from torch.utils.data import DataLoader, Dataset
from torchvision.models.detection import FasterRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms import functional as F
from torchmetrics.detection.mean_ap import MeanAveragePrecision
from PIL import Image
import os
import boto3
from io import BytesIO

# AWS S3 settings
BUCKET_NAME = "rpi-upload-bucket"
TRAIN_PREFIX = "Dataset/train"
VALID_PREFIX = "Dataset/valid"
SUPPORTED_EXTS = (".jpg", ".jpeg", ".png")

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key"),
    region_name='ap-southeast-1'
)

# Dataset class for loading images and annotations from S3
class S3CocoDataset(Dataset):
    def __init__(self, bucket_name, prefix, transforms=None):
        print(f"Initializing dataset for prefix: {prefix}")
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.transforms = transforms
        self.image_keys = []
        self.annotations = {}

        # Load COCO-style annotations
        annotation_key = f"{prefix}/_annotations_coco.json"
        print(f"Loading annotations from: {annotation_key}")
        self.load_annotations_from_s3(annotation_key)

        # List all image objects in the S3 prefix
        print(f"Listing images in S3 bucket: {bucket_name}, prefix: {prefix}")
        response = s3.list_objects_v2(Bucket=self.bucket_name, Prefix=self.prefix)
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.lower().endswith(SUPPORTED_EXTS):
                    self.image_keys.append(key)
        print(f"Found {len(self.image_keys)} images in {prefix}")

    def load_annotations_from_s3(self, key):
        response = s3.get_object(Bucket=self.bucket_name, Key=key)
        annotation_bytes = response['Body'].read()
        coco_data = json.loads(annotation_bytes)

        # Parse COCO annotations
        self.annotations = {img['file_name']: [] for img in coco_data['images']}
        for ann in coco_data['annotations']:
            image_id = ann['image_id']
            image_file_name = next(img['file_name'] for img in coco_data['images'] if img['id'] == image_id)
            self.annotations[image_file_name].append(ann)
        print(f"Loaded annotations for {len(self.annotations)} images")

    def __len__(self):
        return len(self.image_keys)

    def __getitem__(self, idx):
        # Load image from S3
        image_key = self.image_keys[idx]
        image = self.load_image_from_s3(image_key)

        # Load corresponding annotations
        file_name = os.path.basename(image_key)
        target = self.process_annotations(file_name)

        if self.transforms:
            image, target = self.transforms(image, target)

        return image, target

    def load_image_from_s3(self, key):
        print(f"Loading image from S3: {key}")
        response = s3.get_object(Bucket=self.bucket_name, Key=key)
        image_bytes = response['Body'].read()
        return Image.open(BytesIO(image_bytes)).convert("RGB")

    def process_annotations(self, file_name):
        annotations = self.annotations.get(file_name, [])
        boxes = []
        labels = []

        for ann in annotations:
            bbox = ann['bbox']  # COCO format: [x, y, width, height]
            x, y, w, h = bbox
            if w > 0 and h > 0:  # Ensure valid bounding boxes
                boxes.append([x, y, x + w, y + h])  # Convert to [x_min, y_min, x_max, y_max]
                labels.append(ann['category_id'])

        target = {
            "boxes": torch.tensor(boxes, dtype=torch.float32),
            "labels": torch.tensor(labels, dtype=torch.int64),
        }
        print(f"Processed annotations for {file_name}: {len(boxes)} boxes")
        return target

# Define transformations
class CocoTransform:
    def __call__(self, image, target):
        image = F.to_tensor(image)  # Convert PIL image to tensor
        return image, target

# Load Faster R-CNN with ResNet-50 backbone
def get_model(num_classes):
    print("Initializing Faster R-CNN model")
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=weights)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    return model

def train_one_epoch(model, optimizer, data_loader, device, epoch):
    print(f"Starting training for epoch {epoch + 1}")
    model.train()
    total_loss = 0
    for batch_idx, (images, targets) in enumerate(data_loader):
        # Move images and targets to the device
        images = [img.to(device) for img in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        # Forward pass
        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())
        total_loss += losses.item()

        # Backpropagation
        optimizer.zero_grad()
        losses.backward()
        optimizer.step()

        if (batch_idx + 1) % 10 == 0:
            print(f"Batch [{batch_idx + 1}/{len(data_loader)}] Loss: {losses.item():.4f}")

    print(f"Epoch [{epoch + 1}] Average Loss: {total_loss / len(data_loader):.4f}")

@torch.no_grad()
def evaluate_model_with_map(model, data_loader, device):
    print("Starting evaluation")
    model.eval()
    metric = MeanAveragePrecision()

    for images, targets in data_loader:
        images = [img.to(device) for img in images]
        outputs = model(images)

        preds = []
        gts = []

        for pred, tgt in zip(outputs, targets):
            # Predicted outputs
            preds.append({
                "boxes": pred["boxes"].cpu(),
                "scores": pred["scores"].cpu(),
                "labels": pred["labels"].cpu()
            })

            # Ground truth
            gts.append({
                "boxes": tgt["boxes"].cpu(),
                "labels": tgt["labels"].cpu()
            })

        metric.update(preds, gts)

    results = metric.compute()
    print("Evaluation Results (mAP):")
    for k, v in results.items():
        print(f"{k}: {v:.4f}")

def main():
    print("Loading datasets from S3")
    train_dataset = S3CocoDataset(
        bucket_name=BUCKET_NAME,
        prefix=TRAIN_PREFIX,
        transforms=CocoTransform()
    )

    val_dataset = S3CocoDataset(
        bucket_name=BUCKET_NAME,
        prefix=VALID_PREFIX,
        transforms=CocoTransform()
    )

    print("Creating data loaders")
    train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True, collate_fn=lambda x: tuple(zip(*x)))
    val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False, collate_fn=lambda x: tuple(zip(*x)))

    print("Initializing model")
    num_classes = 4  # PE, PP, PS, + Background
    model = get_model(num_classes)

    # Move model to GPU if available
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model.to(device)

    print("Setting up optimizer and scheduler")
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)

    # Training loop
    num_epochs = 3  # Adjust as needed
    for epoch in range(num_epochs):
        print(f"Processing Epoch {epoch + 1}...")
        train_one_epoch(model, optimizer, train_loader, device, epoch)
        lr_scheduler.step()

        # Save the model's state dictionary after every epoch
        model_path = f"faster_rcnn/models/fasterrcnn_resnet50_epoch_{epoch + 1}.pth"
        torch.save(model.state_dict(), model_path)
        print(f"Model saved: {model_path}")

        evaluate_model_with_map(model, val_loader, device)

if __name__ == "__main__":
    main()


