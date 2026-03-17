from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_fund import Fund, UserFund, UserRole
from app.models.user import User
from app.security import get_current_user
from app.dependencies.rbac import RequireRole
from pydantic import BaseModel, ConfigDict
from app.schemas.response import APIResponse
from app.utils.response import success_response
from typing import List, Optional, Any
import uuid # Standard lib uuid
from app.models.user_preferences import StrategyType # Import shared StrEnum
from app.schemas.generated import (
    Fund as GeneratedFund,
    FundCreate as GeneratedFundCreate,
    FundUpdate as GeneratedFundUpdate
)

router = APIRouter(
    prefix="/api/v1/funds",
    tags=["funds"]
)


class FundResponse(GeneratedFund):
    role: str | None = None  # User's role in this fund
    owner_name: str | None = None
    
    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=APIResponse[List[FundResponse]])
async def list_user_funds(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all funds the current user has access to
    """
    # Get all funds associated with the user through UserFund relationship
    user_funds = db.query(UserFund).filter(UserFund.user_id == current_user.id).all()
    
    funds_response = []
    for uf in user_funds:
        fund = db.query(Fund).filter(Fund.id == uf.fund_id).first()
        if fund:
            # Find the owner name for this fund
            from app.models.user_fund import UserRole as UserFundRole
            owner_uf = db.query(UserFund).filter(
                UserFund.fund_id == fund.id,
                UserFund.role == UserFundRole.OWNER
            ).first()
            
            owner_name = "Unknown"
            if owner_uf:
                owner = db.query(User).filter(User.id == owner_uf.user_id).first()
                if owner:
                    owner_name = owner.username

            funds_response.append(
                FundResponse(
                    id=fund.id,
                    name=fund.name,
                    description=fund.description,
                    owner_name=owner_name,

                    role=uf.role.value if uf.role else None,
                    strategy_type=fund.strategy_type,
                    asset_classes=fund.asset_classes,
                    max_risk_per_trade=fund.max_risk_per_trade,
                    default_lot_size=fund.default_lot_size,
                    max_drawdown_threshold=fund.max_drawdown_threshold,
                    max_portfolio_beta=fund.max_portfolio_beta,
                    gross_exposure_limit=fund.gross_exposure_limit,
                    net_exposure_limit=fund.net_exposure_limit,
                    position_limit_single=fund.position_limit_single,
                    position_limit_sector=fund.position_limit_sector
                )
            )
    
    return success_response(
        data=funds_response,
        message=f"Retrieved {len(funds_response)} funds"
    )


@router.get("/{fund_id}", response_model=APIResponse[FundResponse])
async def get_fund(
    fund_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER, UserRole.MANAGER, UserRole.TRADER, UserRole.VIEWER]))
):
    """
    Get details of a specific fund
    """
    # Access checked by RequireRole dependency
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fund not found"
        )

    # Find the owner name for this fund
    from app.models.user_fund import UserRole as UserFundRole
    owner_uf = db.query(UserFund).filter(
        UserFund.fund_id == fund.id,
        UserFund.role == UserFundRole.OWNER
    ).first()
    
    owner_name = "Unknown"
    if owner_uf:
        owner = db.query(User).filter(User.id == owner_uf.user_id).first()
        if owner:
            owner_name = owner.username
    
    return success_response(
        data=FundResponse(
            id=fund.id,
            name=fund.name,
            description=fund.description,
            owner_name=owner_name,

            role=user_fund.role.value if user_fund.role else None,
            strategy_type=fund.strategy_type,
            asset_classes=fund.asset_classes,
            max_risk_per_trade=fund.max_risk_per_trade,
            default_lot_size=fund.default_lot_size,
            max_drawdown_threshold=fund.max_drawdown_threshold,
            max_portfolio_beta=fund.max_portfolio_beta,
            gross_exposure_limit=fund.gross_exposure_limit,
            net_exposure_limit=fund.net_exposure_limit,
            position_limit_single=fund.position_limit_single,
            position_limit_sector=fund.position_limit_sector
        )
    )


# Local Fund schemas replaced by generated ones


@router.post("", response_model=APIResponse[FundResponse], status_code=status.HTTP_201_CREATED)
async def create_fund(
    fund_data: GeneratedFundCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new fund and assign the creator as OWNER
    """
    new_fund = Fund(
        name=fund_data.name,
        description=fund_data.description
    )
    # Apply optional risk settings if provided
    if fund_data.strategy_type: new_fund.strategy_type = fund_data.strategy_type
    if fund_data.asset_classes: new_fund.asset_classes = fund_data.asset_classes
    if fund_data.max_risk_per_trade is not None: new_fund.max_risk_per_trade = fund_data.max_risk_per_trade
    if fund_data.risk_percentage is not None: new_fund.risk_percentage = fund_data.risk_percentage
    if fund_data.default_lot_size is not None: new_fund.default_lot_size = fund_data.default_lot_size
    if fund_data.max_drawdown_threshold is not None: new_fund.max_drawdown_threshold = fund_data.max_drawdown_threshold
    if fund_data.max_portfolio_beta is not None: new_fund.max_portfolio_beta = fund_data.max_portfolio_beta
    if fund_data.gross_exposure_limit is not None: new_fund.gross_exposure_limit = fund_data.gross_exposure_limit
    if fund_data.net_exposure_limit is not None: new_fund.net_exposure_limit = fund_data.net_exposure_limit
    if fund_data.position_limit_single is not None: new_fund.position_limit_single = fund_data.position_limit_single
    if fund_data.position_limit_sector is not None: new_fund.position_limit_sector = fund_data.position_limit_sector
    db.add(new_fund)
    db.flush() # Generate ID
    
    # Assign creator as OWNER
    from app.models.user_fund import UserRole as UserFundRole
    user_fund = UserFund(
        user_id=current_user.id,
        fund_id=new_fund.id,
        role=UserFundRole.OWNER
    )
    db.add(user_fund)
    
    db.commit()
    db.refresh(new_fund)
    
    return success_response(
        data=FundResponse(
            id=new_fund.id,
            name=new_fund.name,
            description=new_fund.description,

            role="OWNER",
            strategy_type=new_fund.strategy_type,
            asset_classes=new_fund.asset_classes,
            max_risk_per_trade=new_fund.max_risk_per_trade,
            default_lot_size=new_fund.default_lot_size,
            max_drawdown_threshold=new_fund.max_drawdown_threshold,
            max_portfolio_beta=new_fund.max_portfolio_beta,
            gross_exposure_limit=new_fund.gross_exposure_limit,
            net_exposure_limit=new_fund.net_exposure_limit,
            position_limit_single=new_fund.position_limit_single,
            position_limit_sector=new_fund.position_limit_sector
        ),
        message="Fund created successfully"
    )


@router.put("/{fund_id}", response_model=APIResponse[FundResponse])
async def update_fund(
    fund_id: uuid.UUID,
    fund_update: GeneratedFundUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER, UserRole.MANAGER]))
):
    """
    Update fund details. Requires MANAGER or OWNER role.
    """
    from app.models.user_fund import UserRole as UserFundRole
    
    # Permission handled by RequireRole dependency
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
         raise HTTPException(status_code=404, detail="Fund not found")

    if fund_update.name is not None:
        fund.name = fund_update.name
    if fund_update.description is not None:
        fund.description = fund_update.description
    
    # Update Risk Settings
    if fund_update.strategy_type is not None:
        fund.strategy_type = fund_update.strategy_type
    if fund_update.asset_classes is not None:
        fund.asset_classes = fund_update.asset_classes
    if fund_update.max_risk_per_trade is not None:
        fund.max_risk_per_trade = fund_update.max_risk_per_trade
    if fund_update.default_lot_size is not None:
        fund.default_lot_size = fund_update.default_lot_size
    if fund_update.max_drawdown_threshold is not None:
        fund.max_drawdown_threshold = fund_update.max_drawdown_threshold
    if fund_update.max_portfolio_beta is not None:
        fund.max_portfolio_beta = fund_update.max_portfolio_beta
    if fund_update.gross_exposure_limit is not None:
        fund.gross_exposure_limit = fund_update.gross_exposure_limit
    if fund_update.net_exposure_limit is not None:
        fund.net_exposure_limit = fund_update.net_exposure_limit
    if fund_update.position_limit_single is not None:
        fund.position_limit_single = fund_update.position_limit_single
    if fund_update.position_limit_sector is not None:
        fund.position_limit_sector = fund_update.position_limit_sector
    if fund_update.risk_percentage is not None:
        fund.risk_percentage = fund_update.risk_percentage
        
    db.commit()
    db.refresh(fund)
    
    return success_response(
        data=FundResponse(
            id=fund.id,
            name=fund.name,
            description=fund.description,

            role=user_fund.role.value,
            strategy_type=fund.strategy_type,
            asset_classes=fund.asset_classes,
            max_risk_per_trade=fund.max_risk_per_trade,
            default_lot_size=fund.default_lot_size,
            max_drawdown_threshold=fund.max_drawdown_threshold,
            max_portfolio_beta=fund.max_portfolio_beta,
            gross_exposure_limit=fund.gross_exposure_limit,
            net_exposure_limit=fund.net_exposure_limit,
            position_limit_single=fund.position_limit_single,
            position_limit_sector=fund.position_limit_sector
        ),
        message="Fund updated successfully"
    )


@router.delete("/{fund_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fund(
    fund_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER]))
):
    """
    Delete a fund. Requires OWNER role.
    """
    from app.models.user_fund import UserRole as UserFundRole
    
    # Permission handled by RequireRole dependency (OWNER only)
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
         raise HTTPException(status_code=404, detail="Fund not found")
         
    db.delete(fund)
    db.commit()
    
    return None
