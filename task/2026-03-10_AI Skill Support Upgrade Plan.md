# AI Skill Support Upgrade Plan (สรุปการอัพเกรดระบบ AI Skill)

แผนงานนี้คือการเพิ่มความสามารถให้ AI Analyst สามารถ **"ค้นพบ (Discover)"**, **"เรียกใช้ (Execute)"** และ **"สร้างทักษะใหม่ (Create)"** ได้ด้วยตัวเองแบบพลอดวัต (Dynamic) ตามแนวทางของ `agentskills.io`

## 🇹🇭 สรุปสาระสำคัญ (Thai Summary)

1.  **การเปิดเผยข้อมูลแบบค่อยเป็นค่อยไป (Progressive Disclosure)**: เพื่อไม่ให้ไฟล์คำสั่ง (Prompt) ใหญ่เกินไป AI จะรับรู้เฉพาะ "สรุปสั้นๆ" ของทักษะที่มีอยู่ก่อน เมื่อจำเป็นต้องใช้จริงๆ ค่อยโหลดคำแนะนำฉบับเต็มขึ้นมา
2.  **เครื่องมือเรียกใช้ทักษะ (ExecuteSkillTool)**: เมื่อ AI ตัดสินใจว่าจะใช้ทักษะใด มันจะใช้เครื่องมือนี้เพื่อรันทักษะนั้นผ่าน **Sub-Agent** (ผู้ช่วยชั่วคราว) เพื่อป้องกันไม่ให้ข้อมูลสับสนกับงานหลัก
3.  **ระบบสร้างทักษะอัตโนมัติ (SkillCreatorAgent)**: AI จะสามารถสร้างโฟลเดอร์ทักษะใหม่ เขียนไฟล์ [SKILL.md](file://wsl.localhost/Ubuntu-24.04/home/dan/workspace/mtf-trading-system/example/skills/template/SKILL.md) และทดสอบ (Evals) ได้ด้วยตัวเอง
    - **เพิ่ม Template**: มีชุดคำสั่งเริ่มต้น (Template) เพื่อให้ Skill ที่สร้างใหม่มีโครงสร้างที่ซับซ้อนและเป็นมาตรฐาน
    - **เชื่อมต่อการค้นหา**: สามารถค้นหาข้อมูลเพิ่มเติมจาก Internet (เช่น `agentskills.io`) หรือเอกสารภายในผ่าน `GoogleSearchTool` เพื่อนำมาประกอบการสร้าง Skill ที่ฉลาดและแม่นยำขึ้น

## User Review Required

> [!IMPORTANT]
> This upgrade introduces a new "Sub-Agent" pattern where the main agent delegates specialized tasks to a transient sub-agent loaded with skill-specific instructions.
>
> **Design Decisions:**
> - Skills are stored as [SKILL.md](file://wsl.localhost/Ubuntu-24.04/home/dan/workspace/mtf-trading-system/example/skills/template/SKILL.md) files in `services/ai-analyst/skills/`.
> - Discovery uses "Progressive Disclosure": Only name/description are in the main prompt.
> - Execution spawns a sub-agent with the full [SKILL.md](file://wsl.localhost/Ubuntu-24.04/home/dan/workspace/mtf-trading-system/example/skills/template/SKILL.md) context.

## Proposed Changes

### [Specs]
#### [MODIFY] [06_ai_agent.md](file:///specs/06_ai_agent.md)
- Define the **Dynamic Agent Skills** architecture.
- Specify the [SKILL.md](file://wsl.localhost/Ubuntu-24.04/home/dan/workspace/mtf-trading-system/example/skills/template/SKILL.md) format (YAML frontmatter + Markdown).
- Define the **Skill Creator** workflow.

---

### [Core Services]
#### [NEW] [skill.py](file:///services/ai-analyst/app/services/skill.py)
- `SkillService`: Class to manage skill discovery and loading.
- `list_skills()`: Returns metadata (name, description) for all available skills.
- `get_skill(name)`: Returns full content and resources for a skill.

#### [MODIFY] [globals.py](file:///services/ai-analyst/app/core/globals.py)
- Register `SkillService` in the global `services` dictionary.

#### [MODIFY] [main.py](file:///services/ai-analyst/app/main.py)
- Initialize `SkillService` during the application lifespan.

---

### [Tools & Agents]
#### [NEW] [skills_execution.py](file:///services/ai-analyst/app/tools/skills_execution.py)
- `ExecuteSkillTool`: Allows the main agent to trigger a skill.
- Logic: Fetches skill from `SkillService`, creates a sub-agent (LangGraph), and executes the task.

#### [NEW] [skill_creator.py](file:///services/ai-analyst/app/agents/skill_creator.py)
- `SkillCreatorAgent`: A specialized agent that follows the `skill-creator` workflow to generate new [SKILL.md](file://wsl.localhost/Ubuntu-24.04/home/dan/workspace/mtf-trading-system/example/skills/template/SKILL.md) files.
- **Enhanced Capabilities**:
    - **Templates**: Uses a default template (`services/ai-analyst/skills/templates/default_skill.md`) to ensure consistent structure for complex skills.
    - **Web Search**: Integrated with `GoogleSearchTool` and `WebReaderTool` to research implementation details from websites like `agentskills.io`.
- Includes tools for drafting files, running tests, and evaluating results.

#### [MODIFY] [universal.py](file:///services/ai-analyst/app/agents/universal.py)
- Dynamically inject "Available Skills" into the system prompt.
- Add `ExecuteSkillTool` to the default tool list.

### [Templates]
#### [NEW] [default_skill.md](file:///services/ai-analyst/skills/templates/default_skill.md)
- A comprehensive template for new skills, including sections for frontmatter, instructions, examples, and guidelines.

---

## Verification Plan

### Automated Tests
- **Unit Tests**:
  - `pytest services/ai-analyst/tests/unit/test_skill_service.py`: Verify parsing of [SKILL.md](file://wsl.localhost/Ubuntu-24.04/home/dan/workspace/mtf-trading-system/example/skills/template/SKILL.md) and metadata extraction.
- **Integration Tests**:
  - `pytest services/ai-analyst/tests/integration/test_skill_execution.py`: Verify that calling `ExecuteSkillTool` correctly triggers a sub-agent.

### Manual Verification
1. **Skill Discovery**:
   - Call `/api/v1/ai/agents/universal/run` with a query like "What skills do you have?".
   - Verify the AI lists the available skills defined in the `skills/` directory.
2. **Skill Creation**:
   - Ask the AI: "Create a new skill called 'market-summarizer' that uses `market_data` to create a concise morning report."
   - Verify that `services/ai-analyst/skills/market-summarizer/SKILL.md` is created.
3. **Skill Execution**:
   - Ask the AI: "Use the market-summarizer skill to summarize today's Gold price action."
   - Verify the sub-agent is triggered and produces the expected output.
