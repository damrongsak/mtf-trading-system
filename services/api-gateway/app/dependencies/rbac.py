from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from app.database import get_db
from app.models.user_fund import UserFund, UserRole
from app.models.user import User
from app.security import get_current_user

logger = logging.getLogger(__name__)

class RequireRole:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        request: Request,
        fund_id: Optional[uuid.UUID] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user) # Added type hint for current_user
    ):
        """
        Dependency that checks if the current user has the required roles for a fund.
        It attempts to resolve fund_id from:
        1. Explicitly passed fund_id (query param or other dependency)
        2. Path parameters (fund_id or id if context allows)
        3. Request body (fund_id) - fallback
        """
        # 1. Resolve fund_id from path params if not provided
        if not fund_id:
            path_params = request.path_params
            if "fund_id" in path_params:
                try:
                    fund_id = uuid.UUID(path_params["fund_id"])
                except:
                    pass
            elif "id" in path_params and request.url.path.startswith("/api/v1/funds"):
                # Special case for /api/v1/funds/{id}
                try:
                    fund_id = uuid.UUID(path_params["id"])
                except:
                    pass
            elif "account_id" in path_params:
                # Resolve fund_id from account_id
                try:
                    acc_id = uuid.UUID(path_params["account_id"])
                    from app.models.broker_account import BrokerAccount
                    acc = db.query(BrokerAccount).filter(BrokerAccount.id == acc_id).first()
                    if acc:
                        fund_id = acc.fund_id
                except Exception as e:
                    logger.warning(f"Failed to resolve fund_id from account_id in RBAC: {e}")
                    pass

        # 2. Body Fallback (Only if not already resolved)
        if not fund_id:
            try:
                # Note: Reading body twice might require middleware or reset seek
                # But for simple JSON it usually works in FastAPI if not already consumed
                body = await request.json()
                if isinstance(body, dict):
                    fid = body.get("fund_id")
                    if fid:
                        fund_id = uuid.UUID(str(fid))
            except:
                pass

        if not fund_id:
            # Note: For list endpoints, this might not be needed if they handle filtering internally
            # If fund_id is still not resolved, it means the endpoint might not be fund-specific
            # or the fund_id could not be determined from the request context.
            # For manual calls, fund_id should be provided.
            # For FastAPI dependencies, if fund_id is truly optional for the route,
            # this dependency might not be suitable or needs further logic.
            # For now, we'll raise an error if fund_id is required but not found.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fund ID could not be determined from the request."
            )

        # 3. Check UserRole for this Fund
        user_fund = db.query(UserFund).filter(
            UserFund.user_id == current_user.id,
            UserFund.fund_id == fund_id
        ).first()

        if not user_fund:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: You do not have access to this fund"
            )

        if user_fund.role not in self.allowed_roles:
            role_names = [r.value for r in self.allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Required roles: {role_names}. Your role: {user_fund.role.value}"
            )

        return user_fund

async def get_fund_id_from_account(account_id: uuid.UUID, db: Session = Depends(get_db)) -> uuid.UUID:
    """Helper dependency to extract fund_id from a broker account."""
    from app.models.broker_account import BrokerAccount
    acc = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Broker account not found")
    return acc.fund_id
