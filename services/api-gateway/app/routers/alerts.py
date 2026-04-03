from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import logging

from app.database import get_db
from app.models.alert import Alert, AlertCondition as AlertModelCondition
from app.schemas.generated import AlertCreate, AlertResponse, AlertCondition as AlertSchemaCondition
from app.security import get_current_user
from app.models.user import User

from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(tags=["alerts"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_in: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a persistent price alert.
    The scheduler will monitor this alert and trigger a Telegram notification when resolved.
    """
    try:
        # Convert schema enum to model enum
        alert = Alert(
            user_id=current_user.id,
            symbol=alert_in.symbol,
            condition=AlertModelCondition(alert_in.condition.value),
            threshold=alert_in.threshold,
            is_active=alert_in.is_active if alert_in.is_active is not None else True
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info(f"Created alert {alert.id} for user {current_user.id}: {alert.symbol} {alert.condition.value} {alert.threshold}")
        data = AlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            symbol=alert.symbol,
            condition=AlertSchemaCondition(alert.condition.value),
            threshold=alert.threshold,
            is_active=alert.is_active,
            is_triggered=alert.is_triggered,
            last_triggered_at=alert.last_triggered_at,
            created_at=alert.created_at,
            updated_at=alert.updated_at
        )
        return success_response(data=data.model_dump(mode='json'), message="Alert created successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}"
        )

@router.get("")
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all alerts for the current user"""
    alerts_mo = db.query(Alert).filter(Alert.user_id == current_user.id).order_by(Alert.created_at.desc()).all()
    data = [
        AlertResponse(
            id=a.id,
            user_id=a.user_id,
            symbol=a.symbol,
            condition=AlertSchemaCondition(a.condition.value),
            threshold=a.threshold,
            is_active=a.is_active,
            is_triggered=a.is_triggered,
            last_triggered_at=a.last_triggered_at,
            created_at=a.created_at,
            updated_at=a.updated_at
        ) for a in alerts_mo
    ]
    return success_response(data=[d.model_dump(mode='json') for d in data], message="Alerts retrieved successfully")

@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a price alert"""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    
    try:
        db.delete(alert)
        db.commit()
        logger.info(f"Deleted alert {alert_id} for user {current_user.id}")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert: {str(e)}"
        )
