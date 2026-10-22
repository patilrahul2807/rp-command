---
name: core-xd-extractor
description: "Shared Adobe XD extraction: run scripts/xd_extract.py on a .xd file, what it can and cannot recover, and the design.json it writes."
---

# Skill: core-xd-extractor

## Run

```
python ${CLAUDE_PLUGIN_ROOT}/scripts/xd_extract.py "<file.xd>" .rp/design --frames-dir "<exported PNG folder>"
```

An `.xd` file is a zip archive. The script reads:

| Part of the archive | Gives |
|---|---|
| `manifest` | artboard names and bounds |
| `artwork/<artboard>/graphics/graphicContent.agc` | texts (raw text, font family/style/size, color), image fills, solid colors, positions |
| `resources/<uid>` | embedded images → `images/<uid>.png/.jpg/...` |

It writes the same `design.json` shape as `core-figma-extractor` (`source: "xd"`).

## Limits — tell the user

- **XD does not store rendered artboards.** Ask the user to export them from XD
  (*File → Export → All Artboards*, PNG, 1x) and pass the folder as `--frames-dir`.
  Files are matched to artboards by name. Without them `frames/` is empty and visual QA can
  only compare against `preview.png` (if the file has one) — say so in the QA report.
- Vector icons drawn in XD are paths, not files. Ask the user to mark them for export /
  export them as SVG, or rebuild them with the builder's icon widget.
- Positions are approximate for deeply nested groups with rotations; use the PNGs as truth.
- Cloud documents (not saved locally as `.xd`) must be saved as a local `.xd` first.

## How agents use it

Same as `core-figma-extractor` → "How agents use it".
