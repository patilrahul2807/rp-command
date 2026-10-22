---
name: qa-html-report
description: "Format of the QA HTML report."
---

# Skill: qa-html-report

Format of the QA HTML report.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
