---
name: avada-element-decision-matrix
description: "Which Fusion Builder element to use for which design element."
---

# Skill: avada-element-decision-matrix

Which Fusion Builder element to use for which design element.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
