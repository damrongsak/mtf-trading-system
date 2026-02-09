from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.database import get_db
from app.models.plugins import Plugin, UserPlugin, AuditLog, PluginCategory
from app.models.user import User
from app.security import get_current_user

router = APIRouter(prefix="/plugins", tags=["plugins"])

# --- Schemas ---

class PluginResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    author: Optional[str]
    version: str
    category: PluginCategory
    base_config_schema: dict
    is_active: bool = False
    
    class Config:
        from_attributes = True

class PluginConfigUpdate(BaseModel):
    config_overrides: dict

# --- Endpoints ---

@router.get("", response_model=List[PluginResponse])
def list_plugins(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all available plugins and their activation status for the current user."""
    plugins = db.query(Plugin).all()
    
    # Get user activations
    activations = db.query(UserPlugin).filter(UserPlugin.user_id == current_user.id).all()
    active_map = {up.plugin_id: up.is_active for up in activations}
    
    response = []
    for p in plugins:
        resp = PluginResponse.model_validate(p)
        resp.is_active = active_map.get(p.id, False)
        response.append(resp)
        
    return response

@router.post("/{plugin_id}/activate")
def activate_plugin(plugin_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Activate a plugin for the current user."""
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
        
    user_plugin = db.query(UserPlugin).filter(
        UserPlugin.user_id == current_user.id,
        UserPlugin.plugin_id == plugin_id
    ).first()
    
    if not user_plugin:
        user_plugin = UserPlugin(
            user_id=current_user.id,
            plugin_id=plugin_id,
            is_active=True,
            activated_at=datetime.utcnow()
        )
        db.add(user_plugin)
    else:
        user_plugin.is_active = True
        user_plugin.activated_at = datetime.utcnow()
        
    # Log Audit
    audit = AuditLog(
        user_id=current_user.id,
        action_type="PLUGIN_ACTIVATE",
        resource_id=plugin_id,
        details_json={"version": plugin.version}
    )
    db.add(audit)
    db.commit()
    
    return {"status": "activated", "plugin_id": plugin_id}

@router.post("/{plugin_id}/deactivate")
def deactivate_plugin(plugin_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Deactivate a plugin."""
    user_plugin = db.query(UserPlugin).filter(
        UserPlugin.user_id == current_user.id,
        UserPlugin.plugin_id == plugin_id
    ).first()
    
    if user_plugin:
        user_plugin.is_active = False
        
        audit = AuditLog(
            user_id=current_user.id,
            action_type="PLUGIN_DEACTIVATE",
            resource_id=plugin_id
        )
        db.add(audit)
        db.commit()
        
    return {"status": "deactivated", "plugin_id": plugin_id}

@router.put("/{plugin_id}/config")
def update_plugin_config(
    plugin_id: str, 
    config: PluginConfigUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Update user-specific plugin configuration."""
    user_plugin = db.query(UserPlugin).filter(
        UserPlugin.user_id == current_user.id,
        UserPlugin.plugin_id == plugin_id
    ).first()
    
    if not user_plugin:
        raise HTTPException(status_code=404, detail="Plugin not activated for user")
        
    user_plugin.config_overrides = config.config_overrides
    
    audit = AuditLog(
        user_id=current_user.id,
        action_type="PLUGIN_CONFIG_UPDATE",
        resource_id=plugin_id,
        details_json=config.config_overrides
    )
    db.add(audit)
    db.commit()
    
    return {"status": "updated", "config": config.config_overrides}

# --- Management Endpoints (Proxy to Strategy Core) ---

import httpx
import os

# Env var or config for strategy core URL
STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

@router.post("/upload")
async def upload_plugin(file: UploadFile, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Upload a plugin zip file.
    1. Proxies upload to Strategy Core.
    2. Syncs DB to ensure plugin record exists.
    """
    # 1. Proxy to Strategy Core
    async with httpx.AsyncClient() as client:
        # Re-read file to stream? 
        # UploadFile is a file-like object.
        # We need to send it as multipart.
        files = {'file': (file.filename, await file.read(), file.content_type)}
        try:
            resp = await client.post(f"{STRATEGY_CORE_URL}/internal/plugins/install", files=files)
            resp.raise_for_status()
            data = resp.json() # {"status": "installed", "id": "plugin-name"}
            plugin_id = data.get("id")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Strategy Core Upload Failed: {e}")

    # 2. Sync DB (Create entry if missing)
    # We don't have full metadata from strategy-core scan yet (unless we parse it there).
    # For now, create a placeholder using the ID. The user can update details or we can fetch metadata later.
    existing = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not existing:
        new_plugin = Plugin(
            id=plugin_id,
            name=plugin_id.replace("-", " ").title(),
            description="Uploaded via UI",
            version="0.0.1",
            author=current_user.email,
            category=PluginCategory.UTILITY,
            base_config_schema={}
        )
        db.add(new_plugin)
        db.commit()
    
    return {"status": "installed", "id": plugin_id}

@router.post("/sync")
async def sync_plugins(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Scans Strategy Core for plugins and creates missing DB entries.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{STRATEGY_CORE_URL}/internal/plugins")
            resp.raise_for_status()
            plugin_ids = resp.json() # List[str]
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Strategy Core Sync Failed: {e}")

    added = []
    for pid in plugin_ids:
        existing = db.query(Plugin).filter(Plugin.id == pid).first()
        if not existing:
            new_plugin = Plugin(
                id=pid,
                name=pid.replace("-", " ").title(),
                description="Discovered via Sync",
                version="0.0.1",
                author="System",
                category=PluginCategory.UTILITY,
                base_config_schema={}
            )
            db.add(new_plugin)
            added.append(pid)
    
    if added:
        db.commit()
        
    return {"status": "synced", "added": added}

@router.get("/hooks")
async def inspect_system_hooks(current_user: User = Depends(get_current_user)):
    """
    Returns current active hooks from Strategy Core.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{STRATEGY_CORE_URL}/internal/plugins/hooks")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Strategy Core Hook Inspection Failed: {e}")

class NotifyRequest(BaseModel):
    message: str
    category: Optional[str] = "info"

@router.post("/notify")
async def send_notification(
    request: NotifyRequest, 
    current_user: User = Depends(get_current_user)
):
    """
    Proxies a notification request to Strategy Core for the current user.
    """
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "message": request.message,
                "user_id": str(current_user.id),
                "category": request.category
            }
            resp = await client.post(f"{STRATEGY_CORE_URL}/internal/plugins/notify", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Strategy Core Notification Failed: {e}")

