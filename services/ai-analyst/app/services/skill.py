import os
import yaml
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SkillMetadata(Dict):
    name: str
    description: str
    path: str

class SkillService:
    def __init__(self, skills_dir: str = "skills"):
        # skills_dir is relative to the service root
        self.base_dir = Path(os.getcwd()) / skills_dir
        self.templates_dir = self.base_dir / "templates"
        self._cache: List[Dict[str, str]] = []
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> List[Dict[str, str]]:
        """List metadata for all available skills (cached)."""
        if self._cache:
            return self._cache

        skills = []
        for skill_dir in self.base_dir.iterdir():
            if skill_dir.is_dir() and skill_dir.name != "templates":
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    metadata = self._parse_metadata(skill_file)
                    if metadata:
                        metadata["path"] = str(skill_file)
                        skills.append(metadata)
        
        self._cache = skills
        return skills

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Get full details of a specific skill including references."""
        skill_dir = self.base_dir / name
        skill_file = skill_dir / "SKILL.md"
        ref_dir = skill_dir / "references"
        
        if not skill_file.exists():
            return None
            
        metadata = self._parse_metadata(skill_file)
        if not metadata:
            return None
            
        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract instructions (part after frontmatter)
        parts = content.split("---")
        instructions = parts[2].strip() if len(parts) >= 3 else ""
        
        # Load references if they exist
        references = []
        if ref_dir.exists():
            for ref_file in ref_dir.glob("*.md"):
                try:
                    with open(ref_file, "r", encoding="utf-8") as f:
                        references.append(f"Reference ({ref_file.name}):\n{f.read()}")
                except Exception as e:
                    logger.error(f"Error reading reference {ref_file}: {e}")

        return {
            "metadata": metadata,
            "instructions": instructions,
            "references": "\n\n".join(references),
            "full_content": content,
            "path": str(skill_file)
        }

    def _parse_metadata(self, skill_file: Path) -> Optional[Dict[str, str]]:
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            if not content.startswith("---"):
                return None
                
            parts = content.split("---")
            if len(parts) < 3:
                return None
                
            metadata = yaml.safe_load(parts[1])
            return {
                "name": metadata.get("name", ""),
                "description": metadata.get("description", "")
            }
        except Exception as e:
            logger.error(f"Error parsing metadata from {skill_file}: {e}")
            return None

    async def save_skill(self, name: str, content: str) -> str:
        """Save a new skill or update an existing one with full skeleton."""
        skill_dir = self.base_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Create agentskills.io skeleton
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)
        (skill_dir / "assets").mkdir(exist_ok=True)
        
        skill_file = skill_dir / "SKILL.md"
        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Invalidate cache
        self._cache = []
        logger.info(f"Saved skill '{name}' to disk and initialized directory skeleton.")
        
        return str(skill_file)
