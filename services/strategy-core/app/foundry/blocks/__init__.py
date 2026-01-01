from .trend import TrendEMACross, TrendAMA
from .structure import StructureSMCOrderBlock, StructureFibGolden
from .momentum import MomentumRSICross, MomentumVectorCandle

BLOCK_REGISTRY = {
    "TREND_EMA_CROSS": TrendEMACross,
    "TREND_AMA": TrendAMA,
    "STRUCT_SMC_OB": StructureSMCOrderBlock,
    "STRUCT_FIB_GOLDEN": StructureFibGolden,
    "MOM_RSI_CROSS": MomentumRSICross,
    "MOM_VECTOR_CANDLE": MomentumVectorCandle
}

def get_block_class(block_id: str):
    return BLOCK_REGISTRY.get(block_id)
