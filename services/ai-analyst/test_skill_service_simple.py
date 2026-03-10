import asyncio
import os
import sys
from pathlib import Path

# Add the service to path
sys.path.append(os.path.join(os.getcwd(), "services", "ai-analyst"))

from app.services.skill import SkillService

async def test_skill_service():
    print(f"Current Directory: {os.getcwd()}")
    service = SkillService(skills_dir="skills")
    
    # 1. Test Save
    content = "---\nname: test-skill\ndescription: A test skill\n---\n# Instructions"
    path = await service.save_skill("test-skill", content)
    print(f"Saved skill to: {path}")
    
    # 2. Test List
    skills = service.list_skills()
    print(f"Skills list: {skills}")
    
    if any(s['name'] == 'test-skill' for s in skills):
        print("✅ SkillService Save & List: SUCCESS")
    else:
        print("❌ SkillService List: FAILED")

if __name__ == "__main__":
    asyncio.run(test_skill_service())
