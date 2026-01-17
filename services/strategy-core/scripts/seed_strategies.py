import os
import sys
import re
import ast
from pathlib import Path

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base, SessionLocal
from app.models.saved_strategy import SavedStrategy

# Path to strategies relative to this script
STRATEGIES_DIR = Path(os.path.dirname(__file__)) / "../app/strategies"

def parse_metadata(content):
    """
    Extract METADATA dict from python content using AST to avoid imports.
    """
    try:
        tree = ast.parse(content)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "METADATA":
                        # Convert AST dict to python dict
                        return ast.literal_eval(node.value)
    except Exception as e:
        print(f"Error parsing metadata: {e}")
    return {}

def seed_strategies():
    db = SessionLocal()

    try:
        # Get default user (admin) via Raw SQL because User model is not in strategy-core
        result = db.execute(text("SELECT id, username FROM users WHERE username = 'admin'")).fetchone()
        
        if not result:
            # Try getting any user
            result = db.execute(text("SELECT id, username FROM users LIMIT 1")).fetchone()
        
        if not result:
            print("No user found in DB. Please create a user first.")
            return

        user_id = result.id
        username = result.username
        print(f"Seeding strategies for user: {username} ({user_id})")

        # Iterate strategy folders
        if not STRATEGIES_DIR.exists():
            print(f"Strategy directory not found: {STRATEGIES_DIR}")
            return

        for strategy_dir in STRATEGIES_DIR.iterdir():
            if strategy_dir.is_dir() and (strategy_dir / "strategy.py").exists():
                file_path = strategy_dir / "strategy.py"
                print(f"Processing {strategy_dir.name}...")
                
                with open(file_path, "r") as f:
                    content = f.read()
                
                metadata = parse_metadata(content)
                name = metadata.get("strategy_name", strategy_dir.name.replace("_", " ").title())
                description = metadata.get("description", "")
                
                # Check if exists
                existing = db.query(SavedStrategy).filter(
                    SavedStrategy.name == name,
                    SavedStrategy.user_id == user_id
                ).first()

                if existing:
                    print(f"Updating strategy: {name}")
                    existing.code = content
                    existing.code = content
                    # Merge parameters if needed, or just keep existing. 
                    # For a reset, we might want to update.
                    # existing.parameters = {} 
                else:
                    print(f"Creating strategy: {name}")
                    new_strat = SavedStrategy(
                        user_id=user_id,
                        name=name,
                        is_public=True, # Make them public/system templates
                        parameters={}
                    )
                    db.add(new_strat)
        
        db.commit()
        print("Seeding complete.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_strategies()
