---
name: html-elementor-fidelity
description: "Fidelity rules for HTML -> Elementor rebuilds."
---

# Skill: html-elementor-fidelity

Fidelity rules for HTML -> Elementor rebuilds.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
