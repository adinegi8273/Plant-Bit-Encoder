"""Compose the plant from layers: no masks, no inpainting -> no cuts.
Each leaf is its own transparent full-size PNG, rotated about its pivot
(the point where it joins the stalk), then alpha-composited over stem.png."""
import json, cv2, numpy as np
from pathlib import Path

LAYERS = Path("plant_layers")
ANGLE = 8  # degrees; larger values make neighbouring leaves overlap

def load(p): return cv2.imread(str(p), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0

def over(dst, src):
    a = src[..., 3:4]
    out = dst.copy()
    out[..., :3] = src[..., :3] * a + dst[..., :3] * (1 - a)
    out[..., 3:4] = a + dst[..., 3:4] * (1 - a)
    return out

def render(bits, angle=ANGLE, bg=(1, 1, 1)):
    meta = json.loads((LAYERS / "leaves.json").read_text())
    canvas = load(LAYERS / "stem.png")
    h, w = canvas.shape[:2]
    for leaf, bit in zip(meta, bits):
        img = load(LAYERS / leaf["file"])
        # OpenCV: positive angle = counter-clockwise, so negate for clockwise
        a = -angle if bit == "1" else angle
        M = cv2.getRotationMatrix2D(tuple(leaf["pivot"]), a, 1.0)
        # premultiply so edges don't get dark halos when interpolated
        pm = img.copy(); pm[..., :3] *= pm[..., 3:4]
        r = cv2.warpAffine(pm, M, (w, h), flags=cv2.INTER_CUBIC,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        r = np.clip(r, 0, 1)
        al = r[..., 3:4]
        r[..., :3] = np.where(al > 1e-4, r[..., :3] / np.maximum(al, 1e-4), 0)
        canvas = over(canvas, r)
    white = np.ones_like(canvas[..., :3]) * np.array(bg, np.float32)
    rgb = canvas[..., :3] * canvas[..., 3:4] + white * (1 - canvas[..., 3:4])
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

if __name__ == "__main__":
    cv2.imwrite("encoded_plant.png", render("10110010"))
