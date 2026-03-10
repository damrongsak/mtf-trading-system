---
name: skill_creator
description: Meta-skill for autonomous skill authoring, optimization, and validation.
---

# Skill Creator (Meta-Skill)

This skill provides the specialized instructions for authoring new skills that follow the **Agent Skills Phase 2 (Institutional)** standard. Use this to expand system capabilities with maximum reliability.

## 🎯 Authoring Workflow

### 1. Research & Skeleton
- **Discovery**: Identify the task domain and required tools.
- **Initialization**: Create the directory structure (`scripts/`, `references/`).
- **Drafting**: Create the initial `SKILL.md` with required frontmatter.

### 2. Description Optimization (The Loop)
- **Goal**: Ensure the description (Tier 1) triggers only when relevant.
- **Tests**: Mentally simulate "Should Trigger" and "Should NOT Trigger" queries.
- **Refinement**: 
    - Broaden if the agent fails to identify relevance.
    - Narrow if the agent is over-eager (false positives).
    - Limit to 1,024 characters.

### 3. Script & Reference Design
- **Scripts**: Must be non-interactive. Use `uvx` or `npx` for dependency isolation.
- **References**: Extract technical data (API specs, manuals) into `references/REFERENCE.md`.
- **Validation**: Ensure scripts return structured JSON for easy agent parsing.

## 🛠️ Operational Commands
Use the `save_persistent_skill` tool to finalize the creation:

```python
save_persistent_skill(
    name="my_new_skill",
    action="save",
    content="--- \nname: my_new_skill\ndescription: ...\n---\n# Instructions..."
)
```

## ⚠️ Standards Compliance
- **Progressive Disclosure**: Keep `SKILL.md` under 5,000 tokens.
- **Naming**: `snake-case` only.
- **Guardrails**: No skills that bypass institutional risk gates.
