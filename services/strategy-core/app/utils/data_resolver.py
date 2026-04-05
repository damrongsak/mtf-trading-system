import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.user_fund import UserFund, Fund
from app.models.broker_account import BrokerAccount
from app.models.data_source import DataSource
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Institutional Macro Constants
MACRO_SYMBOLS = ["VIX", "DXY", "US10Y", "US02Y", "SPX500", "NAS100"]
DEFAULT_MACRO_PROVIDER = "YAHOO_FINANCE"

def resolve_source_for_fund(db: Session, user_id: str, fund_id: Optional[str], symbol: str) -> str:
    """
    Institutional Data Resolver.
    Ensures data isolation and aligns data source with the user's fund.
    
    Returns: provider_name (e.g., 'CTRADER', 'OANDA', 'YAHOO_FINANCE')
    """
    # 1. Macro Rule: Universal source for global drivers
    if symbol.upper() in MACRO_SYMBOLS:
        return DEFAULT_MACRO_PROVIDER

    # 2. Validation: If not macro, fund_id is mandatory for institutional isolation
    if not fund_id:
        # For non-fund specific requests, we might allow a default or reject
        # In a strict institutional environment, we reject.
        logger.warning(f"Request for {symbol} without fund_id. Access Denied.")
        raise HTTPException(
            status_code=400, 
            detail="fund_id is required for non-macro symbols to ensure data isolation."
        )

    # 3. RBAC Check: Ensure user has access to the fund
    user_fund = db.query(UserFund).filter(
        UserFund.user_id == user_id,
        UserFund.fund_id == fund_id
    ).first()

    if not user_fund:
        logger.error(f"User {user_id} attempted to access Fund {fund_id} - Unauthorized.")
        raise HTTPException(
            status_code=403, 
            detail="User does not have access to the specified fund."
        )

    # 4. Resolve Data Source from BrokerAccount
    # Fund -> BrokerAccount -> DataSource
    account = db.query(BrokerAccount).filter(
        BrokerAccount.fund_id == fund_id,
        BrokerAccount.is_active == True
    ).first()

    if not account or not account.data_source_id:
        logger.warning(f"Fund {fund_id} has no active broker account or data source linked.")
        # Fallback to a default or raise error
        # In SDD, we should have a 'CTRADER' default for Demo1
        return "CTRADER" 

    data_source = db.query(DataSource).filter(
        DataSource.id == account.data_source_id
    ).first()

    if not data_source:
        return "CTRADER" # Absolute fallback

    return data_source.name
