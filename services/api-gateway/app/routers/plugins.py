from fastapi import APIRouter, Depends, HTTPException, status
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
