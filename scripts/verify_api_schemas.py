import yaml
import sys
import os
import re
from pathlib import Path
from typing import Dict, Any, List

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent.absolute()

def get_pydantic_fields(file_path: Path, model_name: str) -> List[str]:
    """Extract fields from a Pydantic model in a file using regex (static analysis)."""
    if not file_path.exists():
        return []
        
    with open(file_path, 'r') as f:
        content = f.read()
        
    # Find the class definition
    pattern = rf"class {model_name}\(.*?BaseModel.*?\):(.*?)(?=\nclass|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return []
        
    body = match.group(1)
    # Extract fields (assuming typical Pydantic field: type = ...)
    fields = re.findall(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:", body, re.MULTILINE)
    return fields

def verify_service(service_name: str, response_py: Path, master_fields: List[str]):
    """Verify that a service's APIResponse has all the expected fields."""
    if not response_py.exists():
        print(f"❌ {service_name}: response.py NOT FOUND at {response_py}")
        return False
        
    fields = get_pydantic_fields(response_py, "APIResponse")
    if not fields:
        print(f"❌ {service_name}: Could not find APIResponse model in {response_py}")
        return False
        
    missing = [f for f in master_fields if f not in fields]
    if missing:
        print(f"❌ {service_name}: Missing fields in APIResponse: {missing}")
        return False
    
    print(f"✅ {service_name}: APIResponse is standardized.")
    return True

def main():
    master_spec_path = ROOT_DIR / "specs" / "04_api_spec.yaml"
    with open(master_spec_path, 'r') as f:
        master_spec = yaml.safe_load(f)
        
    master_fields = list(master_spec['components']['schemas']['APIResponse']['properties'].keys())
    print(f"Standard APIResponse fields to verify: {master_fields}")
    
    services = [
        {"name": "api-gateway", "path": "services/api-gateway/app/schemas/response.py"},
        {"name": "ai-analyst", "path": "services/ai-analyst/app/schemas/response.py"},
        {"name": "execution", "path": "services/execution/app/schemas/response.py"},
    ]
    
    all_passed = True
    for service in services:
        full_path = ROOT_DIR / service['path']
        if not verify_service(service['name'], full_path, master_fields):
            all_passed = False
            
    if all_passed:
        print("\n✨ All services have standardized APIResponse structures.")
        sys.exit(0)
    else:
        print("\n💥 Type synchronization check failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
