---
name: acf-section-specs-schema
description: "JSON schema for a section spec consumed by acf-field-creator and acf-frontend-developer."
---

# Skill: acf-section-specs-schema

JSON schema for a section spec consumed by acf-field-creator and acf-frontend-developer.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
