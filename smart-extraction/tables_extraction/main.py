import pandas as pd
import torch
from tables_extraction.models import YoloDetector, YoloConfig, TatrExtractor, TatrConfig
from tables_extraction.processing import ImageProcessor as Processor, Ocr, OcrConfig

from tables_extraction.processing.deskewer import deskew_pil


def extract_tables(pdf_path: str) -> list[pd.DataFrame | None]:
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

    texts = []
    table_dfs = []

    for page in pages:
        try:
            page = deskew_pil(page)
            detection_result = detection_model.detect(page)
            if len(detection_result) == 0:
                table_dfs.append(None)
                texts.append(None)
                continue
            bbox = detection_model.get_max_area_bbox(detection_result)

            layout = Processor.cxcywh2xyxy(bbox)
            layout = Processor.xyxy_add_margin(layout, margin=[20, -5, 20, 20])
            table_image = page.crop(layout)

            objects = TatrExtractor.outputs_to_objects(
                extraction_model.extract(table_image),
                table_image.size,
                extraction_model.id2label,
            )
            if len(objects) == 0:
                table_dfs.append(None)
                texts.append(None)
                continue
            coordinates = extraction_model.get_object_coordinates(objects)

            outputs = ocr_runtime.run_on_coordinates(table_image, coordinates)
            data = ocr_runtime.merge_data(outputs)

            table_dfs.append(pd.DataFrame(data))
            texts.append(ocr_runtime.run_on_whole_page(page))

        except Exception as e:
            print(e)
            table_dfs.append(None)
            texts.append(None)

    return table_dfs, texts
