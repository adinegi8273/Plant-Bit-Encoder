# Plant Bit Encoder: Project Guide

## 1. What the project does

This prototype encodes text in a short animation of a 2D plant illustration:

```text
text
  -> UTF-8 bytes
  -> AES-256-GCM encryption
  -> encrypted bytes and bits
  -> groups of 8 bits
  -> one direction per leaf
  -> rendered frames
  -> lossless video
```

There are exactly eight leaves. Each leaf represents one bit, so all eight
leaves together represent one byte in a frame state. A bit is shown by the
direction of that leaf's small rotation.

This is image processing and 2D affine geometry. It does not use Blender, 3D
models, physical simulation, or machine learning.

## 2. Technologies used

- **Python** runs the program and connects the steps.
- **OpenCV (`opencv-python`)** loads PNG layers, rotates them with affine
  transforms, composites images, and writes video.
- **NumPy** performs pixel and alpha-channel calculations.
- **cryptography** provides authenticated AES-256-GCM encryption.
- **FFV1** is the lossless video codec used inside an AVI container. Lossless
  frames preserve the small angles more faithfully than typical MP4 compression.

Install the dependencies from the project root:

```powershell
python -m pip install -r requirements.txt
```

`requirements.txt` contains `opencv-python`, `numpy`, and `cryptography`.

## 3. Why the project uses separate image layers

The earlier renderer tried to select green pixels from a flattened plant image,
erase them, fill the erased areas with inpainting, and paste rotated pixels back.
Because each leaf touches its stalk, the selection could include part of the
stalk. Erasing and filling that area caused the visible cuts and gaps.

The current renderer does not cut anything out of a flattened image. It builds
each frame from the prepared artwork:

1. Draw the transparent stem-and-stalk layer as the fixed background.
2. Rotate each transparent leaf layer around its attachment pivot.
3. Alpha-composite the rotated leaves over the stem.
4. Place the result on white.

The stem/stalk pixels come directly from the supplied stem layer and are never
rotated, erased, or inpainted. Each leaf is transformed from its supplied layer
for every frame; a previous frame is never used as the next frame's source.

## 4. Plant layer files

All required source layers are in `plant_layers/`:

```text
plant_layers/
    stem.png
    leaves.json
    leaf_1_top_left.png
    leaf_2_top_right.png
    leaf_3_mid_left.png
    leaf_4_mid_right.png
    leaf_5_low_left.png
    leaf_6_low_right.png
    leaf_7_bottom_left.png
    leaf_8_bottom_right.png
```

Each PNG is a four-channel BGRA image with transparency and uses the same source
canvas dimensions. `stem.png` contains the main stem and all stalks, without the
leaf blades. Each leaf PNG contains one leaf on a transparent background.

`leaves.json` supplies each leaf's ID, name, image filename, and pivot:

```json
{
  "id": 1,
  "name": "top_left",
  "file": "leaf_1_top_left.png",
  "pivot": [540.0, 195.0]
}
```

The pivot coordinates are pixel positions measured from the top-left corner of
the original layer canvas. The pivot is the point where the leaf meets its
stalk. The loader checks that there are eight unique IDs, valid four-channel
images of matching dimensions, and pivots that lie within the canvas.

The renderer uses these supplied files as inputs; it does not modify them.
When using another illustration, prepare equivalent transparent layers and
metadata first. Do not change the supplied assets unless you intend to change
the plant artwork or pivots.

## 5. Bit order and movement direction

The encrypted payload is read a byte at a time, with bits in most-significant-
bit-first order. Within a byte:

| Bit position | Leaf |
| --- | --- |
| 1st bit (most significant) | Leaf 1 |
| 2nd bit | Leaf 2 |
| 3rd bit | Leaf 3 |
| 4th bit | Leaf 4 |
| 5th bit | Leaf 5 |
| 6th bit | Leaf 6 |
| 7th bit | Leaf 7 |
| 8th bit (least significant) | Leaf 8 |

The project uses OpenCV's `getRotationMatrix2D`. In OpenCV, a positive angle is
counter-clockwise and a negative angle is clockwise:

- **Bit 0:** counter-clockwise by `LEAF_TILT_DEGREES`.
- **Bit 1:** clockwise by `LEAF_TILT_DEGREES`.

The single angle is `LEAF_TILT_DEGREES = 8` in `config/settings.py`. Keeping it
at 8 degrees helps avoid overlap between nearby leaves.

## 6. What happens when the program runs

Run with text in quotation marks:

```powershell
python src/main.py "HELLO"
```

The steps are:

1. **Read the input text.** The command-line text is converted to UTF-8. If no
   text is provided, the default is `HELLO`.
2. **Load the plant artwork.** `src/leaf_selector.py` loads the stem image,
   eight leaf images, and pivots from `plant_layers/`.
3. **Prepare a padded canvas.** A white margin is added around the source
   artwork so rotating leaf tips are less likely to be cropped. The margin is
   `CANVAS_MARGIN = 32` pixels on each side before tight output bounds are
   calculated.
4. **Make visual test images.** The program saves a neutral pivot diagram,
   single-leaf previews, per-leaf previews, and previews with all leaves tilted
   in each direction.
5. **Encrypt the text.** `src/encoder.py` creates a random 256-bit key and a
   fresh 12-byte nonce, then encrypts the UTF-8 text with AES-GCM.
6. **Save the encryption material.** `output/encryption_key.bin` contains the
   raw key. `output/encrypted_payload.bin` contains the nonce followed by the
   AES-GCM ciphertext and authentication tag.
7. **Make bytes into groups of eight bits.** Each byte in that payload becomes
   one animation state. No bit padding is needed because payloads are whole
   bytes.
8. **Render the video.** `src/leaf_transform.py` rotates all eight leaf layers
   to the target directions and composites them over the stationary stem.
   `src/video_generator.py` creates the transitions and writes FFV1 video.

### Repeated bit values still produce movement

The stored leaf position represents the bit, not whether it changed from the
previous byte. If the same leaf has the same bit in consecutive bytes, simply
changing directly from one state to the next would leave that leaf stationary.
To make every byte boundary visible, the animation smoothly returns all leaves
to neutral and then moves them to the next byte's directions. The held
directions represent the current byte.

The video uses 24 frames per second. The settings are eight frames for the
transition, eight for reset between states, and eight for holding the state.
Together, they make 24 frames (one second) per byte. For the first byte, there
is no previous state to reset, so the available transition uses 16 frames and
the hold uses eight frames. Later bytes use eight reset frames, eight movement
frames, and eight hold frames.

## 7. Encryption details and important key warning

AES-GCM adds a 16-byte authentication tag to the encrypted text. The saved
payload is laid out as:

```text
12-byte nonce | ciphertext | 16-byte authentication tag
```

If the original text contains `N` UTF-8 bytes, the payload therefore contains
`N + 28` bytes: 12 nonce bytes, `N` encrypted bytes, and 16 tag bytes. The video
represents every payload byte, including the nonce and tag, so its duration is
`N + 28` seconds.

**Keep the key private.** The key is saved separately so the output can be
decrypted for this prototype. Anyone who obtains both the video/payload and
`encryption_key.bin` can recover the message. Each run generates a new random
key and overwrites the previous key and payload files. Keep copies together if
you need to decode that run, and do not share the key with the video when
confidentiality matters.

The project currently encodes data; it does not include a video decoder or a
command that decrypts the extracted payload.

## 8. Video format, size, and generation-time estimate

The output is `output/encoded_plant.avi`, using FFV1 lossless compression at
24 FPS. The current generated canvas is 568 × 656 pixels. Exact file size
depends on the layer artwork and output length; the test run for `HELLO`
produced a 33-second, 792-frame video of about 74 MB. Lossless video is much
larger than an ordinary compressed MP4. Some media players may not support
FFV1/AVI; use a player that supports FFV1 or convert a copy for casual viewing.
Keep the original AVI for image measurement/decoding.

### Duration for a line of text

For a line containing `N` UTF-8 bytes:

```text
video duration in seconds = N + 28
```

For example, `HELLO` contains 5 UTF-8 bytes and produces 33 encrypted-byte
states, so the video is 33 seconds long. An 80-character ASCII line has 80
UTF-8 bytes and produces about 108 seconds (1 minute 48 seconds) of video.
Characters outside ASCII can take more than one UTF-8 byte, so count encoded
bytes rather than visible characters.

### Approximate time to generate

On the development machine, a complete run for `HELLO` took about **156
seconds** and produced a 33-second video. The measured time includes loading
the assets, creating the preview images, encrypting, rendering, and writing
the AVI. That works out to roughly **4.7 seconds of processing per encrypted
byte/state** for this test.

As a rough estimate on the same machine:

- `HELLO`: about 2.5–3 minutes for the full run.
- An 80-byte ASCII line: around 8–9 minutes for the full run.

These are estimates, not guarantees. Computer speed, disk speed, image size,
and OpenCV build affect the time. The animation itself always plays at one
second per encrypted byte; generation takes longer than playback. The test
images also add some work to each run.

The FFV1 AVI is intentionally large: the measured 74 MB for 33 seconds is
roughly 2.2 MB per video second. File size varies with the image and codec
implementation.

## 9. Files and responsibilities

| File | Responsibility |
| --- | --- |
| `src/main.py` | Coordinates asset loading, test-image generation, encryption, bit grouping, and video writing |
| `src/leaf_selector.py` | Loads and validates transparent layer PNGs and pivot metadata; does not segment the plant |
| `src/leaf_transform.py` | Prepares alpha layers, rotates each leaf around its pivot, and composites a frame |
| `src/encoder.py` | Encrypts text, converts bytes to bits, groups bits, and maps bits to angles |
| `src/video_generator.py` | Creates visual previews and the per-byte transition/hold video |
| `config/settings.py` | Stores paths, tilt angle, white margin, frame timing, and codec |
| `plant_layers/` | Original stem, leaf layers, and JSON pivots |
| `tests/test_layer_composition.py` | Exhaustively checks all 256 byte states |

The original `input/plant.png` remains in the project for reference but is not
used by the layered renderer.

## 10. Configuration values

Edit `config/settings.py` to change paths or animation settings:

| Setting | Current value | Meaning |
| --- | ---: | --- |
| `LEAF_TILT_DEGREES` | 8 | Rotation magnitude for either bit direction |
| `CANVAS_MARGIN` | 32 pixels | White safety margin around the layer canvas |
| `FPS` | 24 | Video frame rate |
| `FRAMES_PER_TRANSITION` | 8 | Movement frames for byte states after the first; the first state uses the extra available frames |
| `RESET_FRAMES` | 8 | Frames used to return to neutral between bytes |
| `HOLD_FRAMES` | 8 | Frames that hold the encoded state |
| `VIDEO_FOURCC` | `FFV1` | Lossless video codec |

The video generator requires `FRAMES_PER_TRANSITION + RESET_FRAMES +
HOLD_FRAMES == FPS`; otherwise it reports a configuration error. Keep `FPS`
and the frame counts consistent so a byte continues to occupy one second.
Large angles can cause nearby leaves to overlap.

The actual pivots and layer filenames are in `plant_layers/leaves.json`, not
in `settings.py`.

## 11. Generated output files

Running the program creates or replaces these files:

| Output | Purpose |
| --- | --- |
| `output/encoded_plant.avi` | Final lossless encoded animation |
| `output/encryption_key.bin` | Raw random AES-256 key for this run |
| `output/encrypted_payload.bin` | Nonce, ciphertext, and authentication tag |
| `output/debug_leaves.png` | Neutral plant with JSON pivots and leaf IDs marked |
| `output/test_leaf_left.png`, `output/test_leaf_right.png` | First leaf tilted each way |
| `output/test_all_counterclockwise.png` | All eight leaves tilted counter-clockwise |
| `output/test_all_clockwise.png` | All eight leaves tilted clockwise |
| `output/leaf_1_left.png` through `output/leaf_8_right.png` | One leaf tilted at a time |

The visual test images are previews, not additional encryption frames. The
final video contains only the encrypted payload states.

## 12. Validation performed

Run the tests from the project root:

```powershell
python -m unittest discover -s tests -v
```

The tests render all 256 possible byte values and check:

- Every state has all eight leaf layers and eight bit directions.
- The output has white margins on all four outer edges.
- The pivot-center pixel for each leaf remains unchanged from the neutral
  rendered state.
- No two transformed leaf alpha silhouettes overlap at the configured
  8-degree tilt.
- The stem and leaf source arrays remain unchanged during rendering.
- Bit 0 and bit 1 map to their configured counter-clockwise and clockwise
  directions.

These automated checks do not replace visual inspection for every possible
display or encoder. The all-leaves previews are useful for checking the
worst-case directions by eye.

To generate the output again:

```powershell
python src/main.py "YOUR TEXT HERE"
```

Check `output/debug_leaves.png` if you want to inspect the pivots. Because the
layer PNGs and JSON are supplied artwork, adjust those source assets only if a
pivot or source layer is actually incorrect.

## 13. Limitations to know

- This is a visual demonstration, not a high-capacity or steganographic
  communication system. One second represents only one encrypted byte.
- AES-GCM encrypts and authenticates the payload, but the animation itself
  needs a decoder to recover bit directions. A decoder is not included yet.
- The key is stored as a raw file for this prototype. Protect it; storing it
  beside the payload is convenient for testing but does not protect the message
  if both files are shared.
- Lossless FFV1 preserves small tilts but creates large files and may not play
  in every default media player.
- Exact run time and file size depend on hardware, OpenCV's FFV1 support,
  artwork, and text length.
