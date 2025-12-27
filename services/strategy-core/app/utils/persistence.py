import logging
import json
from sqlalchemy import text
from app.database import engine

logger = logging.getLogger(__name__)

def save_strategy_result(strategy_id: str, result_type: str, data: dict):
    """
    Save analysis result to the strategy record.
    
    Args:
        strategy_id: UUID string of the strategy
        result_type: One of 'backtest', 'optimization', 'simulation'
        data: Use Pydantic .dict() or compatible dictionary
    """
    if not strategy_id:
        return

    valid_types = ['backtest', 'optimization', 'simulation']
    if result_type not in valid_types:
        logger.error(f"Invalid result_type: {result_type}")
        return

    column_map = {
        'backtest': 'last_results',
        'optimization': 'last_optimization_result',
        'simulation': 'last_simulation_result'
    }
    
    col_name = column_map[result_type]
    
    try:
        # Convert Pydantic models to dict if needed (though callers usually pass dict or json-serializable)
        # SQLAlchemy handles JSON serialization for JSONB columns, but let's ensure it's a dict.
        if hasattr(data, 'dict'):
             payload = data.dict()
        else:
             payload = data

        query = text(f"""
            UPDATE saved_strategies 
            SET {col_name} = :payload, updated_at = now()
            WHERE id = :id
        """)
        
        with engine.begin() as conn:
            conn.execute(query, {"payload": json.dumps(payload, default=str), "id": strategy_id})
            
        logger.info(f"Saved {result_type} result for strategy {strategy_id}")
        
    except Exception as e:
        logger.error(f"Failed to save {result_type} result for strategy {strategy_id}: {e}")
