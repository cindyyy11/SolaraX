# Brand asset generators

The SolaraX mark is defined once, as geometry, in `make_brand.py` — not as a
binary anyone would have to re-trace. Everything in `apps/web/public/brand/`
is generated from it, so the SVG and the PNG can never drift apart.

```
python tools/brand/make_brand.py apps/web/public/brand   # the vectors
python tools/brand/render_png.py apps/web/public/brand   # the rasters
```

`render_png.py` imports its constants from `make_brand.py` rather than
repeating them, which is the only thing keeping the two renderers honest.

**Colours** are sampled from the original reference artwork, not eyeballed:

| Token | Hex | Used for |
|---|---|---|
| navy | `#192C4C` | the dial, the wordmark, every structural stroke |
| solar | `#E3A246` | the sun, the needle, the one point of emphasis |

**The wordmark is baked to outlines** from Segoe UI Semibold. A logo that
depends on a font being installed on the viewer's machine is not a logo.

`render_png.py` needs Pillow; `make_brand.py` needs fontTools. Both arrive with
the pipeline requirements. Neither is imported by the pipeline or the web app —
these run by hand, when the mark changes.
