# Plant Bit Encoder

This beginner-friendly prototype encrypts text, converts the encrypted bytes to
bits, and represents each group of 8 bits with the movement of 8 illustrated
plant leaves. It uses pre-separated transparent image layers so that the leaves
can turn at their attachment points without erasing or repainting the stem.

For the complete explanation of the design, rendering steps, files, validation,
timing, and limitations, see the [Project Guide](docs/PROJECT_GUIDE.md).

## Quick start

Run these commands from the project folder:

```powershell
python -m pip install -r requirements.txt
python src/main.py "HELLO"
```

If no text is supplied, the program encodes `HELLO`:

```powershell
python src/main.py
```

The final video is `output/encoded_plant.avi`. It uses FFV1 lossless
compression. Keep `output/encryption_key.bin` private and save it alongside
`output/encrypted_payload.bin` if you need to decrypt the payload later.

## Main outputs

| File | What it contains |
| --- | --- |
| `output/encoded_plant.avi` | Lossless 24 FPS animation; each encrypted byte occupies one second |
| `output/encryption_key.bin` | Random 32-byte AES-256 key for this run |
| `output/encrypted_payload.bin` | 12-byte AES-GCM nonce followed by ciphertext and its authentication tag |
| `output/debug_leaves.png` | Neutral plant with the eight JSON pivots marked |
| `output/test_all_counterclockwise.png` | All eight leaves tilted counter-clockwise |
| `output/test_all_clockwise.png` | All eight leaves tilted clockwise |
| `output/test_leaf_left.png`, `output/test_leaf_right.png` | One-leaf movement previews |
| `output/leaf_1_left.png` through `output/leaf_8_right.png` | Individual leaf movement previews |

The code architecture and the meaning of the configuration options are
documented in the [Project Guide](docs/PROJECT_GUIDE.md).
