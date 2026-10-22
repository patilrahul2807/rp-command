---
name: html-deploy
description: "Deploying a theme to staging, including Basic-Auth staging sites."
---

# Skill: html-deploy

Deploying a theme to staging, including Basic-Auth staging sites.

## Configuration

Read project settings from `project-config.json`.

## Rules

- Follow `rp-core-rules`.
- Keep output deterministic: same input, same result.

## Procedure

1. Read the inputs named by the calling agent.
2. Apply the rules in this skill.
3. Return results in the format the calling agent expects.
