from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_IMAGE_PATH = ROOT_DIR / "input" / "plant.png"
OUTPUT_DIR = ROOT_DIR / "output"
LAYERS_DIR = ROOT_DIR / "plant_layers"
LEAVES_JSON_PATH = LAYERS_DIR / "leaves.json"
STEM_LAYER_PATH = LAYERS_DIR / "stem.png"
DEBUG_IMAGE_PATH = OUTPUT_DIR / "debug_leaves.png"
TEST_LEFT_PATH = OUTPUT_DIR / "test_leaf_left.png"
TEST_RIGHT_PATH = OUTPUT_DIR / "test_leaf_right.png"
TEST_ALL_COUNTERCLOCKWISE_PATH = OUTPUT_DIR / "test_all_counterclockwise.png"
TEST_ALL_CLOCKWISE_PATH = OUTPUT_DIR / "test_all_clockwise.png"
VIDEO_OUTPUT_PATH = OUTPUT_DIR / "encoded_plant.avi"
AES_KEY_PATH = OUTPUT_DIR / "encryption_key.bin"
ENCRYPTED_PAYLOAD_PATH = OUTPUT_DIR / "encrypted_payload.bin"

LEAF_COUNT = 8
LEAF_TILT_DEGREES = 8
CANVAS_MARGIN = 32
FPS = 24
FRAMES_PER_TRANSITION = 8
RESET_FRAMES = 8
HOLD_FRAMES = 8
DEBUG_MODE = True
VIDEO_FOURCC = "FFV1"
