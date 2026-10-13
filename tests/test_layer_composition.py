import unittest

import numpy as np

from config.settings import LEAF_TILT_DEGREES
from src.encoder import angle_for_bit
from src.leaf_selector import load_plant_layers
from src.leaf_transform import (
    _warp_prepared_leaf,
    angles_for_bits,
    prepare_plant_renderer,
    render_plant_frame,
)


class LayerCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layers = load_plant_layers()
        cls.renderer = prepare_plant_renderer(cls.layers)
        cls.neutral = render_plant_frame(cls.renderer, [0.0] * 8)
        cls.original_layers = [cls.layers.stem.copy()] + [
            leaf.image.copy() for leaf in cls.layers.leaves
        ]

    def test_bit_directions(self):
        self.assertEqual(angle_for_bit(0), LEAF_TILT_DEGREES)
        self.assertEqual(angle_for_bit(1), -LEAF_TILT_DEGREES)

    def test_all_byte_values_keep_junctions_and_avoid_leaf_overlap(self):
        for value in range(256):
            bits = [(value >> shift) & 1 for shift in range(7, -1, -1)]
            angles = angles_for_bits(bits)
            frame = render_plant_frame(self.renderer, angles)

            self.assertEqual(
                frame.shape,
                (*self.renderer.background.shape[:2], 3),
            )
            self.assertTrue(np.all(frame[0] == 255), f"Top margin cropped for byte {value}.")
            self.assertTrue(np.all(frame[-1] == 255), f"Bottom margin cropped for byte {value}.")
            self.assertTrue(np.all(frame[:, 0] == 255), f"Left margin cropped for byte {value}.")
            self.assertTrue(np.all(frame[:, -1] == 255), f"Right margin cropped for byte {value}.")

            occupancies = []
            for leaf, angle in zip(self.renderer.leaves, angles):
                px, py = map(lambda coordinate: int(round(coordinate)), leaf.pivot)
                np.testing.assert_array_equal(
                    frame[py, px],
                    self.neutral[py, px],
                    err_msg=f"Leaf {leaf.leaf_id} attachment pixel changed for byte {value}.",
                )
                alpha, bounds = _warp_prepared_leaf(self.renderer, leaf, angle)
                left, top, right, bottom = bounds
                occupancies.append((left, top, right, bottom, alpha[:, :, 3] > 0.5))

            for index, (left_a, top_a, right_a, bottom_a, mask_a) in enumerate(occupancies):
                for left_b, top_b, right_b, bottom_b, mask_b in occupancies[index + 1 :]:
                    left = max(left_a, left_b)
                    top = max(top_a, top_b)
                    right = min(right_a, right_b)
                    bottom = min(bottom_a, bottom_b)
                    if left >= right or top >= bottom:
                        continue
                    overlap = np.count_nonzero(
                        mask_a[top - top_a : bottom - top_a, left - left_a : right - left_a]
                        & mask_b[top - top_b : bottom - top_b, left - left_b : right - left_b]
                    )
                    self.assertEqual(overlap, 0, f"Leaves overlap in byte value {value}.")

        np.testing.assert_array_equal(self.layers.stem, self.original_layers[0])
        for leaf, original in zip(self.layers.leaves, self.original_layers[1:]):
            np.testing.assert_array_equal(leaf.image, original)


if __name__ == "__main__":
    unittest.main()
