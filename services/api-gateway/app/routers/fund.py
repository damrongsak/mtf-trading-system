from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_fund import Fund, UserFund
from app.security import get_current_user
from pydantic import BaseModel
from app.schemas.response import APIResponse
from app.utils.response import success_response
import uuid

router = APIRouter(
    prefix="/api/v1/funds",
    tags=["funds"]
)


class FundResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    role: str | None  # User's role in this fund
    
    class Config:
        from_attributes = True


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
            funds_response.append(
                FundResponse(
                    id=fund.id,
                    name=fund.name,
                    description=fund.description,
                    role=uf.role.value if uf.role else None
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
    db: Session = Depends(get_db)
):
    """
    Get details of a specific fund
    """
    # Check if user has access to this fund
    user_fund = db.query(UserFund).filter(
        UserFund.user_id == current_user.id,
        UserFund.fund_id == fund_id
    ).first()
    
    if not user_fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fund not found or access denied"
        )
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fund not found"
        )
    
    return success_response(
        data=FundResponse(
            id=fund.id,
            name=fund.name,
            description=fund.description,
            role=user_fund.role.value if user_fund.role else None
        )
    )


class FundCreate(BaseModel):
    name: str
    description: str | None = None

class FundUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@router.post("", response_model=APIResponse[FundResponse], status_code=status.HTTP_201_CREATED)
async def create_fund(
    fund_data: FundCreate,
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
    db.add(new_fund)
    db.flush() # Generate ID
    
    # Assign creator as OWNER
    from app.models.user_fund import UserFundRole
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
            role="OWNER"
        ),
        message="Fund created successfully"
    )


@router.put("/{fund_id}", response_model=APIResponse[FundResponse])
async def update_fund(
    fund_id: uuid.UUID,
    fund_update: FundUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update fund details. Requires MANAGER or OWNER role.
    """
    from app.models.user_fund import UserFundRole
    
    # Check permissions
    user_fund = db.query(UserFund).filter(
        UserFund.user_id == current_user.id,
        UserFund.fund_id == fund_id
    ).first()
    
    if not user_fund or user_fund.role not in [UserFundRole.OWNER, UserFundRole.MANAGER]:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this fund"
        )
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
         raise HTTPException(status_code=404, detail="Fund not found")

    if fund_update.name is not None:
        fund.name = fund_update.name
    if fund_update.description is not None:
        fund.description = fund_update.description
        
    db.commit()
    db.refresh(fund)
    
    return success_response(
        data=FundResponse(
            id=fund.id,
            name=fund.name,
            description=fund.description,
            role=user_fund.role.value
        ),
        message="Fund updated successfully"
    )


@router.delete("/{fund_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fund(
    fund_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a fund. Requires OWNER role.
    """
    from app.models.user_fund import UserFundRole
    
    # Check permissions (Strictly OWNER)
    user_fund = db.query(UserFund).filter(
        UserFund.user_id == current_user.id,
        UserFund.fund_id == fund_id
    ).first()
    
    if not user_fund or user_fund.role != UserFundRole.OWNER:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the fund owner can delete this fund"
        )
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
         raise HTTPException(status_code=404, detail="Fund not found")
         
    db.delete(fund)
    db.commit()
    
    return None
