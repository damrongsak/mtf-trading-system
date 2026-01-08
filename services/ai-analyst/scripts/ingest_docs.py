import asyncio
import os
import sys
from pathlib import Path

# Add parent dir to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag import RAGService
from app.services.gemini import GeminiClient

async def ingest_specs():
    print("🚀 Starting Documentation Ingestion...")
    
    # Initialize Service
    try:
        gemini = GeminiClient()
        rag = RAGService(gemini)
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        return

    # Path to specs
    # Assuming script is in services/ai-analyst/scripts/
    # And specs are in root/specs/
    root_dir = Path(__file__).parent.parent.parent.parent
    specs_dir = root_dir / "specs"
    
    if not specs_dir.exists():
        print(f"❌ Specs directory not found at {specs_dir}")
        return

    count = 0
    
    # Walk directory
    for root, _, files in os.walk(specs_dir):
        for file in files:
            if file.endswith((".md", ".yaml", ".yml")):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(specs_dir)
                
                print(f"📄 Processing {relative_path}...")
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # Add file context to content
                    full_content = f"Filename: {file}\nPath: specs/{relative_path}\nContent:\n{content}"
                    
                    await rag.ingest_document(
                        filename=str(relative_path),
                        content=full_content,
                        doc_type="spec"
                    )
                    count += 1
                except Exception as e:
                    print(f"⚠️ Failed to ingest {file}: {e}")

    # Also ingest GEMINI.md
    gemini_md = root_dir / "GEMINI.md"
    if gemini_md.exists():
         print(f"📄 Processing GEMINI.md...")
         try:
            with open(gemini_md, "r", encoding="utf-8") as f:
                content = f.read()
            full_content = f"Filename: GEMINI.md\nContent:\n{content}"
            await rag.ingest_document("GEMINI.md", full_content, "guide")
            count += 1
         except Exception as e:
            print(f"⚠️ Failed to ingest GEMINI.md: {e}")

    print(f"✅ Ingestion Complete. Processed {count} documents.")

if __name__ == "__main__":
    asyncio.run(ingest_specs())
