"""
detection/detector.py
─────────────────────
YOLOv8-based vehicle detection and counting at traffic intersections.

Detects and classifies:
  - car / two_wheeler / bus / truck / auto_rickshaw

Usage:
    from ml.detection.detector import VehicleDetector

    detector = VehicleDetector("weights/yolov8n_traffic.pt")
    result = detector.detect_frame(frame)
    print(result.counts)   # {'car': 5, 'bus': 1, ...}
"""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Map COCO class IDs → our vehicle labels
# YOLOv8 pretrained COCO: car=2, motorcycle=3, bus=5, truck=7
# For a custom-trained model these IDs will differ
COCO_TO_LABEL = {
    2: "car",
    3: "two_wheeler",
    5: "bus",
    7: "truck",
}

# For custom Indian traffic model — override after fine-tuning
CUSTOM_LABEL_MAP = {
    0: "car",
    1: "two_wheeler",
    2: "bus",
    3: "truck",
    4: "auto_rickshaw",
}


@dataclass
class DetectionResult:
    counts: dict[str, int] = field(default_factory=dict)
    total: int = 0
    avg_confidence: float = 0.0
    boxes: list[dict] = field(default_factory=list)
    frame_shape: tuple = (0, 0)

    def congestion_level(self, max_capacity: int = 60) -> float:
        """Normalize vehicle count to 0–1 congestion score."""
        return min(self.total / max_capacity, 1.0)


class VehicleDetector:
    """
    Wraps YOLOv8 for real-time vehicle detection.

    Args:
        weights_path: Path to .pt model weights.
                      Defaults to 'yolov8n' (nano pretrained) if not found.
        conf_threshold: Minimum confidence to count a detection.
        use_custom_labels: If True, uses CUSTOM_LABEL_MAP (post fine-tuning).
    """

    def __init__(
        self,
        weights_path: str = "weights/yolov8n_traffic.pt",
        conf_threshold: float = 0.40,
        use_custom_labels: bool = False,
        device: str = "cpu",
    ):
        from ultralytics import YOLO

        path = Path(weights_path)
        model_id = str(path) if path.exists() else "yolov8n.pt"
        self.model = YOLO(model_id)
        self.model.to(device)

        self.conf = conf_threshold
        self.label_map = CUSTOM_LABEL_MAP if use_custom_labels else COCO_TO_LABEL
        self.device = device

    def detect_frame(self, frame: np.ndarray, roi: Optional[tuple] = None) -> DetectionResult:
        """
        Run detection on a single BGR frame.

        Args:
            frame: OpenCV BGR image.
            roi: Optional (x1, y1, x2, y2) region of interest to crop before inference.

        Returns:
            DetectionResult with counts, boxes, and congestion.
        """
        if roi:
            x1, y1, x2, y2 = roi
            frame = frame[y1:y2, x1:x2]

        results = self.model.predict(
            source=frame,
            conf=self.conf,
            verbose=False,
            device=self.device,
        )

        counts: dict[str, int] = {}
        boxes = []
        confidences = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = self.label_map.get(cls_id)
                if label is None:
                    continue
                conf = float(box.conf[0])
                confidences.append(conf)
                counts[label] = counts.get(label, 0) + 1
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                boxes.append({
                    "label": label,
                    "confidence": round(conf, 3),
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                })

        return DetectionResult(
            counts=counts,
            total=sum(counts.values()),
            avg_confidence=round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
            boxes=boxes,
            frame_shape=frame.shape[:2],
        )

    def detect_video(self, video_path: str, skip_frames: int = 2):
        """
        Generator — yields DetectionResult for each processed frame.

        Args:
            video_path: Path to video file or RTSP stream URL.
            skip_frames: Process every Nth frame (performance tradeoff).
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        frame_idx = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx += 1
                if frame_idx % (skip_frames + 1) != 0:
                    continue
                yield self.detect_frame(frame)
        finally:
            cap.release()

    def annotate_frame(self, frame: np.ndarray, result: DetectionResult) -> np.ndarray:
        """Draw bounding boxes and labels on a frame (for visualization)."""
        annotated = frame.copy()
        colors = {
            "car": (0, 200, 0),
            "two_wheeler": (0, 150, 255),
            "bus": (255, 50, 50),
            "truck": (180, 0, 180),
            "auto_rickshaw": (255, 200, 0),
        }
        for box in result.boxes:
            x1, y1, x2, y2 = box["bbox"]
            color = colors.get(box["label"], (200, 200, 200))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label_text = f"{box['label']} {box['confidence']:.2f}"
            cv2.putText(annotated, label_text, (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Stats overlay
        y = 20
        for label, count in result.counts.items():
            cv2.putText(annotated, f"{label}: {count}", (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y += 22
        cv2.putText(annotated, f"Total: {result.total}  Congestion: {result.congestion_level():.0%}",
                    (10, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        return annotated


# ── Training helper ────────────────────────────────────────────────────────

def train_custom_detector(
    data_yaml: str,
    base_model: str = "yolov8n.pt",
    epochs: int = 50,
    imgsz: int = 640,
    output_dir: str = "weights/",
):
    """
    Fine-tune YOLOv8 on Indian traffic dataset.

    Args:
        data_yaml: Path to dataset YAML file (Ultralytics format).
        base_model: Starting checkpoint.
        epochs: Training epochs.
        imgsz: Input image size.
        output_dir: Where to save trained weights.

    Example YAML structure:
        path: /data/indian_traffic
        train: images/train
        val: images/val
        nc: 5
        names: [car, two_wheeler, bus, truck, auto_rickshaw]
    """
    from ultralytics import YOLO

    model = YOLO(base_model)
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        project=output_dir,
        name="yolov8_indian_traffic",
        patience=10,
        batch=16,
        workers=4,
        device="0",  # GPU — change to 'cpu' if needed
        augment=True,
        mosaic=1.0,
    )
    return results
