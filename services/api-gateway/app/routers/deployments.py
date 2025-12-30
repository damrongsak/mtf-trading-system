
import httpx
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db, SessionLocal
from app.security import get_current_user
from app.models.deployment import Deployment
from app.models.user_fund import User
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
import os
from datetime import datetime

router = APIRouter()

# Service URLs
STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

from app.schemas.response import PaginatedResponse
from app.utils.response import paginated_response

@router.get("/", response_model=PaginatedResponse[DeploymentResponse])
def list_deployments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """
    List active deployments.
    """
    # 1. Get Total Count
    total = db.query(Deployment).filter(Deployment.user_id == current_user.id).count()
    
    # 2. Get Data
    deployments = db.query(Deployment).options(joinedload(Deployment.strategy)).filter(
        Deployment.user_id == current_user.id
    ).order_by(Deployment.started_at.desc()).offset(skip).limit(limit).all()
    
    # Calculate PnL for each deployment
    results = []
    
    for dep in deployments:
        # PnL Sum
        # This query relies on metadata_json being searchable. 
        # For Postgres: 
        from sqlalchemy import func
        from app.models.trade import Trade
        
        # We need to filter trades that have metadata_json ->> 'deployment_id' == dep.id
        total_pnl = db.query(func.sum(Trade.pnl_usd)).filter(
            Trade.metadata_json['deployment_id'].astext == str(dep.id)
        ).scalar()
        
        dep_resp = DeploymentResponse.model_validate(dep)
        dep_resp.total_pnl_usd = float(total_pnl) if total_pnl is not None else 0.0
        
        # Populate Strategy Name
        if dep.strategy:
             dep_resp.strategy_name = dep.strategy.name
        
        results.append(dep_resp)
        
    # 3. Return Paginated Response
    # page = floor(skip / limit) + 1
    page = (skip // limit) + 1
    
    return paginated_response(
        data=results,
        page=page,
        per_page=limit,
        total=total
    )

@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment_in: DeploymentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deploy a new strategy instance.
    """
    # 1. Check limit
    active_count = db.query(Deployment).filter(
        Deployment.user_id == current_user.id, 
        Deployment.status == "ACTIVE"
    ).count()
    
    if active_count >= 5:
        raise HTTPException(status_code=400, detail="Deployment limit reached (Max 5). Stop an existing bot first.")

    # 2. Create DB Record
    deployment = Deployment(
        user_id=current_user.id,
        strategy_id=deployment_in.strategy_id,
        stock_symbol=deployment_in.stock_symbol,
        timeframe=deployment_in.timeframe,
        config_snapshot=deployment_in.config_snapshot,
        is_live=deployment_in.is_live,
        status="STARTING"
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    # 3. Trigger Strategy Core (Async)
    background_tasks.add_task(start_bot_instance, str(deployment.id), deployment_in.dict())
    
    return deployment

@router.post("/{id}/stop", response_model=DeploymentResponse)
async def stop_deployment(
    id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stop a running deployment.
    """
    deployment = db.query(Deployment).filter(Deployment.id == id, Deployment.user_id == current_user.id).first()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
        
    deployment.status = "STOPPING"
    db.commit()
    
    # Trigger Backend Stop
    background_tasks.add_task(stop_bot_instance, str(deployment.id))
    
    
    return deployment

@router.post("/{id}/restart", response_model=DeploymentResponse)
async def restart_deployment(
    id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Restart a stopped deployment.
    """
    deployment = db.query(Deployment).filter(Deployment.id == id, Deployment.user_id == current_user.id).first()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
        
    if deployment.status not in ["STOPPED", "ERROR", "STOPPING"]:
        raise HTTPException(status_code=400, detail="Only STOPPED, ERROR, or STOPPING deployments can be restarted")
        
    # Reset Status
    deployment.status = "STARTING"
    deployment.last_error = None
    db.commit()
    
    # Trigger Backend Start ( reusing start_bot_instance logic )
    # Note: start_bot_instance expects config dict, but we can access deployment.config_snapshot
    config = deployment.config_snapshot or {}
    background_tasks.add_task(start_bot_instance, str(deployment.id), config)
    
    return deployment


async def start_bot_instance(deployment_id: str, config: dict):
    """
    Call Strategy Core to spin up the bot and update status locally.
    """
    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            # We need to fetch the strategy code first? 
            # Ideally Strategy Core fetches it from DB or we pass it here. 
            # Passing ID is better.
            payload = {
                "deployment_id": deployment_id,
                # passing config just in case, but core can fetch from DB
            }
            resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/live/deploy", json=payload, timeout=10.0)
            
            deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
            if not deployment:
                print(f"Deployment {deployment_id} not found during start callback")
                return

            if resp.status_code == 200:
                deployment.status = "ACTIVE"
                # deployment.started_at is already set on creation? Or should reset?
                # Usually set on creation, but maybe update here if needed.
            else:
                print(f"Failed to start bot {deployment_id}: {resp.text}")
                deployment.status = "ERROR"
                deployment.last_error = f"Core Start Failed: {resp.text}"
            
            db.commit()
            
    except Exception as e:
        print(f"Error starting bot: {e}")
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if deployment:
            deployment.status = "ERROR"
            deployment.last_error = f"Start Exception: {str(e)}"
            db.commit()
    finally:
        db.close()

async def stop_bot_instance(deployment_id: str):
    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/live/stop/{deployment_id}", timeout=5.0)
            
            deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
            if not deployment:
                return

            if resp.status_code == 200:
                deployment.status = "STOPPED"
                deployment.stopped_at = datetime.utcnow()
            else:
                # Even if core fails (e.g. not found), we should probably mark it stopped or error.
                # If not found, it's stopped.
                if resp.status_code == 404:
                     deployment.status = "STOPPED"
                     deployment.stopped_at = datetime.utcnow()
                else:
                    deployment.status = "ERROR"
                    deployment.last_error = f"Stop Failed: {resp.text}"
            
            db.commit()

    except Exception as e:
        print(f"Error stopping bot: {e}")
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if deployment:
            deployment.status = "ERROR" 
            deployment.last_error = f"Stop Exception: {str(e)}"
            db.commit()
    finally:
        db.close()
