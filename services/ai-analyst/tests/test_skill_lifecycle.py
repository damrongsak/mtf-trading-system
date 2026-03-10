
import asyncio
import os
import sys
from pathlib import Path

# Mock globals for direct tool testing
from app.core.globals import services
from app.services.skill import SkillService
from app.tools.skills import SkillManagerTool

async def test_skill_lifecycle():
    print("🚀 Starting Skill Lifecycle Test...")
    
    # Initialize Service
    skills_dir = "skills_test"
    skill_service = SkillService(skills_dir=skills_dir)
    services["skill"] = skill_service
    
    tool = SkillManagerTool()
    skill_name = "test_meta_skill"
    skill_content = """---
name: test_meta_skill
description: A temporary test skill.
---
# Test Content
This is a test of the lifecycle."""

    # 1. Test Save
    print(f"📝 Testing Save Action for '{skill_name}'...")
    save_res = await tool._arun(name=skill_name, action="save", content=skill_content)
    print(f"Result: {save_res}")
    
    skill_path = Path(os.getcwd()) / skills_dir / skill_name / "SKILL.md"
    if skill_path.exists():
        print(f"✅ Skill file created at {skill_path}")
    else:
        print(f"❌ Skill file NOT found at {skill_path}")
        return

    # 2. Test Delete
    print(f"🗑️ Testing Delete Action for '{skill_name}'...")
    del_res = await tool._arun(name=skill_name, action="delete")
    print(f"Result: {del_res}")
    
    if not skill_path.parent.exists():
        print(f"✅ Skill directory removed successfully.")
    else:
        print(f"❌ Skill directory still exists at {skill_path.parent}")
        return

    # Cleanup test dir
    import shutil
    shutil.rmtree(Path(os.getcwd()) / skills_dir)
    print("🧹 Test directory cleaned up.")
    print("✨ Skill Lifecycle Test PASSED.")

if __name__ == "__main__":
    # Add app to path
    sys.path.append(os.getcwd())
    asyncio.run(test_skill_lifecycle())
