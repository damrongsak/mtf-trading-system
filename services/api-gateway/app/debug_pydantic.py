import sys
import os
sys.path.append(os.getcwd())

try:
    from app.routers import auth
    print("Imported auth successfully")
except Exception as e:
    print(f"Error importing auth: {e}")
    import traceback
    traceback.print_exc()
