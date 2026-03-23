#!/usr/bin/env python3
"""
MTF Olympus - Strategy Seeding Script
Manual Usage:
    1. Seed all strategies:
       docker compose exec strategy-core python scripts/seed_strategies.py
    2. Seed a specific strategy:
       docker compose exec strategy-core python scripts/seed_strategies.py --strategy quasimodo_v1
    3. Clear all seeded strategies for admin and re-seed:
       docker compose exec strategy-core python scripts/seed_strategies.py --clear

This script synchronizes the physical strategy files (app/strategies/*/strategy.py) 
with the database (SavedStrategy table). It extracts metadata (name, description, defaults)
from the source code using AST for safe parsing.
"""

import os
import sys
import argparse
import ast
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
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
        print(f"  [!] Error parsing metadata: {e}")
    return {}

def seed_strategies(target_strategy=None, clear_existing=False):
    db = SessionLocal()

    try:
        # Get default user (admin)
        result = db.execute(text("SELECT id, username FROM users WHERE username = 'admin'")).fetchone()
        if not result:
            result = db.execute(text("SELECT id, username FROM users LIMIT 1")).fetchone()
        
        if not result:
            print("[-] No user found in DB. Please create a user first.")
            return

        user_id = result.id
        username = result.username
        print(f"[*] Seeding strategies for user: {username} ({user_id})")

        if clear_existing:
            print(f"[*] Clearing existing strategies for user {username}...")
            db.query(SavedStrategy).filter(SavedStrategy.user_id == user_id).delete()
            db.commit()

        if not STRATEGIES_DIR.exists():
            print(f"[-] Strategy directory not found: {STRATEGIES_DIR}")
            return

        for strategy_dir in STRATEGIES_DIR.iterdir():
            if not strategy_dir.is_dir():
                continue
            
            # Skip if filtering and not the target
            if target_strategy and strategy_dir.name != target_strategy:
                continue
                
            strategy_file = strategy_dir / "strategy.py"
            if not strategy_file.exists():
                continue

            print(f"[*] Processing {strategy_dir.name}...")
            
            with open(strategy_file, "r") as f:
                content = f.read()
            
            metadata = parse_metadata(content)
            
            # Support both 'strategy_name' (legacy) and 'name' (v2.1+)
            name = metadata.get("strategy_name") or metadata.get("name") or strategy_dir.name.replace("_", " ").title()
            description = metadata.get("description", "")
            defaults = metadata.get("defaults", {})
            
            # Check if exists
            existing = db.query(SavedStrategy).filter(
                SavedStrategy.name == name,
                SavedStrategy.user_id == user_id
            ).first()

            if existing:
                print(f"  [+] Updating strategy: {name}")
                existing.code = content
                existing.description = description
                # Update parameters with defaults if it was empty
                if not existing.parameters:
                    existing.parameters = defaults
            else:
                print(f"  [+] Creating strategy: {name}")
                new_strat = SavedStrategy(
                    user_id=user_id,
                    name=name,
                    description=description,
                    code=content,
                    is_public=True,
                    parameters=defaults
                )
                db.add(new_strat)
        
        db.commit()
        print("[+] Seeding complete.")

    except Exception as e:
        print(f"[-] Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed strategies from files to DB")
    parser.add_argument("--strategy", type=str, help="Specific strategy directory name to seed")
    parser.add_argument("--clear", action="store_true", help="Clear existing strategies for user before seeding")
    args = parser.parse_args()

    seed_strategies(target_strategy=args.strategy, clear_existing=args.clear)
