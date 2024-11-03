import math
from typing import Union, Tuple

import numpy as np
import cv2
from deskew import determine_skew
from PIL import Image


def rotate(
        image: np.ndarray,
        angle: float,
        background: Union[int, Tuple[int, int, int]]
) -> np.ndarray:
    old_width, old_height = image.shape[:2]
    angle_radian = math.radians(angle)
    width = abs(np.sin(angle_radian) * old_height) + abs(np.cos(angle_radian) * old_width)
    height = abs(np.sin(angle_radian) * old_width) + abs(np.cos(angle_radian) * old_height)

    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    rot_mat[1, 2] += (width - old_width) / 2
    rot_mat[0, 2] += (height - old_height) / 2
    return cv2.warpAffine(image, rot_mat, (int(round(height)), int(round(width))),
                          borderValue=background)


def deskew(image: np.ndarray) -> np.ndarray:
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    angle = determine_skew(grayscale)
    rotated = rotate(image, angle, 255)
    return rotated


def deskew_pil(image: Image.Image) -> Image.Image:
    array = np.array(image)
    deskewed_array = deskew(array)
    return Image.fromarray(deskewed_array)
