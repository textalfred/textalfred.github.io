#!/usr/bin/env python3
"""Holographic glitch renderer (PIL only, no numpy).

    python3 art/holo.py IN OUT [--color #e11d2a] [--seed N] [--width W]
                               [--aspect 2:3] [--flat] [--mask M.png]

Takes a subject on a plain/dark background (or with alpha), extracts the
silhouette and renders it in the house hologram style:

  * rough-edged colour blotch behind the subject, stored the way the original
    art stores it: full colour in RGB but only a faint glow in alpha, so on the
    black page it reads as a soft halo (viewers that ignore alpha show the
    solid blotch)
  * subject in a darker shade of the hue, internal detail kept as tone, with
    faceted (triangulated) shading and a faint wireframe
  * dense thin scanlines, horizontal smear streaks bleeding past the edge,
    a few horizontal slices shifted sideways, thin white highlight lines

Output is RGBA with a transparent background (like the reference art) unless
--flat, which composites onto pure black RGB. Same seed -> same output.
"""
import argparse
import colorsys
import random

from PIL import (Image, ImageChops, ImageDraw, ImageFilter,
                 ImageOps, ImageStat)


# ---------------------------------------------------------------- helpers

def hex_rgb(s):
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def shade(rgb, light=None, sat=None):
    """Same hue, different lightness/saturation (HLS)."""
    h, l, s = colorsys.rgb_to_hls(*[c / 255.0 for c in rgb])
    if light is not None:
        l = light
    if sat is not None:
        s = sat
    return tuple(int(round(c * 255)) for c in colorsys.hls_to_rgb(h, l, s))


def noise(rng, size, blur=0.0, out=None):
    """Deterministic value noise: random bytes at `size`, optionally resized."""
    w, h = size
    im = Image.frombytes("L", (w, h), rng.randbytes(w * h))
    if out:
        im = im.resize(out, Image.BICUBIC)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return ImageOps.autocontrast(im)


def threshold(im, t):
    return im.point(lambda v: 255 if v >= t else 0)


def scale_l(im, k, offset=0):
    return im.point(lambda v: max(0, min(255, int(v * k + offset))))


# ---------------------------------------------------------------- silhouette

def _components(px, w, h, want):
    """4-connected components of pixels where (px >= 128) == want.
    Yields (pixel index list, touches_border)."""
    seen = bytearray(w * h)
    for start in range(w * h):
        if seen[start] or (px[start] >= 128) != want:
            continue
        comp, stack, border = [], [start], False
        seen[start] = 1
        while stack:
            i = stack.pop()
            comp.append(i)
            x, y = i % w, i // w
            if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                border = True
            for j in (i - 1 if x else -1, i + 1 if x < w - 1 else -1,
                      i - w if y else -1, i + w if y < h - 1 else -1):
                if j >= 0 and not seen[j] and (px[j] >= 128) == want:
                    seen[j] = 1
                    stack.append(j)
        yield comp, border


def clean_mask(mask, keep_frac=0.02, hole_frac=0.08):
    """Drop specks and stray marks (e.g. a corner watermark): keep only
    components at least keep_frac of the largest. Then fill enclosed
    background pockets smaller than hole_frac of the image, so a black coat
    on a black background stays solid while big open gaps survive.
    Works at 1/4 resolution; the full-res edge is preserved."""
    W, H = mask.size
    f = 4
    small = mask.resize((max(1, W // f), max(1, H // f)), Image.BOX)
    w, h = small.size
    px = small.tobytes()
    comps = [c for c, _ in _components(px, w, h, True)]
    if not comps:
        return mask
    big = max(len(c) for c in comps)
    keep = bytearray(w * h)
    for c in comps:
        if len(c) >= keep_frac * big:
            for i in c:
                keep[i] = 255
    fill = bytearray(w * h)
    for c, border in _components(bytes(keep), w, h, False):
        if not border and len(c) < hole_frac * w * h:
            for i in c:
                fill[i] = 255
    keep_im = Image.frombytes("L", (w, h), bytes(keep)).resize((W, H), Image.NEAREST)
    keep_im = keep_im.filter(ImageFilter.MaxFilter(2 * f + 1))   # generous: edges come from `mask`
    fill_im = Image.frombytes("L", (w, h), bytes(fill)).resize((W, H), Image.BILINEAR)
    fill_im = threshold(fill_im.filter(ImageFilter.MaxFilter(f + 1 | 1)), 1)
    return ImageChops.lighter(ImageChops.multiply(mask, keep_im), fill_im)


def silhouette(src):
    """Return (mask L, tone L) for an RGBA source."""
    alpha = src.getchannel("A")
    rgb = src.convert("RGB")
    lo, hi = alpha.getextrema()
    if lo < 250:                       # real alpha channel: trust it
        mask = clean_mask(alpha)
    else:                              # plain background: key on the corners
        W, H = src.size
        corners = [rgb.getpixel(p) for p in
                   ((2, 2), (W - 3, 2), (2, H - 3), (W - 3, H - 3))]
        bg = tuple(sorted(c[i] for c in corners)[1] for i in range(3))
        diff = ImageChops.difference(rgb, Image.new("RGB", src.size, bg))
        r, g, b = diff.split()
        d = ImageChops.lighter(ImageChops.lighter(r, g), b)
        mask = threshold(d.filter(ImageFilter.GaussianBlur(1)), 28)
        mask = mask.filter(ImageFilter.MedianFilter(5))
        mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
        mask = clean_mask(mask)
        mask = mask.filter(ImageFilter.GaussianBlur(0.8))
    tone = rgb.convert("L")
    return mask, tone


def normalise_tone(tone, mask):
    """Map subject luminance so its mean sits on the base colour and detail
    spreads either side; flat subjects just come out at the base colour."""
    hard = threshold(mask, 128)
    st = ImageStat.Stat(tone, hard)
    mean, sd = st.mean[0], max(st.stddev[0], 1.0)
    k = 62.0 / max(sd, 18.0)           # don't blow up nearly-flat inputs
    return tone.point(lambda v: max(0, min(255, int(140 + (v - mean) * k))))


# ---------------------------------------------------------------- layers

def facets(rng, size, bbox, cell):
    """Triangulated shading (L, 128 = neutral) and wireframe lines (L)."""
    W, H = size
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - cell), max(0, y0 - cell)
    x1, y1 = min(W, x1 + cell), min(H, y1 + cell)
    nx, ny = int((x1 - x0) / cell) + 2, int((y1 - y0) / (cell * 1.3)) + 2
    pts = [[(x0 + i * cell + rng.uniform(-0.45, 0.45) * cell,
             y0 + j * cell * 1.3 + rng.uniform(-0.45, 0.45) * cell)
            for i in range(nx)] for j in range(ny)]
    shade_im = Image.new("L", size, 128)
    wire = Image.new("L", size, 0)
    ds, dw = ImageDraw.Draw(shade_im), ImageDraw.Draw(wire)
    tris = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a, b, c, d = pts[j][i], pts[j][i + 1], pts[j + 1][i], pts[j + 1][i + 1]
            if rng.random() < 0.5:
                tris += [(a, b, d), (a, d, c)]
            else:
                tris += [(a, b, c), (b, d, c)]
    for t in tris:
        ds.polygon(t, fill=int(128 + rng.gauss(0, 16)))
    for t in tris:
        for p, q in ((t[0], t[1]), (t[1], t[2])):
            if rng.random() < 0.75:
                dw.line([p, q], fill=int(rng.uniform(40, 150)), width=1)
    return shade_im.filter(ImageFilter.GaussianBlur(0.7)), wire


def scanline_pattern(rng, W, H, period):
    col = Image.new("L", (1, H))
    vals = []
    for y in range(H):
        v = 255 if (y % period) else 165
        v = int(v * rng.uniform(0.88, 1.0))
        vals.append(v)
    col.putdata(vals)
    return col.resize((W, H), Image.NEAREST)


def row_extents(mask):
    """Per row: (left, right) of the hard mask, or None."""
    W, H = mask.size
    hard = threshold(mask, 128)
    out = []
    for y in range(H):
        bb = hard.crop((0, y, W, y + 1)).getbbox()
        out.append((bb[0], bb[2] - 1) if bb else None)
    return out


def draw_fade(draw, x, y, length, direction, rgb, a0, width=1, seg=6):
    """Horizontal line fading from alpha a0 to 0 over `length` px."""
    n = max(1, int(length / seg))
    for k in range(n):
        a = int(a0 * (1 - k / n) ** 1.3)
        xa = x + direction * k * seg
        xb = x + direction * (k + 1) * seg
        draw.line([(xa, y), (xb, y)], fill=rgb + (a,), width=width)


# ---------------------------------------------------------------- main render

def render(src, color, seed, width=None):
    rng = random.Random(seed)
    src = src.convert("RGBA")
    if width and width != src.width:
        src = src.resize((width, round(src.height * width / src.width)), Image.LANCZOS)
    W, H = src.size
    s = W / 1024.0 if W <= H else H / 1024.0   # scale factor for pixel sizes
    s = max(s, 0.25)

    base = hex_rgb(color)
    dark = shade(base, light=0.17)
    light = shade(base, light=0.72, sat=1.0)
    blotch_rgb = shade(base, light=0.60)

    mask, tone = silhouette(src)
    bbox = threshold(mask, 128).getbbox() or (0, 0, W, H)

    # --- blotch: dilated silhouette with rough, brushy edges -----------------
    sw, sh = max(8, W // 8), max(8, H // 8)
    m_small = mask.resize((sw, sh), Image.BOX).filter(ImageFilter.GaussianBlur(14))
    m_small = ImageOps.autocontrast(m_small)
    lo_n = noise(rng, (max(4, W // 80), max(4, H // 80)), out=(sw, sh))
    # blurred silhouette modulated by noise: stays attached to the subject
    field = ImageChops.multiply(m_small, lo_n.point(lambda v: int(110 + v * 0.57)))
    blotch = threshold(field.resize((W, H), Image.BICUBIC), 14)
    # brushy horizontal ragging on the edge
    rag = noise(rng, (max(4, W // 90), H // 3), out=(W, H))
    edge_zone = ImageChops.subtract(blotch.filter(ImageFilter.MaxFilter(1 + 2 * int(6 * s) | 1)),
                                    blotch.filter(ImageFilter.MinFilter(1 + 2 * int(6 * s) | 1)))
    bite = ImageChops.multiply(edge_zone, threshold(rag, 150))
    blotch = ImageChops.subtract(blotch, bite)
    blotch = blotch.filter(ImageFilter.MedianFilter(3))

    # --- glow alpha (what the blotch looks like on black) --------------------
    glow = mask.filter(ImageFilter.GaussianBlur(28 * s))
    glow = ImageOps.autocontrast(glow)
    glow = scale_l(glow, 0.38)
    glow = ImageChops.lighter(glow, scale_l(mask.filter(ImageFilter.GaussianBlur(8 * s)), 0.30))
    glow = ImageChops.multiply(glow, blotch)

    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(Image.new("RGB", (W, H), blotch_rgb), (0, 0), blotch)
    out.putalpha(glow)

    # --- subject colour ------------------------------------------------------
    t = normalise_tone(tone, mask)
    fshade, wire = facets(rng, (W, H), bbox, 46 * s)
    t = ImageChops.add(t, fshade, scale=1.0, offset=-128)
    t = ImageChops.add(t, noise(rng, (max(4, W // 40), max(4, H // 40)), out=(W, H))
                       .point(lambda v: 128 + (v - 128) // 6),
                       scale=1.0, offset=-128)  # gentle low-frequency mottling
    t = ImageChops.add(t, Image.frombytes("L", (W, H), rng.randbytes(W * H)).point(
        lambda v: 128 + (v - 128) // 10), scale=1.0, offset=-128)  # fine grain
    subj_rgb = ImageOps.colorize(t, black=dark, white=light, mid=base,
                                 blackpoint=20, midpoint=140, whitepoint=250)
    scan = scanline_pattern(rng, W, H, max(2, int(round(3 * s))))
    subj_rgb = ImageChops.multiply(subj_rgb, Image.merge("RGB", (scan, scan, scan)))
    subj_a = scale_l(mask, 0.93)
    subj = subj_rgb.convert("RGBA")
    subj.putalpha(subj_a)

    # --- soft horizontal smear under the subject -----------------------------
    smear = subj.resize((max(4, W // 28), H), Image.BOX).resize((W, H), Image.BILINEAR)
    rows = Image.new("L", (1, H))
    rv, y = [0] * H, 0
    while y < H:
        if rng.random() < 0.05:
            hgt = rng.randint(1, max(1, int(4 * s)))
            a = rng.randint(90, 220)
            for yy in range(y, min(H, y + hgt)):
                rv[yy] = a
            y += hgt
        y += 1
    rows.putdata(rv)
    rows = rows.resize((W, H), Image.NEAREST)
    smear.putalpha(ImageChops.multiply(smear.getchannel("A"), rows))
    smear.putalpha(scale_l(smear.getchannel("A"), 1.6))
    out.alpha_composite(smear)
    out.alpha_composite(subj)

    # --- streaks bleeding past the silhouette --------------------------------
    ext = row_extents(mask)
    streak = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(streak)
    for y, e in enumerate(ext):
        if not e:
            continue
        xl, xr = e
        span = xr - xl
        for side, prob in ((-1, 0.30), (1, 0.16)):
            if rng.random() < prob:
                x = xl if side < 0 else xr
                x += -side * rng.uniform(0, min(40 * s, span * 0.3))
                length = min(rng.expovariate(1 / (70 * s)), 380 * s) + 10 * s
                c = subj_rgb.getpixel((int(min(max(x, 0), W - 1)), y))
                if rng.random() < 0.2:
                    c = light
                draw_fade(sd, x, y, length, side, c, rng.randint(140, 235),
                          width=1 if rng.random() < 0.85 else 2)
        if span > 4 and rng.random() < 0.10:          # streaks across the body
            x = rng.uniform(xl, xr)
            c = light if rng.random() < 0.5 else dark
            draw_fade(sd, x, y, rng.uniform(20, 160) * s, rng.choice((-1, 1)),
                      c, rng.randint(60, 150))
    out.alpha_composite(streak)

    # --- thin white highlight lines -----------------------------------------
    hl = Image.new("RGBA", (W, H), shade(base, light=0.93, sat=1.0) + (0,))
    edges = tone.filter(ImageFilter.GaussianBlur(1.2 * s)).filter(ImageFilter.FIND_EDGES)
    edges = scale_l(threshold(edges, 22), 0.40)
    inner = mask.filter(ImageFilter.MinFilter(3))
    hl_a = ImageChops.lighter(ImageChops.multiply(edges, inner),
                              ImageChops.multiply(scale_l(wire, 0.8), inner))
    hl_a = ImageChops.multiply(hl_a, scan)
    hl.putalpha(hl_a)
    out.alpha_composite(hl)

    # --- glitch slices -------------------------------------------------------
    x0, y0, x1, y1 = bbox
    for _ in range(rng.randint(5, 8)):
        hgt = int(rng.uniform(2, 14) * s) + 1
        y = rng.randint(y0 + int(0.2 * (y1 - y0)), max(y0 + 1, y1 - hgt - 1))
        dx = int(rng.choice((-1, 1)) * rng.uniform(8, 55) * s)
        band = out.crop((0, y, W, y + hgt))
        moved = Image.new("RGBA", band.size, (0, 0, 0, 0))
        moved.paste(band, (dx, 0))
        # keep the faint halo underneath so the slice doesn't punch a hole
        under = out.crop((0, y, W, y + hgt))
        under.putalpha(scale_l(under.getchannel("A"), 0.35))
        under.alpha_composite(moved)
        out.paste(under, (0, y))
        e = ext[y] if y < H else None
        if e:
            gd = ImageDraw.Draw(out)
            ln = rng.uniform(30, 120) * s
            gd.line([(e[0] + dx - ln, y), (e[1] + dx + ln * 0.5, y)],
                    fill=light + (rng.randint(150, 230),), width=1)
    return out


def pad_to_aspect(src, aspect):
    """Pad (never crop) with the corner colour so width:height == aspect."""
    aw, ah = (float(v) for v in aspect.split(":"))
    W, H = src.size
    tw, th = W, H
    if W / H > aw / ah:
        th = round(W * ah / aw)
    else:
        tw = round(H * aw / ah)
    if (tw, th) == (W, H):
        return src
    canvas = Image.new("RGBA", (tw, th), src.getpixel((0, 0)))
    canvas.paste(src, ((tw - W) // 2, (th - H) // 2))
    return canvas


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--color", default="#e11d2a")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--width", type=int, default=None,
                    help="output width (default: input width)")
    ap.add_argument("--aspect", default=None,
                    help="pad the input to this aspect first, e.g. 2:3")
    ap.add_argument("--flat", action="store_true",
                    help="composite onto black RGB instead of transparent")
    ap.add_argument("--mask", default=None,
                    help="also save the extracted silhouette here (debugging)")
    a = ap.parse_args()
    src = Image.open(a.inp).convert("RGBA")
    if a.aspect:
        src = pad_to_aspect(src, a.aspect)
    if a.mask:
        silhouette(src)[0].save(a.mask)
    im = render(src, a.color, a.seed, a.width)
    if a.flat:
        bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
        bg.alpha_composite(im)
        im = bg.convert("RGB")
    im.save(a.out, optimize=True)


if __name__ == "__main__":
    main()
