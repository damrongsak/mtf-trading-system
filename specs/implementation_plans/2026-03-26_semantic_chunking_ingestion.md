# Implementation Plan: Semantic Chunking for Knowledge Ingestion

**Date:** 2026-03-26
**Status:** DRAFT
**Module:** `knowledge-ingestor`

## 1. Overview
The current chunking mechanism in `knowledge-ingestor` (`HierarchicalIngestor`) uses a naive regex to split by markdown headers (`##`) and a fixed character limit (15,000 chars). This can lead to context loss if a logical topic spans across a split or if headers are missing.

**Semantic Chunking** aims to split documents based on meaning and logical structure, ensuring that related concepts stay together for better GraphRAG extraction.

## 2. Proposed Changes

### 2.1. New Core Component: `SemanticChunker`
- **Location:** `services/knowledge-ingestor/app/core/semantic_chunker.py`
- **Logic:**
    1. **Structural Split:** First split by Markdown headers (#, ##, ###).
    2. **Recursive Refinement:** If a chunk is still too large (> 10,000 chars), use a recursive character splitter (splitting by paragraphs, then sentences).
    3. **LLM-Assisted Boundary Detection (Optional/Phase 2):** For critical large chunks, use a lightweight LLM call to identify the best "topic shift" line to split on.
    4. **Overlapping Context:** Implement a 10-15% overlap between chunks to maintain continuity.

### 2.2. Update `HierarchicalIngestor`
- Replace `_chunk_by_headings` with `SemanticChunker.split_text()`.
- Ensure metadata reflects the new chunking strategy.

### 2.3. Spec Impacts
- **`specs/06_ai_agent.md`**: Update Section 2.8 (Knowledge Graph Ingestion) to include Semantic Chunking as a requirement for high-quality ingestion.

## 3. Implementation Steps

1.  **Step 1: Update Spec**: Add Semantic Chunking requirement to `specs/06_ai_agent.md`.
2.  **Step 2: Create `SemanticChunker`**: Implement the splitting logic in a dedicated utility class.
3.  **Step 3: Refactor `HierarchicalIngestor`**: Integrate the new chunker.
4.  **Step 4: Verification**: Test with a large document (e.g., one of the books in `example/`) and verify node connectivity in FalkorDB.

## 4. Quality Gates
- **Gate 1**: Unit tests for `SemanticChunker` with various markdown structures.
- **Gate 2**: Integration test verifying that a large file ingestion completes without `task_id` collisions or property corruption.
- **Gate 3**: Zero `ruff` or `mypy` errors in the new files.
