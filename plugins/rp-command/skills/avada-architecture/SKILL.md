---
name: avada-architecture
description: "Avada / Fusion Builder page architecture and the rp/avada-* abilities: global options, page settings, containers → columns → elements, library items and layouts (header/footer)."
---

# Skill: avada-architecture

## Abilities (through the RP Connect bridge — inspect the schema before each first use)

| Ability | Use |
|---|---|
| `rp/get-builder-info` | confirm Avada + Fusion Builder are active, versions |
| `rp/avada-manage-global-options` | `read` / `write` global options (colors, typography, layout width) |
| `rp/avada-element-registry` | list Fusion elements and their params (`element`, `with_params`, `search`) |
| `rp/avada-validate-element` | validate one element + params before writing (`strict: true`) |
| `rp/avada-manage-page-settings` | per-page options, `enable_builder`, page `custom_css` |
| `rp/avada-manage-library` | reusable containers/columns/elements (`list/get/create/delete/consumers`) |
| `rp/avada-manage-layouts` | Avada Layouts: header / footer / page title sections |
| `rp/build-page` with `builder: "avada"` | write a page's element tree |
| `rp/create-page` | create the page first (draft) |
| `rp/avada-clear-cache` | after every write batch |

## Structure

Page content is a tree: **container → row → column(s) → elements**. Avada stores it as
`[fusion_builder_container][fusion_builder_row][fusion_builder_column type="1_2"]...` shortcodes
in `post_content`; always write through `rp/build-page`, never hand-edit shortcodes.

- One design section = one container. Container width/padding from the design; background
  image/color on the container.
- Column widths use Avada fractions (`1_1`, `1_2`, `1_3`, `2_3`, `1_4`, `3_4`, `1_5`…). Pick the
  nearest fraction to the design's column ratio.
- Responsive: set column `type_medium` / `type_small` and element visibility instead of
  separate mobile containers, unless the mobile frame is structurally different.

## Globals first

1. Read global options. Map design colors → Avada color palette slots (`color1`…`color8`),
   fonts → typography sets (H1–H6, body, buttons), container width → site width.
2. Write them with `rp/avada-manage-global-options`, then reference globals in elements
   (e.g. `var(--awb-color1)`) instead of hex values.

## Header / footer

Build them as Avada Layout sections (`rp/avada-manage-layouts`, `object: "section"`), assign
to the global layout. Repeated blocks (CTA band, newsletter) → library items, reused by id.

## Rules

- Validate every element with `rp/avada-validate-element` before `rp/build-page`.
- Images from `media-map.json` (attachment id + url) — no hotlinks.
- No `custom_css` unless no element param can achieve the style; scope it to the container class.
- `rp/avada-clear-cache` after each page.
