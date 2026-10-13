from __future__ import annotations

from dataclasses import dataclass
from math import ceil, radians, sin
from typing import Sequence

import cv2
import numpy as np

from config.settings import LEAF_COUNT, LEAF_TILT_DEGREES
from src.encoder import angle_for_bit
from src.leaf_selector import PlantLayers


@dataclass(frozen=True)
class PreparedLeaf:
    leaf_id: int
    premultiplied_crop: np.ndarray
    crop_origin: tuple[int, int]
    destination_bounds: tuple[int, int, int, int]
    pivot: tuple[float, float]


@dataclass(frozen=True)
class PlantRenderer:
    background: np.ndarray
    leaves: tuple[PreparedLeaf, ...]
    margin: int

    @property
    def width(self) -> int:
        return self.background.shape[1]

    @property
    def height(self) -> int:
        return self.background.shape[0]


def _premultiply(image: np.ndarray) -> np.ndarray:
    rgba = image.astype(np.float32) / 255.0
    rgba[:, :, :3] *= rgba[:, :, 3:4]
    return rgba


def prepare_plant_renderer(plant: PlantLayers) -> PlantRenderer:
    if len(plant.leaves) != LEAF_COUNT:
        raise ValueError(f"Exactly {LEAF_COUNT} leaf layers are required.")

    margin = plant.margin
    stem_height, stem_width = plant.stem.shape[:2]
    canvas = np.zeros((plant.height, plant.width, 4), dtype=np.float32)
    canvas[margin : margin + stem_height, margin : margin + stem_width] = _premultiply(plant.stem)

    stem_points = cv2.findNonZero(plant.stem[:, :, 3])
    if stem_points is None:
        raise ValueError("The stem layer has no visible pixels.")
    stem_x, stem_y, stem_w, stem_h = cv2.boundingRect(stem_points)
    content_left = stem_x + margin
    content_top = stem_y + margin
    content_right = stem_x + stem_w + margin
    content_bottom = stem_y + stem_h + margin
    leaf_sources = []
    for leaf in plant.leaves:
        points = cv2.findNonZero(leaf.image[:, :, 3])
        if points is None:
            raise ValueError(f"Leaf {leaf.leaf_id} has no visible pixels.")

        x, y, width, height = cv2.boundingRect(points)
        corners = (
            (x, y),
            (x + width, y),
            (x, y + height),
            (x + width, y + height),
        )
        max_radius = max(
            np.hypot(corner[0] - leaf.pivot[0], corner[1] - leaf.pivot[1])
            for corner in corners
        )
        padding = ceil(max_radius * sin(radians(LEAF_TILT_DEGREES)) + 3)
        crop_left = max(0, x - padding)
        crop_top = max(0, y - padding)
        crop_right = min(leaf.image.shape[1], x + width + padding)
        crop_bottom = min(leaf.image.shape[0], y + height + padding)
        crop = leaf.image[crop_top:crop_bottom, crop_left:crop_right]

        destination_left = max(0, x - padding) + margin
        destination_top = max(0, y - padding) + margin
        destination_right = min(leaf.image.shape[1], x + width + padding) + margin
        destination_bottom = min(leaf.image.shape[0], y + height + padding) + margin
        content_left = min(content_left, destination_left)
        content_top = min(content_top, destination_top)
        content_right = max(content_right, destination_right)
        content_bottom = max(content_bottom, destination_bottom)
        leaf_sources.append(
            (
                leaf,
                _premultiply(crop),
                (crop_left, crop_top),
                (destination_left, destination_top, destination_right, destination_bottom),
            )
        )

    output_left = max(0, content_left - margin)
    output_top = max(0, content_top - margin)
    output_right = min(plant.width, content_right + margin)
    output_bottom = min(plant.height, content_bottom + margin)
    prepared_leaves = []
    for leaf, premultiplied_crop, crop_origin, bounds in leaf_sources:
        left, top, right, bottom = bounds
        prepared_leaves.append(
            PreparedLeaf(
                leaf_id=leaf.leaf_id,
                premultiplied_crop=premultiplied_crop,
                crop_origin=(crop_origin[0] - output_left, crop_origin[1] - output_top),
                destination_bounds=(
                    left - output_left,
                    top - output_top,
                    right - output_left,
                    bottom - output_top,
                ),
                pivot=(
                    leaf.pivot[0] + margin - output_left,
                    leaf.pivot[1] + margin - output_top,
                ),
            )
        )

    cropped_background = canvas[output_top:output_bottom, output_left:output_right].copy()
    return PlantRenderer(cropped_background, tuple(prepared_leaves), margin)


def _blend_over(destination: np.ndarray, source: np.ndarray) -> np.ndarray:
    source_alpha = source[:, :, 3:4]
    destination[:, :, :3] = source[:, :, :3] + destination[:, :, :3] * (1.0 - source_alpha)
    destination[:, :, 3:4] = source_alpha + destination[:, :, 3:4] * (1.0 - source_alpha)
    return destination


def _warp_prepared_leaf(
    renderer: PlantRenderer,
    leaf: PreparedLeaf,
    angle: float,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    left, top, right, bottom = leaf.destination_bounds
    matrix = cv2.getRotationMatrix2D(leaf.pivot, float(angle), 1.0)
    crop_origin = np.array(
        [
            leaf.crop_origin[0] + renderer.margin,
            leaf.crop_origin[1] + renderer.margin,
        ],
        dtype=np.float64,
    )
    matrix[:, 2] += matrix[:, :2] @ crop_origin
    matrix[0, 2] -= left
    matrix[1, 2] -= top
    warped = cv2.warpAffine(
        leaf.premultiplied_crop,
        matrix,
        (right - left, bottom - top),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    alpha = np.clip(warped[:, :, 3:4], 0.0, 1.0)
    warped[:, :, :3] = np.clip(warped[:, :, :3], 0.0, alpha)
    warped[:, :, 3:4] = alpha
    return warped, (left, top, right, bottom)


def render_plant_frame(renderer: PlantRenderer, angles: Sequence[float]) -> np.ndarray:
    if len(renderer.leaves) != LEAF_COUNT or len(angles) != LEAF_COUNT:
        raise ValueError(f"Exactly {LEAF_COUNT} angles and leaf layers are required for one frame.")
    if any(abs(float(angle)) > LEAF_TILT_DEGREES for angle in angles):
        raise ValueError(f"Leaf angles cannot exceed {LEAF_TILT_DEGREES} degrees.")

    canvas = renderer.background.copy()
    for leaf, angle in zip(renderer.leaves, angles):
        warped, (left, top, right, bottom) = _warp_prepared_leaf(renderer, leaf, angle)
        region = canvas[top:bottom, left:right]
        canvas[top:bottom, left:right] = _blend_over(region, warped)

    bgr = canvas[:, :, :3] + (1.0 - canvas[:, :, 3:4])
    return (np.clip(bgr, 0.0, 1.0) * 255.0).round().astype(np.uint8)


def angles_for_bits(bits: Sequence[int]) -> list[float]:
    if len(bits) != LEAF_COUNT:
        raise ValueError(f"Exactly {LEAF_COUNT} bits are required for one frame.")
    if any(bit not in (0, 1) for bit in bits):
        raise ValueError("Binary input may contain only 0 and 1.")
    return [angle_for_bit(bit) for bit in bits]
