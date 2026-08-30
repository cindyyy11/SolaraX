"""Generate the SolaraX brand assets from one geometric definition.

Everything below derives from the reference mark: a segmented radar dial with a
sun at its heart, a needle striking out to a node on the rim. The dial is the
fleet being swept; the sun is what is being measured; the needle and its nodes
are the peer comparison that turns a reading into a decision.

Colours are sampled from the reference artwork rather than eyeballed:
    navy   #192C4C   the dial, the wordmark, every structural stroke
    solar  #E3A246   the sun, the needle, the single point of emphasis

Run:  python make_brand.py <output_dir>
"""

import math
import os
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

NAVY = "#192C4C"
SOLAR = "#E3A246"

WORDMARK_FONT = r"C:\Windows\Fonts\seguisb.ttf"
WORD = "SolaraX"


# --- geometry ---------------------------------------------------------------

def polar(cx, cy, radius, degrees):
    """Screen coordinates: 0 deg points right, positive angles run clockwise."""
    radians = math.radians(degrees)
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def arc_path(cx, cy, radius, start_deg, end_deg):
    """A single open ring segment, drawn clockwise from start to end."""
    x1, y1 = polar(cx, cy, radius, start_deg)
    x2, y2 = polar(cx, cy, radius, end_deg)
    sweep = (end_deg - start_deg) % 360
    large = 1 if sweep > 180 else 0
    return (f"M {x1:.2f} {y1:.2f} "
            f"A {radius:.2f} {radius:.2f} 0 {large} 1 {x2:.2f} {y2:.2f}")


def ring(cx, cy, radius, gap_centres, gap_deg):
    """Ring broken by gaps centred on the given angles. Returns path segments."""
    centres = sorted(a % 360 for a in gap_centres)
    segments = []
    for index, gap in enumerate(centres):
        start = gap + gap_deg / 2
        end = centres[(index + 1) % len(centres)] - gap_deg / 2
        segments.append(arc_path(cx, cy, radius, start, end % 360))
    return segments


def sun_path(cx, cy, outer, inner, hole, points=8, rotation=-90.0):
    """An n-pointed sun with a knocked-out centre, as one evenodd path."""
    steps = points * 2
    coords = []
    for index in range(steps):
        radius = outer if index % 2 == 0 else inner
        angle = rotation + index * (360.0 / steps)
        coords.append(polar(cx, cy, radius, angle))

    star = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in coords) + " Z"
    # Counter-drawn circle: two arcs, so evenodd punches a true hole.
    circle = (f" M {cx - hole:.2f} {cy:.2f} "
              f"a {hole:.2f} {hole:.2f} 0 1 0 {hole * 2:.2f} 0 "
              f"a {hole:.2f} {hole:.2f} 0 1 0 {-hole * 2:.2f} 0 Z")
    return star + circle


# --- the mark ---------------------------------------------------------------

SIZE = 128
CX = CY = 64.0

R_OUTER = 54.0
W_OUTER = 10.0
R_INNER = 37.0
W_INNER = 6.0

NEEDLE_DEG = -45.0          # up and to the right
NEEDLE_FROM = 19.0
NEEDLE_TO = 43.0
NEEDLE_W = 7.0
NODE_SOLAR_R = 8.0

# (angle, radius) on the outer rim. Both sit ON an arc, never in a gap —
# a node floating in a break reads as a stray dot rather than a station.
NODES_NAVY = ((0.0, 6.5), (32.0, 6.0))

SUN_OUTER = 27.0
SUN_INNER = 15.5
SUN_HOLE = 8.5


def mark_body(navy=NAVY, solar=SOLAR):
    """The mark's drawing commands, shared by every variant."""
    parts = []

    for path in ring(CX, CY, R_OUTER, (45, 135, 225, 315), 15.0):
        parts.append(f'<path d="{path}" fill="none" stroke="{navy}" '
                     f'stroke-width="{W_OUTER}" stroke-linecap="butt"/>')

    for path in ring(CX, CY, R_INNER, (0, 90, 180, 270), 17.0):
        parts.append(f'<path d="{path}" fill="none" stroke="{navy}" '
                     f'stroke-width="{W_INNER}" stroke-linecap="butt"/>')

    for angle, radius in NODES_NAVY:
        x, y = polar(CX, CY, R_OUTER, angle)
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{navy}"/>')

    x1, y1 = polar(CX, CY, NEEDLE_FROM, NEEDLE_DEG)
    x2, y2 = polar(CX, CY, NEEDLE_TO, NEEDLE_DEG)
    parts.append(f'<path d="M {x1:.2f} {y1:.2f} L {x2:.2f} {y2:.2f}" fill="none" '
                 f'stroke="{solar}" stroke-width="{NEEDLE_W}" stroke-linecap="round"/>')

    parts.append(f'<path d="{sun_path(CX, CY, SUN_OUTER, SUN_INNER, SUN_HOLE)}" '
                 f'fill="{solar}" fill-rule="evenodd"/>')

    nx, ny = polar(CX, CY, NEEDLE_TO + 2.0, NEEDLE_DEG)
    parts.append(f'<circle cx="{nx:.2f}" cy="{ny:.2f}" r="{NODE_SOLAR_R}" fill="{solar}"/>')

    return parts


def svg_mark(navy=NAVY, solar=SOLAR, title="SolaraX"):
    body = "\n  ".join(mark_body(navy, solar))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" '
            f'width="{SIZE}" height="{SIZE}" role="img" aria-label="{title}">\n'
            f'  <title>{title}</title>\n  {body}\n</svg>\n')


# --- the wordmark -----------------------------------------------------------

def wordmark_paths(font_path, text, cap_target):
    """Glyph outlines as SVG path data, scaled so cap height equals cap_target.

    Outlines are baked into paths on purpose: a logo that depends on a font
    being installed is not a logo, it is a suggestion.
    """
    font = TTFont(font_path)
    upm = font["head"].unitsPerEm
    cap_height = getattr(font["OS/2"], "sCapHeight", None) or int(upm * 0.7)
    scale = cap_target / cap_height

    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    hmtx = font["hmtx"]

    paths = []
    pen_x = 0.0
    for char in text:
        name = cmap[ord(char)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        data = pen.getCommands()
        if data:
            # Font space is y-up; SVG is y-down. Flip and place on the baseline.
            transform = (f"translate({pen_x * scale:.3f} 0) "
                         f"scale({scale:.6f} {-scale:.6f})")
            paths.append((transform, data))
        pen_x += hmtx[name][0]

    return paths, pen_x * scale


def svg_lockup(navy=NAVY, solar=SOLAR, title="SolaraX"):
    """Horizontal lockup: mark, optical gap, wordmark sitting on a shared axis."""
    mark_size = 128.0
    cap = mark_size * 0.455
    paths, word_width = wordmark_paths(WORDMARK_FONT, WORD, cap)

    gap = mark_size * 0.30
    baseline_y = CY + cap / 2.0
    word_x = mark_size + gap

    pad = 8.0
    total_w = word_x + word_width + pad
    total_h = mark_size

    glyphs = "\n    ".join(
        f'<path transform="{t}" d="{d}"/>' for t, d in paths
    )
    body = "\n  ".join(mark_body(navy, solar))

    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {total_w:.2f} {total_h:.2f}" '
            f'width="{total_w:.0f}" height="{total_h:.0f}" '
            f'role="img" aria-label="{title}">\n'
            f'  <title>{title}</title>\n  {body}\n'
            f'  <g fill="{navy}" transform="translate({word_x:.2f} {baseline_y:.2f})">\n'
            f'    {glyphs}\n  </g>\n</svg>\n')


# --- favicon ----------------------------------------------------------------

def svg_favicon():
    """Simplified for 16px: one heavy ring, a blunter sun, no inner detail.

    The full mark's 15-degree gaps and eight sun points turn to mud below about
    32px, so the small size gets its own drawing rather than a scaled one.
    """
    cx = cy = 32.0
    parts = []
    for path in ring(cx, cy, 25.0, (45, 225), 26.0):
        parts.append(f'<path d="{path}" fill="none" stroke="{NAVY}" stroke-width="7"/>')
    parts.append(f'<path d="{sun_path(cx, cy, 15.0, 8.6, 0.0, points=8, rotation=-90)}" '
                 f'fill="{SOLAR}"/>')
    nx, ny = polar(cx, cy, 25.0, -45.0)
    parts.append(f'<circle cx="{nx:.2f}" cy="{ny:.2f}" r="6.5" fill="{SOLAR}"/>')
    body = "\n  ".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" '
            f'width="64" height="64" role="img" aria-label="SolaraX">\n'
            f'  <title>SolaraX</title>\n  {body}\n</svg>\n')


# --- main -------------------------------------------------------------------

def write(directory, name, content):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    print(f"  {name:28} {len(content):>6} bytes")


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    print("writing brand assets ->", out)

    write(out, "logo-mark.svg", svg_mark())
    write(out, "logo.svg", svg_lockup())
    write(out, "logo-mark-mono.svg",
          svg_mark(navy="currentColor", solar="currentColor", title="SolaraX"))
    write(out, "logo-mono.svg",
          svg_lockup(navy="currentColor", solar="currentColor"))
    write(out, "logo-on-dark.svg", svg_lockup(navy="#FFFFFF", solar=SOLAR))
    # On a dark plate the navy dial vanishes into the ground, so the structural
    # stroke inverts to white. The sun keeps its colour in every variant.
    write(out, "logo-mark-on-dark.svg", svg_mark(navy="#FFFFFF", solar=SOLAR))
    write(out, "favicon.svg", svg_favicon())


if __name__ == "__main__":
    main()
