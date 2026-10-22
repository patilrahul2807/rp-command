---
name: core-figma-extractor
description: "Shared Figma extraction: run scripts/figma_extract.py, the design.json format, and how agents use frames, texts, colors, fonts and images."
---

# Skill: core-figma-extractor

## Run

```
python ${CLAUDE_PLUGIN_ROOT}/scripts/figma_extract.py "<figma-url>" .rp/design --token <FIGMA_TOKEN>
```

- A URL with `?node-id=` extracts only that node (frame, section or page). Without it, every top-level frame.
- Output: `design.json`, `frames/<slug>.png` (rendered frame), `images/<imageRef>.*` (image fills),
  `exports/<frame>--<name>.<fmt>` (nodes the designer marked for export — logos, icons).
- `--scale 2` gives sharper frame renders for QA (bigger files).

## design.json

```jsonc
{
  "source": "figma",
  "frames": [{
    "id": "1:2", "name": "Home - Desktop", "slug": "home-desktop", "width": 1440, "height": 5200,
    "png": "frames/home-desktop.png",
    "texts":  [{"text": "...", "font": "Inter", "weight": 700, "size": 48, "line_height": 56,
                "color": "#111111", "x": 120, "y": 200, "w": 600, "h": 112}],
    "images": [{"name": "hero-bg", "file": "images/ab12.png", "x": 0, "y": 0, "w": 1440, "h": 800}]
  }],
  "colors":  [{"hex": "#0a2540", "count": 84}],
  "fonts":   [{"family": "Inter", "weight": 400, "size": 16, "count": 120}],
  "images":  [{"file": "images/ab12.png", "ref": "ab12"}],
  "exports": [{"name": "logo", "file": "exports/home-desktop--logo.svg"}]
}
```

Coordinates are relative to the frame's top-left. Texts and images are sorted top → bottom.

## How agents use it

1. **Look at `frames/*.png` first** — it is the truth for layout; `design.json` gives exact values.
2. Sections = horizontal bands of the frame; use text/image `y` ranges to find band boundaries.
3. Tokens: the most frequent colors → primary/secondary/text/background; the most frequent
   font sizes → heading scale and body size. Map them to the builder's globals, never hard-code.
4. Texts: use them verbatim. Never invent copy or use lorem ipsum.
5. Images: look up `file` in `media-map.json` to get the WordPress attachment id/url.
6. Frames named `... Mobile` / `... Tablet` are responsive variants of the same page, not new pages.

## Fallback

If no token is available but the Figma MCP tools are connected in the session, use them to get
the node tree and frame screenshots, and write the same `design.json` shape by hand.
