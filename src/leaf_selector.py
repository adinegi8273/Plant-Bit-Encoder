from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from config.settings import CANVAS_MARGIN, LEAF_COUNT, LEAVES_JSON_PATH, STEM_LAYER_PATH


@dataclass(frozen=True)
class LeafLayer:
    leaf_id: int
    name: str
    image: np.ndarray
    pivot: tuple[float, float]


@dataclass(frozen=True)
class PlantLayers:
    stem: np.ndarray
    leaves: tuple[LeafLayer, ...]
    margin: int

    @property
    def width(self) -> int:
        return self.stem.shape[1] + 2 * self.margin

    @property
    def height(self) -> int:
        return self.stem.shape[0] + 2 * self.margin


def _load_rgba_layer(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Unable to load transparent plant layer: {path}")
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Plant layer must be a 4-channel PNG with alpha: {path}")
    return image


def load_plant_layers(
    leaves_json_path: Path = LEAVES_JSON_PATH,
    stem_layer_path: Path = STEM_LAYER_PATH,
    margin: int = CANVAS_MARGIN,
) -> PlantLayers:
    if margin < 0:
        raise ValueError("Canvas margin cannot be negative.")
    if not leaves_json_path.is_file():
        raise FileNotFoundError(f"Leaf metadata file was not found: {leaves_json_path}")

    try:
        metadata = json.loads(leaves_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Leaf metadata is not valid JSON: {leaves_json_path}") from error
    if not isinstance(metadata, list) or len(metadata) != LEAF_COUNT:
        raise ValueError(f"{leaves_json_path} must contain exactly {LEAF_COUNT} leaf records.")

    stem = _load_rgba_layer(stem_layer_path)
    leaves = []
    seen_ids = set()
    for entry in metadata:
        try:
            leaf_id = int(entry["id"])
            file_name = str(entry["file"])
            name = str(entry["name"])
            pivot_values = entry["pivot"]
            pivot = (float(pivot_values[0]), float(pivot_values[1]))
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise ValueError(f"Invalid leaf record in {leaves_json_path}: {entry!r}") from error

        layer_path = (leaves_json_path.parent / file_name).resolve()
        if layer_path.parent != leaves_json_path.parent.resolve():
            raise ValueError(f"Leaf layer path must be inside {leaves_json_path.parent}: {file_name}")
        if leaf_id in seen_ids or not 1 <= leaf_id <= LEAF_COUNT:
            raise ValueError(f"Duplicate or invalid leaf ID in {leaves_json_path}: {leaf_id}")
        seen_ids.add(leaf_id)

        image = _load_rgba_layer(layer_path)
        if image.shape != stem.shape:
            raise ValueError(f"Leaf layer dimensions must match stem.png: {layer_path}")
        if not np.isfinite(pivot).all() or not (0 <= pivot[0] < stem.shape[1] and 0 <= pivot[1] < stem.shape[0]):
            raise ValueError(f"Pivot for leaf {leaf_id} is outside the layer canvas: {pivot}")

        leaves.append(LeafLayer(leaf_id, name, image, pivot))

    leaves.sort(key=lambda leaf: leaf.leaf_id)
    return PlantLayers(stem, tuple(leaves), margin)
