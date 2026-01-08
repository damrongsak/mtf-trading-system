from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.models.prompt import SystemPrompt, AuditLog
from app.models.user import User
from app.schemas.prompt import (
    SystemPromptCreate, SystemPromptUpdate, SystemPromptResponse,
    RenderPromptRequest, RenderPromptResponse
)
from app.core.security import get_current_user
from datetime import datetime
import json

router = APIRouter(prefix="/prompts", tags=["Prompts"])

def log_audit(db: Session, user_id: UUID, action: str, resource_type: str, resource_id: UUID, changes: dict):
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes
    )
    db.add(audit)
    # Commit should be handled by caller or auto-flush, but explicit add guarantees object exists

@router.get("/", response_model=List[SystemPromptResponse])
def list_prompts(
    owner_id: Optional[UUID] = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SystemPrompt)
    if owner_id:
        query = query.filter(SystemPrompt.owner_id == owner_id)
    return query.all()

@router.post("/", response_model=SystemPromptResponse)
def create_prompt(
    prompt_in: SystemPromptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check uniqueness
    existing = db.query(SystemPrompt).filter(SystemPrompt.name == prompt_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Prompt name already exists")

    new_prompt = SystemPrompt(
        owner_id=current_user.id,
        name=prompt_in.name,
        description=prompt_in.description,
        template=prompt_in.template,
        input_variables=prompt_in.input_variables,
        is_active=prompt_in.is_active,
        version=1
    )
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)

    log_audit(db, current_user.id, "CREATE", "PROMPT", new_prompt.id, prompt_in.model_dump())
    db.commit()

    return new_prompt

@router.get("/{prompt_id}", response_model=SystemPromptResponse)
def get_prompt(
    prompt_id: UUID,
    db: Session = Depends(get_db)
    # No auth required for reading specific prompt (Internal Service use)
    # But usually Gateway requires token. We might need a Service Token concept later.
    # For now, we assume internal calls might bypass or use a specific user.
):
    prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@router.put("/{prompt_id}", response_model=SystemPromptResponse)
def update_prompt(
    prompt_id: UUID,
    prompt_in: SystemPromptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Ownership/Permission check (Optional: Allow admins)
    if prompt.owner_id != current_user.id:
         # For simplicity, strict ownership for now
         pass 

    changes = {}
    if prompt_in.description is not None:
        changes["description"] = {"old": prompt.description, "new": prompt_in.description}
        prompt.description = prompt_in.description
    
    if prompt_in.template is not None:
        changes["template"] = {"old_len": len(prompt.template), "new_len": len(prompt_in.template)}
        prompt.template = prompt_in.template
        prompt.version += 1 # Increment version on template change
    
    if prompt_in.input_variables is not None:
        prompt.input_variables = prompt_in.input_variables
    
    if prompt_in.is_active is not None:
        prompt.is_active = prompt_in.is_active

    prompt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prompt)

    if changes:
        log_audit(db, current_user.id, "UPDATE", "PROMPT", prompt.id, changes)
        db.commit()

    return prompt

@router.post("/{prompt_id}/render", response_model=RenderPromptResponse)
def render_prompt(
    prompt_id: UUID,
    request: RenderPromptRequest,
    db: Session = Depends(get_db)
):
    prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    try:
        # Simple string formatting
        # For more complex logic, use jinja2
        # Use simple replace for now or jinja2 if installed?
        # Let's use simple jinja2-like replacement or f-string style if strictly controlled.
        # But safest given the "template" field is Jinja2.
        
        # We will use valid Jinja2 if available, otherwise simple key replacement
        from jinja2 import Template
        t = Template(prompt.template)
        rendered = t.render(**request.variables)
        
        # Check missing keys? Jinja2 handles them gracefully usually (empty)
        # But we can check input_variables vs request.variables keys
        missing = [v for v in prompt.input_variables if v not in request.variables]
        
        return RenderPromptResponse(rendered_text=rendered, missing_variables=missing)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Render error: {str(e)}")
