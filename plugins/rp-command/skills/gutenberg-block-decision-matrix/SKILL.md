---
name: gutenberg-block-decision-matrix
description: "When to use a core block, a pattern, or a custom block."
---

# Skill: gutenberg-block-decision-matrix

When to use a core block, a pattern, or a custom block.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
