from __future__ import annotations

from pathlib import Path
from typing import List

import cv2

from config.settings import (
    FPS,
    FRAMES_PER_TRANSITION,
    HOLD_FRAMES,
    LEAF_TILT_DEGREES,
    OUTPUT_DIR,
    RESET_FRAMES,
    TEST_ALL_CLOCKWISE_PATH,
    TEST_ALL_COUNTERCLOCKWISE_PATH,
    TEST_LEFT_PATH,
    TEST_RIGHT_PATH,
    VIDEO_FOURCC,
    VIDEO_OUTPUT_PATH,
)
from src.encoder import angle_for_bit
from src.leaf_transform import PlantRenderer, render_plant_frame


def generate_single_leaf_test_images(plant: PlantRenderer) -> None:
    if not plant.leaves:
        raise ValueError("At least one leaf layer is needed for movement tests.")

    for path, angle in (
        (TEST_LEFT_PATH, LEAF_TILT_DEGREES),
        (TEST_RIGHT_PATH, -LEAF_TILT_DEGREES),
    ):
        angles = [0.0] * len(plant.leaves)
        angles[0] = angle
        if not cv2.imwrite(str(path), render_plant_frame(plant, angles)):
            raise IOError(f"Unable to save leaf movement test image: {path}")

    for path, angle in (
        (TEST_ALL_COUNTERCLOCKWISE_PATH, LEAF_TILT_DEGREES),
        (TEST_ALL_CLOCKWISE_PATH, -LEAF_TILT_DEGREES),
    ):
        angles = [angle] * len(plant.leaves)
        if not cv2.imwrite(str(path), render_plant_frame(plant, angles)):
            raise IOError(f"Unable to save all-leaf direction preview: {path}")


def generate_all_leaf_test_images(plant: PlantRenderer) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for index, leaf in enumerate(plant.leaves):
        for direction, angle in (
            ("left", LEAF_TILT_DEGREES),
            ("right", -LEAF_TILT_DEGREES),
        ):
            angles = [0.0] * len(plant.leaves)
            angles[index] = angle
            path = OUTPUT_DIR / f"leaf_{index + 1}_{direction}.png"
            if not cv2.imwrite(str(path), render_plant_frame(plant, angles)):
                raise IOError(f"Unable to save leaf movement test image: {path}")


def generate_debug_image(plant: PlantRenderer, output_path) -> None:
    image = render_plant_frame(plant, [0.0] * len(plant.leaves))
    for leaf in plant.leaves:
        x = int(round(leaf.pivot[0]))
        y = int(round(leaf.pivot[1]))
        cv2.circle(image, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(
            image,
            f"Leaf {leaf.leaf_id}",
            (x + 7, y - 7),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )
    if not cv2.imwrite(str(output_path), image):
        raise IOError(f"Unable to save leaf pivot visualization: {output_path}")


def generate_encoded_video(
    plant: PlantRenderer,
    bit_groups: List[List[int]],
    output_path=VIDEO_OUTPUT_PATH,
):
    if len(plant.leaves) != 8:
        raise ValueError(f"Exactly 8 leaves are required for byte animation; received {len(plant.leaves)}.")
    if not bit_groups:
        raise ValueError("There are no 8-bit groups to encode.")
    if any(len(group) != 8 for group in bit_groups):
        raise ValueError("Every video state must contain exactly 8 bits, one for each leaf.")
    if FRAMES_PER_TRANSITION <= 0 or RESET_FRAMES <= 0 or HOLD_FRAMES < 0:
        raise ValueError("Transition/reset frames must be positive and hold frames cannot be negative.")
    if FRAMES_PER_TRANSITION + RESET_FRAMES + HOLD_FRAMES != FPS:
        raise ValueError(
            "FRAMES_PER_TRANSITION + RESET_FRAMES + HOLD_FRAMES must equal FPS "
            "so each encrypted byte lasts exactly one second."
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*VIDEO_FOURCC),
        FPS,
        (plant.width, plant.height),
    )
    if not writer.isOpened():
        raise IOError(f"Video writer could not initialize lossless {VIDEO_FOURCC} output at {output_path}.")

    current_angles = [0.0] * len(plant.leaves)
    has_previous_state = False
    try:
        for group in bit_groups:
            target_angles = [angle_for_bit(bit) for bit in group]
            reset_frames = RESET_FRAMES if has_previous_state else 0
            transition_frames = FPS - reset_frames - HOLD_FRAMES

            for frame_index in range(1, reset_frames + 1):
                progress = frame_index / reset_frames
                smooth_progress = progress * progress * (3.0 - 2.0 * progress)
                reset_angles = [
                    angle * (1.0 - smooth_progress)
                    for angle in current_angles
                ]
                writer.write(render_plant_frame(plant, reset_angles))

            for frame_index in range(1, transition_frames + 1):
                progress = frame_index / transition_frames
                smooth_progress = progress * progress * (3.0 - 2.0 * progress)
                transition_angles = [
                    angle * smooth_progress
                    for angle in target_angles
                ]
                writer.write(render_plant_frame(plant, transition_angles))

            for _ in range(HOLD_FRAMES):
                writer.write(render_plant_frame(plant, target_angles))

            current_angles = target_angles
            has_previous_state = True
    finally:
        writer.release()
    return output_path
