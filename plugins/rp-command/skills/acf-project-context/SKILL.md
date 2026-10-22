---
name: acf-project-context
description: "Where project-config.json lives and which keys the ACF pipeline reads."
---

# Skill: acf-project-context

Where project-config.json lives and which keys the ACF pipeline reads.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
