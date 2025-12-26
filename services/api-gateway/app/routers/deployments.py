
import httpx
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.api import deps
from app.models.deployment import Deployment
from app.models.user import User
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.core.config import settings

router = APIRouter()

# Service URLs
STRATEGY_CORE_URL = settings.STRATEGY_CORE_URL

@router.get("/", response_model=List[DeploymentResponse])
def list_deployments(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
):
    """
    List active deployments.
    """
    deployments = db.query(Deployment).filter(Deployment.user_id == current_user.id).offset(skip).limit(limit).all()
    return deployments

@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment_in: DeploymentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
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
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
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


async def start_bot_instance(deployment_id: str, config: dict):
    """
    Call Strategy Core to spin up the bot.
    """
    async with httpx.AsyncClient() as client:
        try:
            # We need to fetch the strategy code first? 
            # Ideally Strategy Core fetches it from DB or we pass it here. 
            # Passing ID is better.
            payload = {
                "deployment_id": deployment_id,
                # passing config just in case, but core can fetch from DB
            }
            resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/live/deploy", json=payload, timeout=10.0)
            if resp.status_code != 200:
                print(f"Failed to start bot {deployment_id}: {resp.text}")
                # Update DB status to ERROR? (Needs new session)
        except Exception as e:
            print(f"Error starting bot: {e}")

async def stop_bot_instance(deployment_id: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{STRATEGY_CORE_URL}/api/v1/live/stop/{deployment_id}", timeout=5.0)
        except Exception as e:
            print(f"Error stopping bot: {e}")
