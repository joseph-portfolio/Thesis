import torch
import torchvision
from torch.utils.data import DataLoader
from torchvision.models.detection import FasterRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.datasets import CocoDetection
from torchvision.transforms import functional as F
from torchmetrics.detection.mean_ap import MeanAveragePrecision

# Define transformations
class CocoTransform:
    def __call__(self, image, target):
        image = F.to_tensor(image)  # Convert PIL image to tensor
        return image, target
    
# Dataset class
def get_coco_dataset(img_dir, ann_file):
    return CocoDetection(
        root=img_dir,
        annFile=ann_file,
        transforms=CocoTransform()
    )

# Load Faster R-CNN with ResNet-50 backbone
def get_model(num_classes):
    # Specify the weight enum explicitly
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT

    # Load pre-trained Faster R-CNN model
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=weights)
    
    # Get the number of input features for the classifier
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    
    # Replace the pre-trained head with a new one
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    return model

def train_one_epoch(model, optimizer, data_loader, device, epoch):
    model.train()
    for images, targets in data_loader:
        # Move images to the device
        images = [img.to(device) for img in images]

        # Validate and process targets
        processed_targets = []
        valid_images = []
        for i, target in enumerate(targets):
            boxes = []
            labels = []
            for obj in target:
                # Extract bbox
                bbox = obj["bbox"]  # Format: [x, y, width, height]
                x, y, w, h = bbox

                # Ensure the width and height are positive
                if w > 0 and h > 0:
                    boxes.append([x, y, x + w, y + h])  # Convert to [x_min, y_min, x_max, y_max]
                    labels.append(obj["category_id"])

            # Only process if there are valid boxes
            if boxes:
                processed_target = {
                    "boxes": torch.tensor(boxes, dtype=torch.float32).to(device),
                    "labels": torch.tensor(labels, dtype=torch.int64).to(device),
                }
                processed_targets.append(processed_target)
                valid_images.append(images[i])  # Add only valid images

        # Skip iteration if no valid targets
        if not processed_targets:
            continue

        # Ensure images and targets are aligned
        images = valid_images

        # Forward pass
        loss_dict = model(images, processed_targets)
        losses = sum(loss for loss in loss_dict.values())

        # Backpropagation
        optimizer.zero_grad()
        losses.backward()
        optimizer.step()

    print(f"Epoch [{epoch + 1}] Loss: {losses.item():.4f}")

@torch.no_grad()
def evaluate_model_with_map(model, data_loader, device):
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
            boxes = []
            labels = []
            for obj in tgt:
                x, y, w, h = obj["bbox"]
                boxes.append([x, y, x + w, y + h])
                labels.append(obj["category_id"])
            gts.append({
                "boxes": torch.tensor(boxes, dtype=torch.float32),
                "labels": torch.tensor(labels, dtype=torch.int64)
            })

        metric.update(preds, gts)

    results = metric.compute()
    print("Evaluation Results (mAP):")
    for k, v in results.items():
        print(f"{k}: {v:.4f}")

def main():
    # Load datasets
    train_dataset = get_coco_dataset(
        img_dir="faster_rcnn/Dataset/train",
        ann_file="faster_rcnn/Dataset/train/_annotations_coco.json"
    )

    val_dataset = get_coco_dataset(
        img_dir="faster_rcnn/Dataset/valid",
        ann_file="faster_rcnn/Dataset/valid/_annotations_coco.json"
    )

    # DataLoader
    train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True, collate_fn=lambda x: tuple(zip(*x)))
    val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False, collate_fn=lambda x: tuple(zip(*x)))

    # Initialize the model
    num_classes = 2 # Background + Microplastics
    model = get_model(num_classes)

    # Move model to GPU if available
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model.to(device)

    # Define optimizer and learning rate scheduler
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)

    # Training loop
    num_epochs = 3 # Adjust as needed
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


