# MTF Olympus: Example Skills (agentskills.io)

This directory contains example skills and community-contributed workflows for the MTF Olympus AI Analyst.

## 📁 Directory Structure
Each skill MUST follow the Physical Skeleton standard:
```text
skill-name/
├── SKILL.md           # Required: Frontmatter + Prompt Instructions
├── scripts/           # Optional: Executable code/assets
├── references/        # Optional: Contextual documents
└── assets/           # Optional: Media or output files
```

## 🛠️ Usage
The AI Analyst automatically scans this directory to discover new capabilities. To add a new skill, create a folder here and provide a valid `SKILL.md` file.

## 📜 Standards
- **Progressive Disclosure**: Keep the `description` in `SKILL.md` frontmatter concise.
- **Independence**: Skills should be self-contained within their directory.
- **Reference Injection**: Use the `references/` directory for any large contextual data to keep the prompt clean.
