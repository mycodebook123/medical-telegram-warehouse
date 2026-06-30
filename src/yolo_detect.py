"""
Runs YOLOv8 object detection on all downloaded Telegram images,
classifies each image into a content category, and saves results to CSV.
"""

import csv
import glob
import logging
from pathlib import Path

from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

IMAGE_ROOT = Path("data/raw/images")
OUTPUT_CSV = Path("data/yolo_detections.csv")

PERSON_CLASSES = {"person"}
PRODUCT_CLASSES = {"bottle", "cup", "bowl", "wine glass", "vase", "book"}


def categorize(detected_classes):
    has_person = bool(detected_classes & PERSON_CLASSES)
    has_product = bool(detected_classes & PRODUCT_CLASSES)

    if has_person and has_product:
        return "promotional"
    elif has_product and not has_person:
        return "product_display"
    elif has_person and not has_product:
        return "lifestyle"
    else:
        return "other"


def main():
    model = YOLO("yolov8n.pt")
    image_paths = glob.glob(str(IMAGE_ROOT / "*" / "*.jpg"))
    logger.info(f"Found {len(image_paths)} images to process.")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for img_path in image_paths:
        path_obj = Path(img_path)
        channel_name = path_obj.parent.name
        message_id = path_obj.stem

        try:
            results = model(img_path, verbose=False)
            result = results[0]

            detections = []
            detected_classes = set()

            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id]
                    confidence = float(box.conf[0])
                    detected_classes.add(cls_name)
                    detections.append((cls_name, confidence))

            category = categorize(detected_classes)

            if detections:
                for cls_name, confidence in detections:
                    rows.append([
                        channel_name, message_id, img_path,
                        cls_name, round(confidence, 4), category
                    ])
            else:
                rows.append([
                    channel_name, message_id, img_path,
                    "none", 0.0, category
                ])

            logger.info(f"{channel_name}/{message_id}: {detected_classes or 'none'} -> {category}")

        except Exception as e:
            logger.error(f"Failed to process {img_path}: {e}")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "channel_name", "message_id", "image_path",
            "detected_class", "confidence_score", "image_category"
        ])
        writer.writerows(rows)

    logger.info(f"Detection complete. Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()