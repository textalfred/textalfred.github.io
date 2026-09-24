# Art pipeline

Everything here is plain Python 3 + Pillow (no numpy, no ImageMagick). Run the commands from the repo root.

| Output | Made by |
| --- | --- |
| `assets/alfred-holo.png` (848x1272, 2:3, RGBA) | `holo.py` on `art/source/alfred.png` |
| `assets/bat-holo.png` (1536x1024, RGBA) | `holo.py` on `art/source/bat.png` |
| `assets/bat.svg` (viewBox 0 0 100 50, `fill="currentColor"`) | `bat.py` |
| `favicon.png` (96x96, red bat on black, no effect) | `bat.py` |
| `art/source/bat.png` (white bat on black, input for holo) | `bat.py` |

## Regenerate

```sh
# bat.svg, favicon.png and the bat source image (all from one shape definition)
python3 art/bat.py

# bottom-of-page bat hologram
python3 art/holo.py art/source/bat.png assets/bat-holo.png

# Alfred hologram, the exact command used for the current asset
python3 art/holo.py art/source/alfred.png assets/alfred-holo.png --aspect 2:3
```

The output is deterministic: the same input and `--seed` always give the same bytes.

## holo.py

```
python3 art/holo.py IN OUT [--color #e11d2a] [--seed N] [--width W]
                           [--aspect 2:3] [--flat] [--mask MASK.png]
```

- `--color`: base hue (default brand red `#e11d2a`). The darker subject shade, the light highlights and the blotch are all derived from it.
- `--seed`: changes the streaks, glitch slices, facets and blotch shape (default 7).
- `--width`: resize the output to this width. The default is the input width. Don't upscale much: the effect is built from 1px lines, and upscaling blurs them.
- `--aspect`: pad the input (never crop) with its corner colour to this ratio first.
- `--flat`: composite onto opaque black RGB. By default the output is transparent RGBA, like the original art.
- `--mask`: also save the extracted silhouette, so you can check what was picked up.

How the silhouette is found: if the image has real alpha, the alpha channel is used. Otherwise pixels far from the corner background colour are keyed out. After that, only the largest shape (and pieces at least 2% of its size) is kept, which drops watermarks and specks. Small enclosed pockets of background inside the figure are filled in.

Note on the reference style: in the original pink art, the big solid blotch lives in the RGB channels, but its alpha is only a faint glow. On the black page it reads as a soft halo, and viewers that ignore alpha show the solid blotch. `holo.py` stores its output the same way.

## Tips for a new Alfred source image

Save it as `art/source/alfred.png` and rerun the Alfred command above. Then check `--mask` output and a 200px-wide downscale, because the page shows the image at about 200px.

- A full body, standing, the whole figure in frame with some margin on every side (the streaks and halo need room).
- A plain dark (ideally near-black) or transparent background, with nothing else in the frame. Watermarks are dropped only when they don't touch the figure.
- 2:3 portrait. Otherwise pass `--aspect 2:3`.
- A strong outline. A light rim around the figure (as in the current image) makes the extraction exact even when the coat is black.
- Greyscale or low-saturation art with clear tonal contrast works best, since it is all remapped to one hue. Keep the face large and well lit so it survives the 200px downscale.
- Character: comic-style Alfred Pennyworth, with a bald crown, a pencil moustache, a tailcoat and bow tie, and a silver tray.
