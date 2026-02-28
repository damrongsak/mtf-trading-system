import re
import asyncio
from pathlib import Path
from typing import List, Dict
import os

class QuantMarkdownSplitter:
    """
    Advanced Splitter for Quant books
    - Splits by Markdown Headers (##, ###)
    - Preserves Code Blocks within the same chunk if possible
    - Cleans PDF artifacts (Page numbers, extra spaces, etc.)
    """
    def __init__(self, max_chunk_size: int = 3000, chunk_overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def clean_text(self, text: str) -> str:
        """Clean noise artifacts from PDF-to-Markdown conversion."""
        # 1. Remove Form Feed characters (common in PDF conversions)
        text = text.replace('\x0c', '') # \x0c is the Form Feed character
        
        # 2. Remove Page numbers (e.g., "Page 12", or standalone numbers on new lines)
        text = re.sub(r'(?i)^\s*page\s+\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # 3. Handle excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 4. Remove common book headers/footers (can be extended)
        # Examples:
        # text = re.sub(r'(?i)advances in financial machine learning', '', text)
        
        return text.strip()

    def split_text(self, text: str) -> List[str]:
        text = self.clean_text(text)
        chunks = []
        
        # Split by Markdown Headers (Level 2 and 3)
        # Using lookahead to keep the headers in the resulting sections
        sections = re.split(r'(?=\n#{2,3}\s)', text)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # If a section is too large, split it further by paragraphs or sub-headers
            if len(section) > self.max_chunk_size:
                sub_sections = self._split_large_section(section)
                chunks.extend(sub_sections)
            else:
                chunks.append(section)
                
        return chunks

    def _split_large_section(self, section: str) -> List[str]:
        """Split a large section into smaller chunks while trying to preserve paragraphs and code blocks."""
        chunks = []
        paragraphs = section.split('\n\n')
        current_chunk = ""
        
        for p in paragraphs:
            # If single paragraph is larger than max_chunk_size (rare but possible with large code blocks)
            if len(p) > self.max_chunk_size:
                # If we have something in current_chunk, flush it
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split the huge paragraph by line if it's too big
                lines = p.split('\n')
                line_chunk = ""
                for line in lines:
                    if len(line_chunk) + len(line) + 1 < self.max_chunk_size:
                        line_chunk += line + "\n"
                    else:
                        if line_chunk: chunks.append(line_chunk.strip())
                        line_chunk = line + "\n"
                if line_chunk: chunks.append(line_chunk.strip())
                continue

            if len(current_chunk) + len(p) + 2 < self.max_chunk_size:
                current_chunk += p + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

async def test_on_real_book(file_path: str):
    print(f"--- Testing splitter on: {os.path.basename(file_path)} ---")
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        splitter = QuantMarkdownSplitter(max_chunk_size=3000)
        
        chunks = splitter.split_text(content)
        print(f"✅ Success! Total chunks: {len(chunks)}")
        
        # Show some statistics
        lengths = [len(c) for c in chunks]
        avg_len = sum(lengths) / len(chunks) if chunks else 0
        max_len = max(lengths) if lengths else 0
        
        print(f"Stats: Avg Length={avg_len:.0f}, Max Length={max_len}")
        
        # Print a few samples to verify logic
        if len(chunks) > 5:
            print("\n[Sample Chunk 2 (Likely Introduction/Header)]")
            print("-" * 40)
            print(chunks[1][:1000] + ("..." if len(chunks[1]) > 1000 else ""))
            
            print("\n[Sample Chunk 5 (Deeper Content)]")
            print("-" * 40)
            print(chunks[4][:1000] + ("..." if len(chunks[4]) > 1000 else ""))
            
            # Find a chunk with a code block if possible
            code_chunk = next((c for c in chunks if "```" in c), None)
            if code_chunk:
                print("\n[Sample Chunk with CODE BLOCK]")
                print("-" * 40)
                print(code_chunk[:1500] + "...")
            else:
                print("\n(No code blocks found in top chunks)")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Default test file from the docs
    import sys
    default_book = "/home/dan/workspace/mtf-trading-system/services/ai-analyst/docs/Algorithmic Trading - Winning Strategies and Their Rationale 2013.md"
    target_file = sys.argv[1] if len(sys.argv) > 1 else default_book
    
    asyncio.run(test_on_real_book(target_file))
