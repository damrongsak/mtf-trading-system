import abc
import logging
import shutil
import asyncio
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.app_config import config
from app.core.llm_utils import LLMUtils
from app.core.models import IngestionResult
from app.tools.falkordb_client import FalkorDBClient

class BaseIngestor(abc.ABC):
    """Abstract base class for all Olympus ingestors"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self.config = config
        self.client = FalkorDBClient(
            host=config.falkor_host, 
            port=config.falkor_port, 
            graph_name=config.graph_name
        )

    def scan_files(self, extensions: Optional[set] = None) -> List[Path]:
        """Scan for ingestible files in the source directory"""
        if not config.source_dir.exists():
            self.logger.warning(f"Source dir {config.source_dir} not found")
            return []
            
        if extensions is None:
            extensions = {'.md', '.pdf', '.json', '.csv', '.txt'}
            
        files = [
            f for f in config.source_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in extensions 
            and not f.name.startswith('.')
            and not f.name.lower().startswith('readme')
        ]
        self.logger.info(f"Found {len(files)} files to ingest")
        return files

    def archive_file(self, file_path: Path) -> bool:
        """Move processed file to archive folder with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archived_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        archived_path = config.archive_dir / archived_name
        
        try:
            shutil.move(str(file_path), str(archived_path))
            self.logger.info(f"📦 Archived: {file_path.name} → {archived_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to archive {file_path.name}: {e}")
            return False

    def move_to_errors(self, file_path: Path, error_reason: str = "Unknown error") -> bool:
        """Move failed file to errors folder with a reason artifact"""
        error_path = config.error_dir / file_path.name
        meta_path = config.error_dir / f"{file_path.name}.error.json"
        
        try:
            shutil.move(str(file_path), str(error_path))
            
            # Write error metadata
            import json
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "filename": file_path.name,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "ingestor": self.name,
                    "reason": error_reason
                }, f, indent=2)
                
            self.logger.error(f"❌ Moved to errors: {file_path.name} (Reason: {error_reason})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move {file_path.name} to errors: {e}")
            return False

    def execute_to_falkor(self, queries: List[str]) -> Dict[str, Any]:
        """Execute Cypher queries to FalkorDB with pre-deduplication"""
        self.client.connect()
        
        from app.core.query_optimizer import deduplicate_cypher_queries
        
        # Basic validation/cleaning
        initial_valid = []
        for q in queries:
            q = q.strip()
            if q.upper().startswith(('MERGE', 'CREATE', 'SET', 'MATCH')) and len(q) > 10:
                initial_valid.append(q)
        
        if not initial_valid:
            return {"error": "No valid queries to execute", "success": 0, "failed": 0}
            
        # Deduplicate and optimize
        optimized_queries = deduplicate_cypher_queries(initial_valid)
        self.logger.info(f"⚖️ Query Optimization: {len(initial_valid)} → {len(optimized_queries)} queries")
        
        result = self.client.execute_batch(optimized_queries)
        return result

    @abc.abstractmethod
    async def run_pipeline(self, file_path: Path) -> IngestionResult:
        """Execute the ingestion pipeline for a single file"""
        pass

    async def _process_single_file(self, file_path: Path, semaphore: asyncio.Semaphore):
        """Internal helper to process a single file within a semaphore limit"""
        async with semaphore:
            try:
                self.logger.info(f"🧵 Processing: {file_path.name}")
                result = await self.run_pipeline(file_path)
                
                if result.status == "complete":
                    self.archive_file(file_path)
                else:
                    reason = result.error if hasattr(result, 'error') and result.error else "Pipeline reported failure"
                    self.move_to_errors(file_path, reason)
                self.logger.info(f"⏳ Finished {file_path.name}: {result.status}")
                return result
            except Exception as e:
                self.logger.exception(f"Unexpected error processing {file_path.name}: {e}")
                self.move_to_errors(file_path, str(e))
                return None

    def run(self, max_concurrent: int = 5, files: List[Path] = None):
        """Main entry point to process all files in parallel"""
        self.logger.info(f"🎯 Starting Ingestor: {self.name} (Max Parallel: {max_concurrent})")
        if files is None:
            files = self.scan_files()
        
        if not files:
            self.logger.info("No files to process.")
            return

        import asyncio
        async def _run_all():
            semaphore = asyncio.Semaphore(max_concurrent)
            tasks = [self._process_single_file(f, semaphore) for f in files]
            await asyncio.gather(*tasks)

        asyncio.run(_run_all())
