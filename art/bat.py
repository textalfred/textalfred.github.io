#!/usr/bin/env python3
"""Classic Batman bat silhouette: one shape definition, three outputs.

    python3 art/bat.py

writes
    assets/bat.svg            single path, viewBox 0 0 100 50, fill=currentColor
    art/source/bat.png        1536x1024 white bat on black (input for holo.py)
    favicon.png               96x96 red bat on black, no holo effect
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RED = (225, 29, 42)

# Right half, clockwise from the top centre. ("L", pt) or ("Q", ctrl, pt).
START = (50.0, 12.5)
RIGHT = [
    ("L", (53.2, 12.5)),          # top of head
    ("L", (55.8, 3.0)),           # ear tip
    ("L", (57.6, 14.0)),          # outer ear base
    ("Q", (59.0, 16.2), (62.0, 16.0)),   # shoulder
    ("Q", (80.0, 15.5), (98.5, 5.0)),    # leading edge up to the wing tip
    ("Q", (88.0, 15.0), (88.5, 32.0)),   # outer edge down to first spike
    ("Q", (82.0, 23.0), (74.5, 33.5)),   # scallop 1
    ("Q", (68.0, 26.5), (62.0, 37.5)),   # scallop 2
    ("Q", (57.5, 30.0), (54.0, 36.0)),   # scallop 3 into the body
    ("L", (50.0, 47.5)),          # tail point
]


def _mirror(p):
    return (100.0 - p[0], p[1])


def segments():
    """Full outline as a list of segments starting at START."""
    segs = list(RIGHT)
    # walk the right half backwards, mirrored, to close the left half
    pts = [START] + [s[-1] for s in RIGHT]
    left = []
    for i in range(len(RIGHT) - 1, -1, -1):
        seg = RIGHT[i]
        dest = _mirror(pts[i])
        if seg[0] == "L":
            left.append(("L", dest))
        else:
            left.append(("Q", _mirror(seg[1]), dest))
    # the tail point is shared; skip the mirrored copy of it
    return segs + left


def svg_path():
    f = lambda v: ("%.2f" % v).rstrip("0").rstrip(".")
    d = ["M%s %s" % (f(START[0]), f(START[1]))]
    for s in segments():
        if s[0] == "L":
            d.append("L%s %s" % (f(s[1][0]), f(s[1][1])))
        else:
            d.append("Q%s %s %s %s" % (f(s[1][0]), f(s[1][1]), f(s[2][0]), f(s[2][1])))
    return " ".join(d) + "Z"


def polygon(scale=1.0, ox=0.0, oy=0.0, steps=48):
    pts = [START]
    cur = START
    for s in segments():
        if s[0] == "L":
            pts.append(s[1])
        else:
            c, e = s[1], s[2]
            for k in range(1, steps + 1):
                t = k / steps
                x = (1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * c[0] + t * t * e[0]
                y = (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * c[1] + t * t * e[1]
                pts.append((x, y))
        cur = s[-1]
    return [(ox + x * scale, oy + y * scale) for x, y in pts]


def render(size, bat_width, fill, bg, ss=4):
    """Anti-aliased bat centred on a canvas, supersampled ss times."""
    W, H = size
    big = Image.new("RGB", (W * ss, H * ss), bg)
    sc = bat_width * ss / 100.0
    ox = (W * ss - 100 * sc) / 2
    oy = (H * ss - 50 * sc) / 2 + 2 * sc  # optical centre: nudge down a touch
    ImageDraw.Draw(big).polygon(polygon(sc, ox, oy), fill=fill)
    return big.resize(size, Image.LANCZOS)


def main():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50" '
           'fill="currentColor" role="img" aria-label="Bat">'
           '<path d="%s"/></svg>\n' % svg_path())
    with open(os.path.join(ROOT, "assets", "bat.svg"), "w") as fh:
        fh.write(svg)
    os.makedirs(os.path.join(ROOT, "art", "source"), exist_ok=True)
    render((1536, 1024), 1100, (255, 255, 255), (0, 0, 0)).save(
        os.path.join(ROOT, "art", "source", "bat.png"))
    render((96, 96), 90, RED, (0, 0, 0), ss=8).save(
        os.path.join(ROOT, "favicon.png"), optimize=True)
    print("wrote assets/bat.svg, art/source/bat.png, favicon.png")


if __name__ == "__main__":
    main()
