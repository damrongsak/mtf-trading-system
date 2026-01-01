from typing import List, Dict, Any
from app.foundry.base import LogicBlock, SignalState
from app.foundry.blocks import get_block_class

class StrategyPipeline:
    def __init__(self, blocks: List[LogicBlock], global_params: Dict[str, Any] = None):
        self.blocks = blocks
        self.global_params = global_params or {}

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all blocks in the pipeline and aggregate results.
        Simple aggregation: All blocks must NOT be NEUTRAL/INVALID to consider a trade,
        and if multiple signals exist, they must align or follow specific rules.
        
        For now, returns raw results of all blocks.
        """
        results = {}
        alignment_score = 0
        total_blocks = len(self.blocks)
        
        signals = []
        
        for block in self.blocks:
            res = block.run(context)
            results[block.name] = res
            
            if res['state'] == SignalState.BULLISH:
                signals.append(1)
            elif res['state'] == SignalState.BEARISH:
                signals.append(-1)
            else:
                signals.append(0)

        # Simple Consensus Logic (MVP)
        # If any block is BEARISH, we can't be BULLISH? 
        # Or just sum votes?
        # Let's do a simple sum for 'Direction'
        net_score = sum(signals)
        
        final_state = SignalState.NEUTRAL
        if net_score > 0 and -1 not in signals: # Unanimous or Valid with no blockers
             final_state = SignalState.BULLISH
        elif net_score < 0 and 1 not in signals:
             final_state = SignalState.BEARISH
             
        return {
            'pipeline_state': final_state,
            'net_score': net_score,
            'block_results': results
        }

class StrategyAssembler:
    @staticmethod
    def assemble(config: Dict[str, Any]) -> StrategyPipeline:
        """
        Create a StrategyPipeline from a configuration dictionary.
        
        :param config: Dictionary containing:
            - 'logic_blocks': List of dicts {'id': 'TREND_EMA', 'parameters': {...}}
            - 'parameters': Global parameters
        """
        logic_blocks_config = config.get('logic_blocks', [])
        global_params = config.get('parameters', {})
        
        blocks = []
        for i, block_conf in enumerate(logic_blocks_config):
            block_id = block_conf.get('id')
            params = block_conf.get('parameters', {})
            
            # Merit of mixing global params? 
            # block_params = {**global_params, **params}
            
            block_cls = get_block_class(block_id)
            if not block_cls:
                raise ValueError(f"Unknown Logic Block ID: {block_id}")
            
            # Instantiate
            # Name defaults to ID_Index if not provided
            instance_name = block_conf.get('name', f"{block_id}_{i}")
            block_instance = block_cls(name=instance_name, parameters=params)
            blocks.append(block_instance)
            
        return StrategyPipeline(blocks, global_params)
