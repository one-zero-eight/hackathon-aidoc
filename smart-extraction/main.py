import pandas as pd
import torch
from models import YoloDetector, YoloConfig, TatrExtractor, TatrConfig
from processing import ImageProcessor as Processor, Ocr, OcrConfig


def main(pdf_path: str) -> list[pd.DataFrame | None]:
    device = "cuda" if torch.cuda.is_available() else "cpu"

    pages = Processor.pdf_path_pages(pdf_path)
    detection_model = YoloDetector(
        YoloConfig(device=device),
    )
    extraction_model = TatrExtractor(
        TatrConfig(device=device),
    )
    ocr_runtime = Ocr(
        OcrConfig(language="ru"),
    )

    results = []

    for page in pages:
        try:
            detection_result = detection_model.detect(page)
            bbox = detection_model.get_max_area_bbox(detection_result)

            layout = Processor.cxcywh2xyxy(bbox)
            layout = Processor.xyxy_add_margin(layout, margin=[20, -5, 20, 20])
            table_image = page.crop(layout)

            objects = TatrExtractor.outputs_to_objects(
                extraction_model.extract(table_image),
                table_image.size,
                extraction_model.id2label,
            )
            coordinates = extraction_model.get_object_coordinates(objects)

            outputs = ocr_runtime.run_on_coordinates(table_image, coordinates)
            data = ocr_runtime.merge_data(outputs)

            results.append(pd.DataFrame(data))

        except Exception as e:
            print(e)
            results.append(None)

    return results
