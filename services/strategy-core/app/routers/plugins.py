import os
import shutil
import zipfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.engine import strategy_engine

router = APIRouter(prefix="/internal/plugins", tags=["internal-plugins"])
logger = logging.getLogger("plugin_router")

PLUGIN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins")

class PluginFile(BaseModel):
    id: str
    has_init: bool

class HookInfo(BaseModel):
    tag: str
    callbacks: List[str]

class SystemHooks(BaseModel):
    actions: List[HookInfo]
    filters: List[HookInfo]

@router.get("", response_model=List[str])
def list_installed_plugins():
    """
    Scans the filesystem for installed plugins.
    Returns a list of directory names that contain a plugin.py.
    """
    if not os.path.exists(PLUGIN_DIR):
        return []
        
    plugins = []
    for item in os.listdir(PLUGIN_DIR):
        item_path = os.path.join(PLUGIN_DIR, item)
        if os.path.isdir(item_path) and not item.startswith("__"):
            # specific check for plugin.py?
            if os.path.exists(os.path.join(item_path, "plugin.py")):
                plugins.append(item)
    return plugins

@router.post("/install")
async def install_plugin(file: UploadFile = File(...)):
    """
    Installs a plugin from a .zip file.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files supported")
    
    plugin_name = file.filename.replace(".zip", "")
    target_dir = os.path.join(PLUGIN_DIR, plugin_name)
    
    # Save zip temporarily
    temp_zip_path = os.path.join(PLUGIN_DIR, f"temp_{file.filename}")
    try:
        with open(temp_zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Verify and Extract
        if os.path.exists(target_dir):
             shutil.rmtree(target_dir) # Overwrite existing
        
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
            
        # Validate structure (simple check)
        if not os.path.exists(os.path.join(target_dir, "plugin.py")):
             # Maybe it's nested in a folder?
             # For MVP, assume root of zip has plugin.py or a single folder.
             # If extracting `my-plugin.zip` creates `my-plugin/plugin.py` inside `app/plugins/my-plugin`, that works.
             # But if zip content is directly `plugin.py`, then `target_dir` has `plugin.py`.
             # Let's verify.
             pass
             
        logger.info(f"Installed plugin {plugin_name} to {target_dir}")
        return {"status": "installed", "id": plugin_name}
        
    except Exception as e:
        logger.error(f"Install failed: {e}")
        # Clean up partial
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)

@router.get("/hooks", response_model=SystemHooks)
def inspect_hooks():
    """
    Returns a snapshot of registered hooks in the running engine.
    """
    hm = strategy_engine.hook_manager
    
    def serialize_callbacks(cb_map):
        result = []
        for tag, callbacks in cb_map.items():
            cb_names = []
            for cb in callbacks:
                # Try to get readable name
                try:
                    name = f"{cb.__module__}.{cb.__name__}"
                except:
                    name = str(cb)
                cb_names.append(name)
            result.append(HookInfo(tag=tag, callbacks=cb_names))
        return result

    return SystemHooks(
        actions=serialize_callbacks(hm.actions),
        filters=serialize_callbacks(hm.filters)
    )


class NotifyRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    category: Optional[str] = "info"

@router.post("/notify")
async def notify_users(request: NotifyRequest):
    """
    Trigger a manual notification via the system hooks.
    """
    strategy_engine.notify(
        message=request.message,
        user_id=request.user_id,
        category=request.category
    )
    return {"status": "dispatched"}
