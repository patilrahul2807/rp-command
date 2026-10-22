---
name: html-project-extractor
description: "Extracting pages, assets and fonts from an HTML project."
---

# Skill: html-project-extractor

Extracting pages, assets and fonts from an HTML project.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
