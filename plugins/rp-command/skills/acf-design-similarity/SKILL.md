---
name: acf-design-similarity
description: "Detect visually similar sections so they reuse one ACF layout with settings instead of new layouts."
---

# Skill: acf-design-similarity

Detect visually similar sections so they reuse one ACF layout with settings instead of new layouts.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
