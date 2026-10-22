# RP Connect abilities used by rp-command

Agents reach them through the `rp-wordpress` MCP server: `discover-tools` → `inspect-tool` →
`dispatch-tool`. Read each ability's input schema before the first call.

| Area | Abilities | Used by |
|---|---|---|
| Session | `rp/get-instructions`, `rp/get-site-context`, `rp/get-builder-info` | `/rp-doctor`, `/rp-start` |
| Pages | `rp/create-page`, `rp/update-page`, `rp/list-pages`, `rp/build-page` | page builders |
| Media | `rp/upload-media`, `rp/sideload-image`, `rp/import-tree-images`, `rp/find-media-by-hash` | builders (bulk upload is done by `scripts/wp_upload_media.py`) |
| Theme files | `rp/update-theme-file`, `rp/update-theme-stylesheet`, `rp/list-theme-files`, `rp/read-theme-file` | ACF pipeline |
| ACF | `rp/acf-manage-field-groups`, `rp/acf-manage-options-pages`, `rp/acf-read-write-values`, `rp/acf-field-usage-audit` | ACF pipeline, maint |
| Elementor | `rp/elementor-manage-global-styles-v3`, `rp/elementor-update-global-colors`, `rp/elementor-update-global-typography`, `rp/elementor-get-widget-schema`, `rp/elementor-get-container-schema`, `rp/elementor-validate-widget`, `rp/elementor-upload-svg`, `rp/elementor-create-theme-template`, `rp/elementor-export-page`, `rp/backup-elementor-page` | Elementor pipeline |
| Gutenberg | `rp/gutenberg-manage-theme-json`, `rp/gutenberg-manage-templates`, `rp/gutenberg-manage-template-parts`, `rp/gutenberg-manage-patterns`, `rp/gutenberg-register-block`, `rp/gutenberg-validate-blocks` | Gutenberg pipeline |
| Avada | `rp/avada-manage-global-options`, `rp/avada-element-registry`, `rp/avada-validate-element`, `rp/avada-manage-page-settings`, `rp/avada-manage-library`, `rp/avada-manage-layouts`, `rp/avada-clear-cache` | Avada pipeline |
| Menus | `rp/create-menu`, `rp/create-menu-item`, `rp/assign-menu-location` | builders |
| Safety | `rp/get-post-state`, `rp/restore-post-state`, `rp/list-backups` | all writers |

**Not available over MCP** (RP Connect withholds them): plugin install/activate/list (`rp/install-plugin`,
`rp/activate-plugin`, …), users, options, and `rp/execute-php`. Missing plugins are installed
by the user in wp-admin; `/rp-start` tells them what is needed.
