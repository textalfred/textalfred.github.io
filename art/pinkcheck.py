#!/usr/bin/env python3
"""Pink-pixel check for the Alfred landing page.

For each image, prints the % of non-near-black pixels whose hue is 320-345 deg
with saturation > 0.3. Exits 1 if any image is over 1%.

Usage: python3 art/pinkcheck.py [images...]
Default: assets/*.png and favicon.png (relative to the site root).
"""
import colorsys
import glob
import os
import sys

from PIL import Image

HUE_LO, HUE_HI = 320 / 360, 345 / 360
MIN_SAT = 0.3
BLACK_MAX = 24  # max(r,g,b) <= this counts as near-black and is skipped
LIMIT = 1.0  # percent
MAX_SIDE = 400  # downscale large images for speed


def pink_percent(path):
    im = Image.open(path).convert("RGBA")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    total = pink = 0
    for r, g, b, a in im.getdata():
        if a < 16 or max(r, g, b) <= BLACK_MAX:
            continue
        total += 1
        h, s, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > MIN_SAT and HUE_LO <= h <= HUE_HI:
            pink += 1
    return (100.0 * pink / total) if total else 0.0, total


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = argv or sorted(glob.glob(os.path.join(root, "assets", "*.png"))) + [
        p for p in [os.path.join(root, "favicon.png")] if os.path.exists(p)
    ]
    if not paths:
        print("no images found")
        return 1
    failed = False
    for p in paths:
        pct, n = pink_percent(p)
        bad = pct > LIMIT
        failed |= bad
        print(f"{'FAIL' if bad else 'ok  '} {pct:6.2f}%  ({n} px)  {os.path.relpath(p, root)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
