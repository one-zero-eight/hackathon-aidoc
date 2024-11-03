from tables_extraction.processing import ImageProcessor
from transformers import TableTransformerForObjectDetection
from PIL import Image
from dataclasses import dataclass
from torchvision import transforms


class MaxResize(object):
    def __init__(self, max_size=800):
        self.max_size = max_size

    def __call__(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        current_max_size = max(width, height)
        scale = self.max_size / current_max_size
        resized_image = image.resize(
            (int(round(scale * width)), int(round(scale * height)))
        )

        return resized_image


@dataclass
class TatrConfig:
    device: str = "cpu"
    model: str = "microsoft/table-structure-recognition-v1.1-all"
    image_size: int = 1000
    confidence_threshold = 0.85


class TatrExtractor:
    def __init__(self, cfg: TatrConfig = TatrConfig()):
        self.cfg = cfg
        self.model = TableTransformerForObjectDetection.from_pretrained(self.cfg.model)
        self.model.to(self.cfg.device)

        self.id2label = self.model.config.id2label.copy()
        self.id2label[len(self.id2label)] = "no object"

        self.transforms = transforms.Compose(
            [
                MaxResize(max_size=self.cfg.image_size),
                transforms.ToTensor(),
            ]
        )

    def extract(self, image: Image.Image):
        return self.model(self.transforms(image).unsqueeze(0).to(self.cfg.device))

    @staticmethod
    def outputs_to_objects(outputs, img_size, id2label) -> list[dict]:
        m = outputs.logits.softmax(-1).max(-1)
        pred_labels = list(m.indices.detach().cpu().numpy())[0]
        pred_scores = list(m.values.detach().cpu().numpy())[0]
        pred_bboxes = outputs["pred_boxes"].detach().cpu()[0]
        pred_bboxes = [
            elem.tolist()
            for elem in ImageProcessor.rescale_torch_box(pred_bboxes, img_size)
        ]

        objects = []
        for label, score, bbox in zip(pred_labels, pred_scores, pred_bboxes):
            class_label = id2label[int(label)]
            if not class_label == "no object":
                objects.append(
                    {
                        "label": class_label,
                        "score": float(score),
                        "bbox": [float(elem) for elem in bbox],
                    }
                )

        filtered_objects = []
        for obj in objects:
            if obj["score"] < 0.85:
                continue

            filtered_objects.append(obj)

        return filtered_objects

    @staticmethod
    def to_object_coordinates(row, column):
        cell_bbox = [
            column["bbox"][0],
            row["bbox"][1],
            column["bbox"][2],
            row["bbox"][3],
        ]
        return cell_bbox

    @staticmethod
    def get_object_coordinates(objects: list[dict]) -> list[dict]:
        rows = [entry for entry in objects if entry["label"] == "table row"]
        columns = [entry for entry in objects if entry["label"] == "table column"]

        rows.sort(key=lambda x: x["bbox"][1])
        columns.sort(key=lambda x: x["bbox"][0])

        # Generate cell coordinates and count cells in each row
        coordinates = []

        for row in rows:
            row_cells = []
            for column in columns:
                cell_bbox = TatrExtractor.to_object_coordinates(row, column)
                row_cells.append({"column": column["bbox"], "cell": cell_bbox})

            # Sort cells in the row by X coordinate
            row_cells.sort(key=lambda x: x["column"][0])

            # Append row information to cell_coordinates
            coordinates.append(
                {
                    "row": row["bbox"],
                    "score": row["score"],
                    "cells": row_cells,
                    "cell_count": len(row_cells),
                },
            )

        coordinates.sort(key=lambda x: x["row"][1])

        return coordinates
