---
name: elementor-fast-build-qa
description: "Fast QA pass for Elementor builds when full section QA is not required."
---

# Skill: elementor-fast-build-qa

Fast QA pass for Elementor builds when full section QA is not required.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
