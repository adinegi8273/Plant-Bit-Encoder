from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import AES_KEY_PATH, DEBUG_IMAGE_PATH, ENCRYPTED_PAYLOAD_PATH, OUTPUT_DIR, VIDEO_OUTPUT_PATH
from src.encoder import bits_to_byte_groups, bytes_to_bits, encrypt_text
from src.leaf_selector import load_plant_layers
from src.leaf_transform import prepare_plant_renderer
from src.video_generator import (
    generate_debug_image,
    generate_all_leaf_test_images,
    generate_encoded_video,
    generate_single_leaf_test_images,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Encode text into rotating plant leaves.")
    parser.add_argument("text", nargs="?", default="HELLO", help="The text string to encode into the plant animation.")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    layers = load_plant_layers()
    plant = prepare_plant_renderer(layers)
    generate_debug_image(plant, DEBUG_IMAGE_PATH)
    generate_single_leaf_test_images(plant)
    generate_all_leaf_test_images(plant)

    key, nonce, ciphertext = encrypt_text(args.text)
    encrypted_payload = nonce + ciphertext
    AES_KEY_PATH.write_bytes(key)
    ENCRYPTED_PAYLOAD_PATH.write_bytes(encrypted_payload)

    bits = bytes_to_bits(encrypted_payload)
    groups = bits_to_byte_groups(bits, group_size=8)
    generate_encoded_video(plant, groups, VIDEO_OUTPUT_PATH)

    print(f"Loaded stem and {len(plant.leaves)} leaf layers from plant_layers.")
    print(f"Saved debug visualization: {DEBUG_IMAGE_PATH}")
    print(f"Saved single-leaf tests: {OUTPUT_DIR / 'test_leaf_left.png'} and {OUTPUT_DIR / 'test_leaf_right.png'}")
    print(f"Encrypted {len(args.text.encode('utf-8'))} plaintext bytes with AES-256-GCM.")
    print(f"Saved AES key: {AES_KEY_PATH}")
    print(f"Saved nonce + ciphertext + authentication tag: {ENCRYPTED_PAYLOAD_PATH}")
    print(f"Video contains {len(groups)} encrypted-byte states at 1 second per byte.")
    print(f"Saved final video: {VIDEO_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
