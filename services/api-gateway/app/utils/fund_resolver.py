from typing import Optional
from sqlalchemy.orm import Session
from app.models.user_fund import UserFund, Fund
from app.models.broker_account import BrokerAccount
import logging

logger = logging.getLogger(__name__)

def get_best_fund_for_user(db: Session, user_id: str) -> Optional[str]:
    """
    Intelligently resolves the most relevant fund_id for a user.
    Prioritizes:
    1. Funds where the user is an OWNER.
    2. Funds that have an active BrokerAccount linked.
    3. The first available fund.
    """
    # 1. Look for Funds where user is OWNER and has an active BrokerAccount
    best_fund = db.query(UserFund.fund_id).join(
        BrokerAccount, BrokerAccount.fund_id == UserFund.fund_id
    ).filter(
        UserFund.user_id == user_id,
        UserFund.role == "OWNER",
        BrokerAccount.is_active == True
    ).first()
    
    if best_fund:
        logger.info(f"Resolved primary fund {best_fund[0]} for user {user_id} (Owner + Active Account)")
        return str(best_fund[0])
        
    # 2. Look for any Fund where user is OWNER
    owner_fund = db.query(UserFund.fund_id).filter(
        UserFund.user_id == user_id,
        UserFund.role == "OWNER"
    ).first()
    
    if owner_fund:
        logger.info(f"Resolved owner fund {owner_fund[0]} for user {user_id} (Fallback: Any Owner)")
        return str(owner_fund[0])
        
    # 3. Fallback to any linked fund
    any_fund = db.query(UserFund.fund_id).filter(
        UserFund.user_id == user_id
    ).first()
    
    if any_fund:
        logger.info(f"Resolved fallback fund {any_fund[0]} for user {user_id} (Final Fallback)")
        return str(any_fund[0])

    logger.warning(f"No fund found for user {user_id} in resolution chain.")
    return None
