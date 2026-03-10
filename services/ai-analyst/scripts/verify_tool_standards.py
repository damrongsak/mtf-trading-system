import os
import ast
import sys

def check_tool_file(filepath):
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    
    errors = []
    has_base_tool_import = False
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    
    # Check imports
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module == 'app.core.base_tool' and any(alias.name == 'BaseTool' for alias in node.names):
                has_base_tool_import = True
            if node.module == 'langchain_core.tools' and any(alias.name == 'BaseTool' for alias in node.names):
                errors.append("❌ Legacy import: 'langchain_core.tools.BaseTool' used instead of 'app.core.base_tool.BaseTool'")

    for cls in classes:
        # Check inheritance
        is_subclass = any(isinstance(base, ast.Name) and base.id == 'BaseTool' for base in cls.bases)
        if not is_subclass:
            continue

        if not has_base_tool_import:
             errors.append(f"❌ Class '{cls.name}' inherits from BaseTool but missing correct import")

        # Check methods
        methods = [node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        has_run_tool = any(m.name == 'run_tool' for m in methods)
        has_legacy_run = any(m.name in ['_run', '_arun', 'run'] for m in methods)

        if not has_run_tool:
            errors.append(f"❌ Class '{cls.name}' missing 'run_tool' method")
        if has_legacy_run:
            errors.append(f"❌ Class '{cls.name}' implements legacy '_run', 'run' or '_arun' method")

    return errors

def main():
    tools_dir = "app/tools"
    if not os.path.exists(tools_dir):
        print(f"Directory {tools_dir} not found. Run from service root.")
        sys.exit(1)

    all_errors = {}
    for filename in os.listdir(tools_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            filepath = os.path.join(tools_dir, filename)
            errors = check_tool_file(filepath)
            if errors:
                all_errors[filename] = errors

    if all_errors:
        print("\n🚨 Tool Standard Violations Found:")
        for file, errors in all_errors.items():
            print(f"\n📄 {file}:")
            for err in errors:
                print(f"  {err}")
        sys.exit(1)
    else:
        print("\n✅ All tools in app/tools comply with Olympus resilience standards.")

if __name__ == "__main__":
    main()
