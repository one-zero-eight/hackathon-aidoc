from PIL import Image
import numpy as np
import pdf2image
import torch


class ImageProcessor:
    @staticmethod
    def pdf_path_pages(pdf_path: str) -> list[Image.Image]:
        return pdf2image.convert_from_path(pdf_path)

    @staticmethod
    def pdf_bytes_pages(pdf_bytes: bytes) -> list[Image.Image]:
        return pdf2image.convert_from_bytes(pdf_bytes)

    @staticmethod
    def cxcywh2xywh(bbox):
        return bbox[0] - bbox[2] / 2, bbox[1] - bbox[3] / 2, bbox[2], bbox[3]

    @staticmethod
    def xywh2xyxy(bbox):
        return bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]

    @staticmethod
    def cxcywh2xyxy(bbox):
        return (
            bbox[0] - bbox[2] / 2,
            bbox[1] - bbox[3] / 2,
            bbox[0] + bbox[2] / 2,
            bbox[1] + bbox[3] / 2,
        )

    @staticmethod
    def xyxy_add_margin(bbox, margin: int | list):
        if isinstance(margin, int):
            return (
                bbox[0] - margin,
                bbox[1] - margin,
                bbox[2] + margin,
                bbox[3] + margin,
            )

        return (
            bbox[0] - margin[0],
            bbox[1] - margin[1],
            bbox[2] + margin[0],
            bbox[3] + margin[1],
        )

    @staticmethod
    def add_padding(pil_image: Image, padding: int | list, color: int = 255) -> Image:
        if isinstance(padding, int):
            padding = [padding, padding, padding, padding]

        original_image = np.array(pil_image)

        new_image = (
            np.ones(
                (
                    original_image.shape[0] + padding[0] + padding[2],
                    original_image.shape[1] + padding[1] + padding[3],
                    original_image.shape[2],
                ),
            )
            * color
        )
        # put original image in the center
        new_image[
            padding[0] : -padding[2], padding[1] : -padding[3], :
        ] = original_image

        return Image.fromarray(new_image)

    @staticmethod
    def torch_box_cxcywh_to_xyxy(bbox):
        # todo: should be merged with cxcywh2xyxy
        x_c, y_c, w, h = bbox.unbind(-1)
        b = [(x_c - 0.5 * w), (y_c - 0.5 * h), (x_c + 0.5 * w), (y_c + 0.5 * h)]
        return torch.stack(b, dim=1)

    @staticmethod
    def rescale_torch_box(bbox: torch.Tensor, size: tuple[int, int]):
        img_w, img_h = size
        b = ImageProcessor.torch_box_cxcywh_to_xyxy(bbox)
        b = b * torch.tensor([img_w, img_h, img_w, img_h], dtype=torch.float32)
        return b
