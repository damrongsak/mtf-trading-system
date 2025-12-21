"""
RiskRule SQLAlchemy model.
Source of truth: specs/03_data_model.yaml -> RiskRule entity
"""

from sqlalchemy import Column, String, DateTime, Numeric, Boolean, Enum as SQLEnum, Text, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.database import Base


class RuleType(enum.Enum):
    """Category of risk rule"""
    RISK_CAP = "RISK_CAP"
    LOT_SIZE = "LOT_SIZE"
    VOLATILITY = "VOLATILITY"
    RR_RATIO = "RR_RATIO"


class RiskRule(Base):
    """
    Configurable risk guardrail thresholds (F2.2, F2.3, F2.4).

    Centralizes risk management configuration:
    - MAX_RISK_PER_TRADE: $10 cap (F2.2)
    - MIN_LOT_SIZE: 0.01 minimum (F2.3)
    - MAX_ATR_PIPS: 100 pips volatility limit (F2.4)
    - MIN_RR_RATIO: 1:2 risk-to-reward minimum
    """
    __tablename__ = "risk_rules"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    rule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Rule Identification
    rule_name = Column(String(100), nullable=False, unique=True,
                      comment="Name of the risk rule (e.g., 'MAX_RISK_PER_TRADE')")
    rule_type = Column(SQLEnum(RuleType), nullable=False,
                      comment="Category of risk rule")

    # Threshold Configuration
    threshold_value = Column(Numeric(10, 2), nullable=False,
                            comment="Threshold value (e.g., 10.00 for $10 risk cap)")
    threshold_unit = Column(String(20), nullable=False,
                           comment="Unit of measurement (USD, LOT, PIPS, RATIO)")

    # Status
    is_active = Column(Boolean, nullable=False, default=True,
                      comment="Whether this rule is currently enforced")

    # Documentation
    description = Column(Text, nullable=True,
                        comment="Human-readable description of the rule")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Rule creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                       onupdate=func.now(),
                       comment="Rule last update timestamp")

    __table_args__ = (
        {
            'comment': 'Configurable risk guardrail thresholds (F2.2, F2.3, F2.4)',
            'extend_existing': True
        }
    )

    def __repr__(self):
        return f"<RiskRule {self.rule_name} {self.threshold_value} {self.threshold_unit} active={self.is_active}>"
