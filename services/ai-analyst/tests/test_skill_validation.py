
import asyncio
import os
import sys
from pathlib import Path

from app.core.globals import services
from app.services.skill import SkillService
from app.tools.skills import SkillManagerTool

async def test_skill_validation():
    print("🚀 Starting Skill Validation Test...")
    
    tool = SkillManagerTool()
    
    # 1. Valid Skill
    print("✅ Testing Valid Skill...")
    valid_content = """---
name: valid-skill
description: This is a valid description.
---
# Instructions"""
    res = await tool._arun(name="valid-skill", action="validate", content=valid_content)
    print(f"Result: {res}")
    assert "SUCCESS" in res

    # 2. Invalid Frontmatter (Missing Name)
    print("❌ Testing Missing Name...")
    invalid_1 = """---
description: Missing name.
---
# Instructions"""
    res = await tool._arun(name="missing-name", action="validate", content=invalid_1)
    print(f"Result: {res}")
    assert "Validation Error" in res

    # 3. Name Mismatch
    print("❌ Testing Name Mismatch...")
    invalid_2 = """---
name: side-skill
description: Name mismatch test.
---
# Instructions"""
    res = await tool._arun(name="main-skill", action="validate", content=invalid_2)
    print(f"Result: {res}")
    assert "does not match requested name" in res

    # 4. Invalid Name Characters
    print("❌ Testing Invalid Characters...")
    invalid_3 = """---
name: Invalid_Name
description: Uppercase and underscore not allowed.
---
# Instructions"""
    res = await tool._arun(name="Invalid_Name", action="validate", content=invalid_3)
    print(f"Result: {res}")
    assert "Validation Error" in res

    # 5. Long Description
    print("❌ Testing Long Description...")
    long_desc = "A" * 1025
    invalid_4 = f"""---
name: long-desc
description: {long_desc}
---
# Instructions"""
    res = await tool._arun(name="long-desc", action="validate", content=invalid_4)
    print(f"Result: {res}")
    assert "1-1024 characters" in res

    print("✨ All Validation Tests PASSED.")

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    asyncio.run(test_skill_validation())
