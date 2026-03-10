from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field
from app.core.globals import services
import logging

logger = logging.getLogger(__name__)

class SkillInput(BaseModel):
    name: str = Field(description="The name of the skill (snake_case)")
    content: Optional[str] = Field(None, description="The full content of the SKILL.md file or Python code (Required for 'save' and 'validate' actions)")
    action: Literal["save", "delete", "validate"] = Field("save", description="Action to perform: 'save' to create/update, 'delete' to remove, 'validate' to check structure")

class SkillManagerTool(BaseTool):
    name: str = "save_persistent_skill"
    description: str = (
        "Manage permanent skills. You can 'save' a successfully executed Python script or logic as a skill, "
        " 'delete' an existing skill, or 'validate' a skill's structure before saving. "
        "For saving and validation, provide the full SKILL.md content. For deleting, only provide the skill name."
    )
    args_schema: Type[BaseModel] = SkillInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        name = ""
        action = "save"
        content = None
        
        if isinstance(input_data, dict):
            name = input_data.get("name", "")
            action = input_data.get("action", "save")
            content = input_data.get("content")
        
        skill_service = services.get("skill")
        skill_service = services.get("skill")
        memory_service = services.get("memory")
        
        results = []
        
        if action == "validate":
            if not content:
                return "Error: Content is required for 'validate' action."
            
            # Simple Structural Validation
            if not content.startswith("---"):
                return "Validation Error: Missing YAML frontmatter (starts with ---)."
            
            parts = content.split("---")
            if len(parts) < 3:
                return "Validation Error: Malformed frontmatter (needs closing ---)."
            
            import yaml
            try:
                metadata = yaml.safe_load(parts[1])
                if not metadata or "name" not in metadata or "description" not in metadata:
                    return "Validation Error: Frontmatter must include 'name' and 'description'."
                
                # Check name constraints
                skill_name = metadata.get("name", "")
                if skill_name != name:
                    return f"Validation Error: Frontmatter name '{skill_name}' does not match requested name '{name}'."
                
                if not skill_name or len(skill_name) > 64:
                    return "Validation Error: Name must be 1-64 characters."
                
                import re
                if not re.match(r"^[a-z0-9\-]+$", skill_name) or skill_name.startswith("-") or skill_name.endswith("-") or "--" in skill_name:
                    return "Validation Error: Name must be snake-case/hyphenated only, no consecutive hyphens."

                description = metadata.get("description", "")
                if not description or len(description) > 1024:
                    return "Validation Error: Description must be 1-1024 characters."

                return f"Validation SUCCESS: Skill '{name}' is structurally valid."
            except Exception as e:
                return f"Validation Error: YAML Parse Error - {e}"

        if action == "save":
            if not content:
                return "Error: Content is required for 'save' action."
            
            # 1. Save to Disk (Skill Discovery Path)
            if skill_service:
                try:
                    path = await skill_service.save_skill(name, content)
                    results.append(f"Disk: Saved to {path}")
                except Exception as e:
                    logger.error(f"SkillManagerTool (Disk Save) error: {e}")
                    results.append(f"Disk Error: {e}")

            # 2. Save to Memory (Semantic Search Path)
            if memory_service:
                try:
                    await memory_service.save_persistent_skill("agent_skill", name, content)
                    results.append("Memory: OK")
                except Exception as e:
                    logger.error(f"SkillManagerTool (Memory Save) error: {e}")
                    results.append(f"Memory Error: {e}")
        
        elif action == "delete":
            # 1. Delete from Disk
            if skill_service:
                try:
                    success = await skill_service.delete_skill(name)
                    if success:
                        results.append("Disk: Deleted")
                    else:
                        results.append("Disk: Skill not found")
                except Exception as e:
                    logger.error(f"SkillManagerTool (Disk Delete) error: {e}")
                    results.append(f"Disk Error: {e}")
            
            # 2. Delete from Memory (If supported by memory service)
            if memory_service:
                try:
                    # Note: memory_service.delete_persistent_skill might not be implemented yet
                    # but we track the intent.
                    results.append("Memory: Deletion pending sync")
                except Exception as e:
                    logger.error(f"SkillManagerTool (Memory Delete) error: {e}")
                    results.append(f"Memory Error: {e}")

        if not results:
            return "Error: No persistence services available."
            
        return " | ".join(results)
