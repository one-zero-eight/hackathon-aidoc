from PIL import Image
import numpy as np
from ultralyticsplus import YOLO
from dataclasses import dataclass


@dataclass(kw_only=True)
class YoloConfig:
    model: str = "foduucom/table-detection-and-extraction"
    device: str = "cpu"
    confidence_threshold: float = 0.7
    iou_threshold = 0.3
    agnostic_nms = False
    max_detection_objects = 50


class YoloDetector:
    def __init__(self, cfg: YoloConfig = YoloConfig()):
        self.cfg = cfg

        self.model = YOLO(self.cfg.model)
        self.model.overrides["conf"] = self.cfg.confidence_threshold
        self.model.overrides["iou"] = self.cfg.iou_threshold
        self.model.overrides["agnostic_nms"] = self.cfg.agnostic_nms
        self.model.overrides["max_det"] = self.cfg.max_detection_objects
        self.model.to(self.cfg.device)

    def detect(self, image: Image.Image):
        return self.model.predict(image)[0]

    @staticmethod
    def get_max_area_bbox(yolo_result) -> np.ndarray:
        """Returns cxcywh int, int, int, int"""
        return max(yolo_result.boxes.xywh, key=lambda x: x[2] * x[3]).cpu().numpy()
