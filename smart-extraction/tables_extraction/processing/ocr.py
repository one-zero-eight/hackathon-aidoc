import easyocr
from PIL import Image
from dataclasses import dataclass

import numpy as np


@dataclass
class OcrConfig:
    language: str = "ru"


class Ocr:
    def __init__(self, cfg: OcrConfig = OcrConfig()):
        self.cfg = cfg
        self.reader = easyocr.Reader([self.cfg.language])

    def run_on_coordinates(self, image: Image.Image, coordinates: list[dict]):
        data = dict()
        max_num_columns = 0
        for idx, row in enumerate(coordinates):
            row_text = []
            for cell in row["cells"]:
                cell_image = np.array(image.crop(cell["cell"]))

                result = self.reader.readtext(np.array(cell_image))
                if len(result) > 0:
                    text = " ".join([x[1] for x in result])
                    row_text.append(text)
                else:
                    row_text.append("")

            if len(row_text) > max_num_columns:
                max_num_columns = len(row_text)

            data[idx] = row_text

        for row, row_data in data.copy().items():
            if len(row_data) != max_num_columns:
                row_data = row_data + [
                    "" for _ in range(max_num_columns - len(row_data))
                ]
            data[row] = row_data

        return [data[i] for i in range(0, len(data))]

    def run_on_whole_page(self, image: Image.Image) -> str:
        return "\n".join(
            [
                result
                for result in
                self.reader.readtext(np.array(image), paragraph=True, detail=0)
            ]

        )

    @staticmethod
    def merge_data(data):
        new_data = [data[0]]

        for i in range(1, len(data)):
            prev_empty = all(x.strip() == "" for x in new_data[-1][1:])
            this_empty = all(x.strip() == "" for x in data[i][1:])
            if (
                prev_empty
                and not this_empty
                and data[i][0].strip() != ""
                and data[i][0].strip()[0].islower()
            ):
                prev = new_data.pop(-1)
                new_data.append([prev[0] + " " + data[i][0]] + data[i][1:])
            else:
                new_data.append(data[i])

        return new_data
