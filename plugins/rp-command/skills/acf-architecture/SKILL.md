---
name: acf-architecture
description: "Reusable patterns for ACF Pro Flexible Content architecture and PHP template integration — field types, escaping rules, common partials, the clone component library, and registration through the RP Connect bridge. Used by **backend**, **acf-field-creator**, **template-builder** and setup agents."
---

# Skill: ACF Field Architecture

Reusable patterns for ACF Pro Flexible Content architecture and PHP template integration. Used by **backend**, **acf-field-creator**, **template-builder**, and setup agents.

## Configuration

Read existing layouts from `project-config.json` → `theme.existing_fc_layouts`.
Read FC field name from `theme.flexible_content_field`.

## CRITICAL RULE: NO DEFAULT VALUES

**NEVER** set `default_value` to anything other than `""` (empty string) on ANY ACF field.

```php
// CORRECT
'default_value' => '',

// WRONG - NEVER do this
'default_value' => 'Enter your heading here',
'default_value' => 'Lorem ipsum',
```

Empty fields must show nothing — not preset content.

## Core FC Loop (in content-page.php)

The FC loop MUST be wrapped in a `<main>` landmark element for accessibility:

```php
<main id="main-content" role="main">
<?php
if (have_rows('<fc_field>', get_the_ID())) :
    while (have_rows('<fc_field>', get_the_ID())) : the_row();
        get_template_part('template-parts/flex-blocks/' . get_row_layout());
    endwhile;
endif;
?>
</main>
```

- Inside FC templates: `get_sub_field()` (NOT `get_field()`)
- Templates: `template-parts/flex-blocks/{layout_name}.php`

## Common Partials Pattern

Every flex block starts with:

```php
<?php get_template_part('template-parts/common/common', 'section_settings'); ?>
```

Provides: `$sec_id`, `$sec_classes`, `$section_style`

**Why `get_template_part()` instead of `require(locate_template())`:**
- `get_template_part()` is the WordPress-native function for loading template partials
- Supports child theme overrides automatically
- Fires `get_template_part_{$slug}` action hook for extensibility
- Consistent with WordPress template hierarchy conventions

## Clone Component Library

The whole component model is built on ACF **`clone`** fields. Build every FC layout by cloning shared components — **never re-declare heading / media / cta / button fields inline**. Only fields unique to a layout are declared directly.

**A. How clone fields work**

- A `clone` field embeds another field group (or specific fields) into a layout.
- Always use `"display": "seamless"` and `"layout": "block"`. With `seamless`, sub-fields keep their own names — read them with `get_sub_field('heading')`, NOT a nested path.
- Keep `"prefix_label": 0` and `"prefix_name": 0`.
- Clone payload shape for the bridge (`rp/acf-manage-field-groups`):

```json
{ "key": "field_<unique>", "label": "Media", "name": "media", "type": "clone",
  "clone": ["group_media_block"],          // whole-group clone — or ["field_a","field_b"] for a partial clone
  "display": "seamless", "layout": "block", "prefix_label": 0, "prefix_name": 0 }
```

**B. Standard source groups** — create these ONCE per project, then clone them everywhere. Every field `"default_value": ""`.

**Common Section Options** — cloned as `common_settings`

| name | type | choices / notes |
|---|---|---|
| `hide_section` | checkbox | choice `hidden => Hide`, return `value`, vertical |
| `sec_id` | text | |
| `sec_classes` | text | |
| `sec_bg_color` | color_picker | return `string` |
| `section_headings_color` | color_picker | return `string` |
| `section_text_color` | color_picker | return `string` |
| `section_button_bg_color` | color_picker | return `string` |
| `sec_top_mobile` / `sec_top_tablet` / `sec_top_desktop` / `sec_top_big_desktop` | number | padding-top per breakpoint |
| `sec_btm_mobile` / `sec_btm_tablet` / `sec_btm_desktop` / `sec_btm_big_desktop` | number | padding-bottom per breakpoint |

**Media Block** — cloned as `media`

| name | type | choices / notes |
|---|---|---|
| `media_type` | radio | `image => Image`, `video => Video`; return `value`, horizontal |
| `video_type` | radio | `custom => Custom Video`, `third-party => Third Party Video`; return `value`, horizontal |
| `image` | image | return `id` |
| `mobile_img` | image | return `id` |
| `custom_video` | file | return `url` |
| `custom_video_mobile` | file | return `url` |
| `third_party_url` | url | |

**Title/Content/CTA Block** — cloned as `heading_with_content` (whole group), and as `page_heading` / `section_heading` / `cta` (partial clones)

| name | type | choices / notes |
|---|---|---|
| `heading_tag` | select | `h1`..`h6`, `p`, `span`; return `value` |
| `heading` | text | |
| `content` | textarea | |
| `cta` | link | return `array` |
| `social_icon` | image | return `id` |
| `social_link` | text | |

**Button Group** — cloned as `button_group` (a.k.a. `quick_buttons`)

| name | type | notes |
|---|---|---|
| `buttons` | repeater (table layout) | sub-field: `cta` (link, return `array`) |

**C. Standard clone names** (what layouts reference)

| Clone name | Source | Mode |
|---|---|---|
| `common_settings` | Common Section Options (whole group) | seamless/block |
| `media` | Media Block (whole group) | seamless/block |
| `heading_with_content` | Title/Content/CTA Block (whole group) | seamless/block |
| `page_heading` | partial: `heading_tag` + `heading` | seamless/block |
| `section_heading` | partial: `heading_tag` + `heading` + `content` | seamless/block |
| `cta` | partial: `cta` link field | seamless/block |
| `button_group` / `quick_buttons` | Button Group (whole group) | seamless/block |

**D. Template-side:** seamless clones are read with the sub-field's own name inside the FC loop — `get_sub_field('heading')`, `get_sub_field('media_type')`, `get_sub_field('cta')`.

## Field Type Selection

- `text` — short strings (headings, labels)
- `textarea` — multi-line plain text
- `wysiwyg` — rich content (only when formatting truly needed)
- `image` — return format `array` or ID
- `url` / `link` — links
- `repeater` — lists of items
- `post_object` — reference to existing posts
- `gallery` — multiple images
- `select` / `radio` — predefined choices
- `true_false` — toggles

## Escaping Rules (CRITICAL)

```php
esc_html()       // Text content
esc_attr()       // HTML attributes
esc_url()        // URLs
wp_kses_post()   // WYSIWYG content
wp_kses()        // Mixed content with custom allowed tags
```

Never echo raw field data without escaping.

## Image Handling

Use WordPress-native `wp_get_attachment_image()` with `loading="lazy"` for all images. Always pass the `alt` attribute from the ACF image array (or attachment meta).

```php
<?php
$image = get_sub_field('section_image');
if ($image) :
    echo wp_get_attachment_image($image['ID'], 'full', false, [
        'class'   => 'additional-class',
        'loading' => 'lazy',
        'alt'     => !empty($image['alt']) ? $image['alt'] : esc_attr($image['title']),
    ]);
endif;
?>
```

**Why `wp_get_attachment_image()`:** core WP function, auto-generates `srcset`/`sizes`, supports image optimization plugins, no custom functions needed.

## Figma → ACF Decision Tree

### Step 1: Identify Sections
Each full-width block = one FC layout instance.

### Step 2: Check Existing Layouts (from config)
Compare section structure against config's `existing_fc_layouts`.

### Step 3: Reuse vs. Create
- **Reuse** if content structure matches (styling via Section Settings)
- **Create new** only when structure is genuinely different

### Step 4: For New Layouts
1. Choose descriptive `snake_case` name
2. Include section settings fields
3. Create template: `template-parts/flex-blocks/{layout_name}.php`
4. Start with `get_template_part('template-parts/common/common', 'section_settings')`
5. ALL fields have `'default_value' => ''`

### Step 5: Ask When Unsure
Always ask the user before creating new layouts vs. reusing existing.

## Tab Fields (REQUIRED for complex layouts)

Organize fields into Tabs when a layout has 5+ fields:

```php
array(
    'key'       => 'field_<layout>_tab_content',
    'label'     => 'Content',
    'type'      => 'tab',
    'placement' => 'top',
),
// ... content fields ...
array(
    'key'       => 'field_<layout>_tab_settings',
    'label'     => 'Settings',
    'type'      => 'tab',
    'placement' => 'top',
),
// ... settings fields ...
```

Standard tab groups:
- **Content** — headings, text, images, repeaters
- **Settings** — the `common_settings` clone always sits right after the "Section Settings" tab; all content fields live under "Section Content".

## Conditional Logic

Use when a field should only appear based on another field's value:

```php
'conditional_logic' => array(
    array(
        array(
            'field'    => 'field_<layout>_media_type',
            'operator' => '==',
            'value'    => 'video',
        ),
    ),
),
```

Common patterns: show video URL when `media_type=video`, show link fields when `has_button=true`.

## Field Instructions

Every field MUST include `instructions` to guide content managers:

```php
'instructions' => 'Recommended image size: 1200x600px. JPG or WebP format.',
```

## Repeater Table Layout

Use `'layout' => 'table'` for repeaters with 2–3 simple sub-fields (icon grids, social links, stat counters). Use `'layout' => 'block'` for complex items with images + text.

## Registration Method (through the RP Connect bridge)

Field groups and FC layouts are registered on the connected site through the bridge, by dispatching the `rp/acf-manage-field-groups` ability. The JSON field definitions in this skill are the payload shape; never write `acf-json/` files or PHP `acf_add_local_field_group()` registrations by hand.

```json
{ "ability_name": "rp/acf-manage-field-groups",
  "parameters": { "action": "list" | "get" | "create" | "update" | "delete" } }
```

Always `list` / `get` first, then `create` or `update`. The ability's input schema is the source of truth — read it before calling.

### For flexible-content projects (`template_structure == "flexible"`)

Layouts are NOT standalone field groups. Each new layout is added to the **existing** FC field group with the bridge: `get` the group, append the layout to the FC field's `layouts` map (or `create` the FC group if it doesn't exist yet), then `update` the merged group.

```jsonc
// CORRECT — layout lives inside the FC field's layouts map
"layouts": {
  "layout_hero_banner": {
    "key": "layout_hero_banner",
    "name": "hero_banner",
    "label": "Hero Banner",
    "display": "block",          // 'block' for FC rows (NOT 'table'/'row')
    "sub_fields": [ /* ... */ ]
  }
}

// WRONG — a standalone field group won't appear in the FC dropdown
{ "action": "create", "title": "Hero Banner", "fields": [ /* ... */ ] }
```

**FC layout `display` options:**
- `"display": "block"` — fields shown in block format within the FC row (DEFAULT — use this)
- `"display": "table"` — fields shown in table columns (only for layouts with few simple fields)
- `"display": "row"` — fields shown in a compact row

### For standalone field groups (Options Page, unique templates)

```json
{ "action": "create",
  "title": "Layout Title",
  "fields": [ /* ... each with "default_value": "" ... */ ],
  "location": [[{ "param": "page_template", "operator": "==", "value": "..." }]] }
```

## Theme Settings options page (header/footer source of truth)

Site-wide chrome (logo, header CTA, footer copyright + social links) lives on a **Theme Settings** ACF options page, NOT hard-coded in templates. Register the page via `rp/acf-manage-options-pages` (`{"action":"register","page_title":"Theme Settings","menu_slug":"theme-settings"}`), then attach a field group located on it. Canonical fields (each `"default_value": ""`):

- `site_logo` — image
- `header_cta` — link (one link field = title + url + target together)
- `footer_copyright` — text
- `footer_social` — repeater (`icon` image, `url` url)

Read these in `header.php` / `footer.php` with `get_field('<name>', 'option')`.

## Options Pages (Global Fields) — full set

| Page | Location | Notes |
|---|---|---|
| Theme Settings | `options_page == theme-settings` | header/footer chrome (above) |
| General Settings | `options_page == theme-general-settings` | contact info, scripts |

**General Settings** fields: `contact_phone`, `contact_email`, `address` (textarea), `header_scripts` / `footer_scripts` (textarea — raw markup injected in `<head>` / before `</body>`).

Every options-page field also has `"default_value": ""`.

## Per-Page Settings Group

A lightweight settings group located on `post_type == page` for per-page overrides (e.g. header style, hide breadcrumbs). Keep it to toggles and selects; content belongs in FC layouts.
