import asyncio
import os
import sys

# Add the service to path
sys.path.append(os.path.join(os.getcwd(), "services", "ai-analyst"))

from app.core.globals import services
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.skill import SkillService
from app.agents.skill_creator import SkillCreatorAgent
from app.core.bootstrap import bootstrap_tools

async def verify_skill_flow():
    print("🚀 Starting Skill Flow Verification...")
    
    # 1. Initialize dependencies
    services["gemini"] = GeminiClient()
    services["rag"] = RAGService(services["gemini"])
    services["skill"] = SkillService()
    bootstrap_tools()
    
    creator = SkillCreatorAgent(services["gemini"])
    
    # 2. Test Skill Creation
    intent = "Create a skill called 'gold-morning-brief' that summarizes XAUUSD technicals and sentiment for a daily report."
    print(f"📝 Requesting skill creation: {intent}")
    
    result = await creator.run(intent)
    print(f"\n✅ Creator Result:\n{result}\n")
    
    # 3. Verify file exists
    skill_path = os.path.join(os.getcwd(), "services", "ai-analyst", "skills", "gold-morning-brief", "SKILL.md")
    if os.path.exists(skill_path):
        print(f"📂 Verified: {skill_path} created successfully.")
        with open(skill_path, "r") as f:
            print(f"📄 Content Preview:\n{f.read()[:200]}...")
    else:
        print(f"❌ Error: Skill file not found at {skill_path}")

    # 4. Verify Discovery in UniversalAgent
    from app.agents.universal import UniversalAgent
    agent = UniversalAgent(services["rag"], services["gemini"])
    
    print("\n🔍 Verifying Discovery in UniversalAgent...")
    # This should trigger the 'execute_skill' if we ask correctly
    # But for now we just check if it finds the metadata
    skills = services["skill"].list_skills()
    print(f"Loaded Skills: {[s['name'] for s in skills]}")
    
    if any(s['name'] == 'gold-morning-brief' for s in skills):
        print("✅ Discovery Successful!")
    else:
        print("❌ Discovery Failed.")

if __name__ == "__main__":
    asyncio.run(verify_skill_flow())
