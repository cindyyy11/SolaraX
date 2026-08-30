"""Raster companions to the SVG brand assets.

Draws the same geometry as make_brand.py with Pillow, at 6x then downsampled,
because the ICO and the social card have to be real pixels and no SVG
rasteriser is installed here. Constants are imported rather than retyped so the
two renderers cannot drift apart.

Run:  python render_png.py <output_dir>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_brand import (  # noqa: E402
    CX, CY, NAVY, NEEDLE_DEG, NEEDLE_TO, NEEDLE_W, NODES_NAVY, NODE_SOLAR_R,
    R_INNER, R_OUTER, SIZE, SOLAR, SUN_HOLE, SUN_INNER, SUN_OUTER, W_INNER,
    W_OUTER, WORD, WORDMARK_FONT, polar,
)

SS = 6  # supersample factor


def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def draw_ring(draw, cx, cy, radius, width, gap_centres, gap_deg, colour):
    centres = sorted(a % 360 for a in gap_centres)
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    for index, gap in enumerate(centres):
        start = gap + gap_deg / 2
        end = centres[(index + 1) % len(centres)] - gap_deg / 2
        if end < start:
            end += 360
        draw.arc(box, start, end, fill=colour, width=int(round(width)))


def draw_sun(draw, cx, cy, outer, inner, hole, colour, hole_colour, points=8):
    steps = points * 2
    coords = []
    for index in range(steps):
        radius = outer if index % 2 == 0 else inner
        angle = -90 + index * (360.0 / steps)
        coords.append(polar(cx, cy, radius, angle))
    draw.polygon(coords, fill=colour)
    if hole > 0 and hole_colour is not None:
        draw.ellipse((cx - hole, cy - hole, cx + hole, cy + hole), fill=hole_colour)


def render_mark(size, background=None, ink=NAVY):
    """The mark at `size` px. background=None yields a transparent PNG.

    `ink` overrides the structural navy so the mark can invert to white on a
    dark plate; the sun keeps its colour either way.
    """
    s = size * SS
    scale = s / float(SIZE)
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0) if background is None else rgb(background))
    draw = ImageDraw.Draw(canvas)

    navy, solar = rgb(ink), rgb(SOLAR)
    cx, cy = CX * scale, CY * scale
    hole_colour = (0, 0, 0, 0) if background is None else rgb(background)

    draw_ring(draw, cx, cy, R_OUTER * scale, W_OUTER * scale,
              (45, 135, 225, 315), 15.0, navy)
    draw_ring(draw, cx, cy, R_INNER * scale, W_INNER * scale,
              (0, 90, 180, 270), 17.0, navy)

    for angle, radius in NODES_NAVY:
        x, y = polar(cx, cy, R_OUTER * scale, angle)
        r = radius * scale
        draw.ellipse((x - r, y - r, x + r, y + r), fill=navy)

    x1, y1 = polar(cx, cy, 19.0 * scale, NEEDLE_DEG)
    x2, y2 = polar(cx, cy, NEEDLE_TO * scale, NEEDLE_DEG)
    draw.line((x1, y1, x2, y2), fill=solar, width=int(round(NEEDLE_W * scale)))

    draw_sun(draw, cx, cy, SUN_OUTER * scale, SUN_INNER * scale,
             SUN_HOLE * scale, solar, hole_colour)

    nx, ny = polar(cx, cy, (NEEDLE_TO + 2.0) * scale, NEEDLE_DEG)
    nr = NODE_SOLAR_R * scale
    draw.ellipse((nx - nr, ny - nr, nx + nr, ny + nr), fill=solar)

    return canvas.resize((size, size), Image.LANCZOS)


def render_lockup(mark_px, background, ink):
    """Mark plus wordmark, on a plate. Used for the social card and previews."""
    mark = render_mark(mark_px, background=None, ink=ink)
    cap = int(mark_px * 0.455)
    font = ImageFont.truetype(WORDMARK_FONT, int(cap * 1.36))

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    box = probe.textbbox((0, 0), WORD, font=font)
    word_w, word_h = box[2] - box[0], box[3] - box[1]

    gap = int(mark_px * 0.30)
    pad = int(mark_px * 0.22)
    width = pad + mark_px + gap + word_w + pad
    height = mark_px + pad * 2

    canvas = Image.new("RGB", (width, height), rgb(background))
    canvas.paste(mark, (pad, pad), mark)
    draw = ImageDraw.Draw(canvas)
    ty = pad + (mark_px - word_h) // 2 - box[1]
    draw.text((pad + mark_px + gap, ty), WORD, font=font, fill=rgb(ink))
    return canvas


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    print("rendering rasters ->", out)

    for size in (512, 256, 128):
        img = render_mark(size)
        img.save(os.path.join(out, f"logo-mark-{size}.png"))
        print(f"  logo-mark-{size}.png")

    apple = render_mark(180, background="#FFFFFF")
    apple.convert("RGB").save(os.path.join(out, "apple-touch-icon.png"))
    print("  apple-touch-icon.png")

    lockup = render_lockup(256, "#FFFFFF", NAVY)
    lockup.save(os.path.join(out, "logo-lockup.png"))
    print(f"  logo-lockup.png  {lockup.size[0]}x{lockup.size[1]}")

    dark = render_lockup(256, "#0D1220", "#FFFFFF")
    dark.save(os.path.join(out, "logo-lockup-dark.png"))
    print("  logo-lockup-dark.png")

    return out


if __name__ == "__main__":
    main()
