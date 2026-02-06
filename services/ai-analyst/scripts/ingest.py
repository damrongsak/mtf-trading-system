import asyncio
import sys
import argparse
import glob
from pathlib import Path
import logging

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.gemini import GeminiClient
from app.services.rag import RAGService

# Configure Logging
logging.basicConfig(level=logging.ERROR)

async def ingest_file(rag: RAGService, file_path: str, doc_type: str):
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return

    try:
        content = path.read_text(encoding="utf-8")
        filename = path.name
        print(f"📄 Processing: {filename}...")
        
        await rag.ingest_document(filename, content, doc_type)
        print(f"   ✅ Ingested ({len(content)} bytes)")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Ingest Documents into MTF Olympus RAG")
    parser.add_argument("pattern", help="File path or glob pattern (e.g., 'specs/*.md')")
    parser.add_argument("--type", default="spec", help="Document type (spec, guide, research)")
    args = parser.parse_args()

    print(f"🚀 Starting Ingestion for pattern: '{args.pattern}'\n")

    # Expand glob
    # If the user runs this from root, logic needs to be careful about relative paths
    # We assume usage like: docker compose run ... python scripts/ingest.py "specs/*.md"
    # But inside the container, the workspace is mounted. Mapped paths usually match.
    
    files = glob.glob(args.pattern, recursive=True)
    if not files:
        print("⚠️  No files matched the pattern.")
        return

    print(f"Found {len(files)} files.")

    # Connect to Services
    try:
        gemini = GeminiClient()
        rag = RAGService(gemini_client=gemini)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # Process
    for f in files:
        await ingest_file(rag, f, args.type)

    print("\n✨ Ingestion Complete.")

if __name__ == "__main__":
    asyncio.run(main())
