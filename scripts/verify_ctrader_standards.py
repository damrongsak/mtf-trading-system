import ast
import sys
import os

def check_file(filepath):
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())

    errors = []
    for node in ast.walk(tree):
        # Flag direct .grossProfit access
        if isinstance(node, ast.Attribute) and node.attr == 'grossProfit':
            # Skip if it's inside a getattr call or hasattr check (complex to detect perfectly with AST, 
            # but we can check if the parent is a Call to getattr)
            # For simplicity, we flag all direct access p.grossProfit
            errors.append(f"Line {node.lineno}: Direct access to '.grossProfit' detected. Use 'getattr(obj, \"grossProfit\", 0.0)' instead for cTrader compatibility.")
        
        # Flag direct .swap access
        if isinstance(node, ast.Attribute) and node.attr == 'swap':
             errors.append(f"Line {node.lineno}: Direct access to '.swap' detected. Use 'getattr(obj, \"swap\", 0.0)' for safety.")

    return errors

if __name__ == "__main__":
    target_files = [
        "services/execution/app/adapters/ctrader.py",
        "services/execution/app/adapters/ctrader_connection.py"
    ]
    
    all_errors = []
    for f in target_files:
        if os.path.exists(f):
            file_errors = check_file(f)
            if file_errors:
                print(f"\n❌ Issues found in {f}:")
                for err in file_errors:
                    print(f"  - {err}")
                all_errors.extend(file_errors)
        else:
            print(f"Skipping {f} (not found)")

    if all_errors:
        print("\nTotal issues found: ", len(all_errors))
        # sys.exit(1) # Un-comment to fail CI
    else:
        print("✅ No direct grossProfit/swap access detected in core cTrader files.")
