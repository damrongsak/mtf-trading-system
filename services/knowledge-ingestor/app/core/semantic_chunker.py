"""
Semantic Chunking Utility for Project Olympus
Splits documents based on logical structure and semantic continuity.
"""

import re
import logging
from typing import List

logger = logging.getLogger("SemanticChunker")

class SemanticChunker:
    """
    Splits text into semantically meaningful chunks.
    Prioritizes Markdown headers, then paragraphs, then sentences.
    """

    def __init__(self, chunk_size: int = 12000, chunk_overlap: int = 1000):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Pattern to identify Markdown headers (#, ##, ###, ####)
        self.header_pattern = re.compile(r'(?m)^(#{1,4}\s+.+)$')

    def split_text(self, text: str) -> List[str]:
        """
        Main entry point for splitting text.
        """
        if not text:
            return []

        # 1. First split by highest level headers to get logical sections
        sections = self._split_by_headers(text)
        
        # 2. Further split sections that are too large
        final_chunks = []
        for section in sections:
            if len(section) > self.chunk_size:
                final_chunks.extend(self._recursive_split(section))
            else:
                final_chunks.append(section)

        # 3. Apply overlap if needed (currently simple append for continuity)
        # Note: In a fully semantic version, overlap would be more complex
        
        logger.info(f"📄 Semantic Split: {len(text)} chars → {len(final_chunks)} chunks")
        return final_chunks

    def _split_by_headers(self, text: str) -> List[str]:
        """Splits text by Markdown headers."""
        # Find all header positions
        splits = [m.start() for m in self.header_pattern.finditer(text)]
        
        if not splits:
            return [text]
            
        chunks = []
        last_idx = 0
        for split_idx in splits:
            if split_idx > last_idx:
                chunks.append(text[last_idx:split_idx].strip())
            last_idx = split_idx
        
        chunks.append(text[last_idx:].strip())
        return [c for c in chunks if c]

    def _recursive_split(self, text: str) -> List[str]:
        """
        Recursively splits text by paragraphs, then sentences if still too large.
        """
        if len(text) <= self.chunk_size:
            return [text]

        # Try splitting by paragraphs
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for p in paragraphs:
            if len(current_chunk) + len(p) < self.chunk_size:
                current_chunk += p + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If a single paragraph is larger than chunk_size, split by sentences
                if len(p) > self.chunk_size:
                    sentences = self._split_by_sentences(p)
                    for s in sentences:
                        if len(current_chunk) + len(s) < self.chunk_size:
                            current_chunk += s + " "
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = s + " "
                else:
                    current_chunk = p + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_sentences(self, text: str) -> List[str]:
        """Naive sentence splitter using regex."""
        # Split by . ! or ? followed by whitespace and a capital letter
        sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        return sentence_endings.split(text)
