import os
import random
import shutil
import json

# Source folder containing all images and annotation
SOURCE_DIR = "Dataset/all_images"
TRAIN_DIR = "Dataset/train/stage2"
VALID_DIR = "Dataset/valid/stage2"
ANNOT_PATH = os.path.join(SOURCE_DIR, "_annotations_coco.json")
TRAIN_ANNOT_PATH = os.path.join(TRAIN_DIR, "_annotations_coco.json")
VALID_ANNOT_PATH = os.path.join(VALID_DIR, "_annotations_coco.json")

SUPPORTED_EXTS = (".jpg", ".jpeg", ".png")

os.makedirs(TRAIN_DIR, exist_ok=True)
os.makedirs(VALID_DIR, exist_ok=True)

# List all image files in the source directory
all_images = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(SUPPORTED_EXTS)]
random.shuffle(all_images)

split_idx = int(len(all_images) * 0.8)
train_images = all_images[:split_idx]
valid_images = all_images[split_idx:]

# Copy images to train folder
for img in train_images:
    src = os.path.join(SOURCE_DIR, img)
    dst = os.path.join(TRAIN_DIR, img)
    shutil.copy2(src, dst)

# Copy images to valid folder
for img in valid_images:
    src = os.path.join(SOURCE_DIR, img)
    dst = os.path.join(VALID_DIR, img)
    shutil.copy2(src, dst)

print(f"Total images: {len(all_images)}")
print(f"Train images: {len(train_images)}")
print(f"Valid images: {len(valid_images)}")
print("Image splitting complete.")

# --- Split COCO annotation ---
def split_coco(coco, split_filenames):
    filename_to_image = {img['file_name']: img for img in coco['images']}
    split_images = [filename_to_image[f] for f in split_filenames if f in filename_to_image]
    split_image_ids = set(img['id'] for img in split_images)
    split_annotations = [ann for ann in coco['annotations'] if ann['image_id'] in split_image_ids]
    split_coco = {
        "images": split_images,
        "annotations": split_annotations,
        "categories": coco['categories']
    }
    return split_coco

with open(ANNOT_PATH, "r") as f:
    coco = json.load(f)

train_coco = split_coco(coco, train_images)
valid_coco = split_coco(coco, valid_images)

with open(TRAIN_ANNOT_PATH, "w") as f:
    json.dump(train_coco, f)

with open(VALID_ANNOT_PATH, "w") as f:
    json.dump(valid_coco, f)

print("COCO annotation splitting complete.")