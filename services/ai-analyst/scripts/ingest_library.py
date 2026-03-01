import asyncio
import os
import sys
from pathlib import Path

# Add app to path for imports
# Assuming script is in services/ai-analyst/scripts/
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag import RAGService
from app.services.gemini import GeminiClient

async def ingest_library(target_file: str = None):
    print("📚 Starting Quant Library Ingestion...")
    
    try:
        gemini = GeminiClient()
        rag = RAGService(gemini)
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # Path to books
    docs_dir = Path(__file__).parent.parent / "docs"
    
    if not docs_dir.exists():
        print(f"❌ Docs directory not found at {docs_dir}")
        return

    # List of files to process
    if target_file:
        md_files = [target_file] if (docs_dir / target_file).exists() else []
        if not md_files:
            print(f"⚠️ Target file {target_file} not found in {docs_dir}.")
            return
    else:
        md_files = [f for f in os.listdir(docs_dir) if f.endswith(".md")]
    
    if not md_files:
        print("⚠️ No markdown files found in docs/.")
        return

    print(f"Found {len(md_files)} books to process.")
    
    count = 0
    for filename in md_files:
        file_path = docs_dir / filename
        print(f"📖 Ingesting: {filename}...")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Use the specialized library ingestion method
            # This uses deterministic IDs to prevent duplicates
            await rag.ingest_library_book(
                filename=filename,
                content=content,
                metadata={"source": "quant_books_2026"}
            )
            count += 1
            print(f"✅ Success: {filename}")
        except Exception as e:
            print(f"❌ Failed to ingest {filename}: {e}")

    print(f"\n✨ Done! Processed {count} books into 'quant_library'.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(ingest_library(target))
