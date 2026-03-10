---
name: skill_manager
description: Meta-skill for autonomous skill lifecycle management (Create, Optimize, Archive).
---

# Skill Manager (Meta-Skill)

This skill empowers the agent to autonomously evolve its capabilities by creating, refining, and removing specialized workflows (skills) based on session performance and user needs.

## 🎯 Core Objectives
1.  **Discovery**: Identify repetitive complex tasks that should be standardized into a skill.
2.  **Creation**: Use `save_persistent_skill` to create new skills following the **Physical Skeleton** standard.
3.  **Optimization**: Improve existing skills by updating their `SKILL.md` or adding reference materials.
4.  **Archiving**: Remove obsolete or ineffective skills using the `delete` action in `save_persistent_skill`.

## 🛠️ Operational Workflow

### 1. Identify Skill Opportunity
When you find yourself performing a sequence of more than 5 complex tool calls to solve a specific problem (e.g., specialized SMC analysis, custom Monte Carlo variant), consider it a candidate for a new skill.

### 2. Creation Standard
A professional skill MUST contain:
- **`SKILL.md`**: With YAML frontmatter (`name`, `description`) and a clear Markdown body.
- **scripts/**: Any necessary Python logic that should be executed via `execute_skill`.
- **references/**: Supporting documentation or data contracts.

### 3. Using the Tool
```python
# To Save/Update
save_persistent_skill(
    name="my_new_skill",
    action="save",
    content="--- \nname: my_new_skill\ndescription: ...\n---\n# Instructions..."
)

# To Delete
save_persistent_skill(
    name="obsolete_skill",
    action="delete"
)
```

## ⚠️ Guardrails
- **Naming**: Use `snake_case` only.
- **Safety**: Never create skills that bypass safety gates or institutional risk limits.
- **Cleanup**: Periodically list skills and archive those that haven't been used in 10+ sessions or are superseded by core system updates.
