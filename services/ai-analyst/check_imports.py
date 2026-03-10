import os
import importlib
import sys

# Add the current directory to path
sys.path.append(os.getcwd())

def check_imports(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                module_path = os.path.relpath(os.path.join(root, file), directory)
                module_name = module_path.replace(os.path.sep, ".").replace(".py", "")
                full_module_name = f"app.{module_name}" if "app" not in module_name else module_name
                
                try:
                    importlib.import_module(full_module_name)
                    # print(f"✅ {full_module_name}")
                except ImportError as e:
                    print(f"❌ {full_module_name}: {e}")
                except Exception as e:
                    # Ignore other errors like missing settings for now, focus on ImportError
                    pass

if __name__ == "__main__":
    check_imports("app")
