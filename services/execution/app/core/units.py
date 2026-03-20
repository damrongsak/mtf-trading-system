import logging
from typing import Optional

logger = logging.getLogger(__name__)

class UnitConverter:
    """
    Centralized utility for Unit and Lot conversions (Risk Citadel Standard).
    Internal Standard: 1.0 Standard Lot = 100,000 Internal Units.
    
    Formula:
        broker_volume = internal_units * (broker_lot_size_volume / 100,000)
        internal_units = broker_volume * (100,000 / broker_lot_size_volume)
    """
    
    INTERNAL_LOT_UNITS = 100000.0
    CTRADER_VOLUME_STEP_CENTS = 100.0 # cTrader volume is usually in cents (0.01 oz = 100)

    @classmethod
    def internal_to_ctrader_volume(cls, units: float, broker_lot_size_cents: float, step_cents: float = 1.0) -> int:
        """
        Converts internal units to cTrader Protobuf volume (cents).
        """
        if broker_lot_size_cents <= 0:
            logger.error(f"Invalid broker_lot_size_cents: {broker_lot_size_cents}. Defaulting to FX 10M.")
            broker_lot_size_cents = 10000000.0
            
        raw_volume = abs(units) * (broker_lot_size_cents / cls.INTERNAL_LOT_UNITS)
        
        # Round down to nearest multiple of step_cents
        volume_cents = int((raw_volume // step_cents) * step_cents)
        
        # Ensure at least one step
        if volume_cents < step_cents:
            volume_cents = int(step_cents)
            
        return volume_cents

    @classmethod
    def ctrader_volume_to_standard_units(cls, volume_cents: float, broker_lot_size_cents: float) -> float:
        """
        Converts cTrader volume cents back to standard broker units (oz, base units).
        Rule: units = volume_cents / 100.0 (Standard for cTrader across Symbols).
        """
        return abs(volume_cents) / 100.0

    @classmethod
    def calculate_risk_usd(cls, price_diff: float, volume_cents: float) -> float:
        """
        Calculates Risk in USD based on price differential and cTrader volume cents.
        Universal Pro Rule: Risk = abs(price_diff) * (volume_cents / 100.0)
        """
        standard_units = cls.ctrader_volume_to_standard_units(volume_cents, 0) # lot_size not needed here
        return round(abs(price_diff) * standard_units, 2)

    @classmethod
    def internal_to_standard_lots(cls, units: float) -> float:
        """Converts internal units to standard lots (1.0 = 100k units)."""
        return abs(units) / cls.INTERNAL_LOT_UNITS

    @classmethod
    def calculate_size_from_risk(cls, risk_usd: float, price_diff: float, broker_lot_size_volume: float) -> float:
        """
        Calculates internal units required to achieve target risk USD.
        Universal Pro Formula:
            standard_units = risk_usd / abs(price_diff)
            internal_units = standard_units * (100,000 / broker_standard_units_per_lot)
        """
        if abs(price_diff) == 0 or broker_lot_size_volume <= 0:
            return 0.0
        
        standard_units = risk_usd / abs(price_diff)
        # Using cTrader standard: 1.0 lot = volume_cents / 100.0
        volume_cents = standard_units * 100.0
        
        # Convert volume_cents to internal_units based on relative lot size
        internal_units = volume_cents * (cls.INTERNAL_LOT_UNITS / broker_lot_size_volume)
        return internal_units

    @classmethod
    def ctrader_volume_to_internal_units(cls, volume_cents: float, broker_lot_size_volume: float) -> float:
        """
        Converts cTrader volume (cents) to internal units.
        """
        if broker_lot_size_volume <= 0:
            return 0.0
        return float(abs(volume_cents)) * (cls.INTERNAL_LOT_UNITS / broker_lot_size_volume)
