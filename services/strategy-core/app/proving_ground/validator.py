from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import vectorbt as vbt
from app.analysis.monte_carlo import run_monte_carlo

class WalkForwardValidator:
    def __init__(self, config: Dict[str, Any], data: pd.DataFrame):
        self.config = config
        self.data = data
        self.train_window = self.config.get('train_window_days', 180)
        self.test_window = self.config.get('test_window_days', 30)
        self.step_size = self.config.get('step_days', 30)
        
        self.optimization_params = self.config.get('optimization', {})
        self.param_grid = self.optimization_params.get('param_grid', {})

    def run(self) -> Dict[str, Any]:
        """
        Execute Walk-Forward Analysis with Monte Carlo validation.
        """
        start_date = self.data.index[0]
        end_date = self.data.index[-1]
        
        current_date = start_date + timedelta(days=self.train_window)
        logger.info(f"Starting WFA: {start_date} to {end_date}")
        
        chunk_results = []
        
        while current_date + timedelta(days=self.test_window) <= end_date:
            train_start = current_date - timedelta(days=self.train_window)
            train_end = current_date
            test_end = current_date + timedelta(days=self.test_window)
            
            # Slice Data
            train_data = self.data.loc[train_start:train_end]
            test_data = self.data.loc[train_end:test_end]
            
            if train_data.empty or test_data.empty:
                break
                
            # 1. OPTIMIZE (In-Sample)
            best_params = self._optimize(train_data)
            
            # 2. VALIDATE (Out-Of-Sample)
            oos_metrics, portfolio = self._backtest(test_data, best_params)
            
            # 3. Monte Carlo on OOS Trades
            # Extract trades for MC
            oos_trades = []
            try:
                readable_trades = portfolio.trades.records_readable
                for _, row in readable_trades.iterrows():
                    oos_trades.append({'pnl_percent': float(row['Return'] * 100)})
            except:
                pass
                
            mc_results = run_monte_carlo(oos_trades, n_sims=500) if oos_trades else {}
            
            chunk_results.append({
                'period_start': train_end.isoformat(),
                'period_end': test_end.isoformat(),
                'best_params': best_params,
                'oos_metrics': oos_metrics,
                'mc_robustness': mc_results.get('ruin_probability', 1.0)
            })

            current_date += timedelta(days=self.step_size)

        if not chunk_results:
             return {'robustness_score': 0, 'details': []}

        positive_oos = sum(1 for c in chunk_results if c['oos_metrics']['total_return'] > 0)
        robust_oos = sum(1 for c in chunk_results if c['mc_robustness'] < 0.1) # Less than 10% ruin prob
        
        robustness_score = (positive_oos * 0.6 + robust_oos * 0.4) / len(chunk_results) * 100
        
        return {
            'robustness_score': int(robustness_score),
            'period_count': len(chunk_results),
            'avg_oos_return': float(np.mean([c['oos_metrics']['total_return'] for c in chunk_results])),
            'details': chunk_results
        }
        
    def _optimize(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run Optimization on Train Data to find best params.
        """
        if not self.param_grid:
            return {} # No optimization
            
        # We need a callable that maps 'flat params' back to 'foundry config struct'
        def strategy_wrapper(df: pd.DataFrame, params: Dict[str, Any]):
             # 1. Inject flat params into the config structure
             # Assuming param names are unique IDs or names in config
             # Eg. "Trend_Period": 20
             
             # Clone local config
             run_config = self._apply_params(self.config, params)
             
             pipeline = StrategyAssembler.assemble(run_config)
             
             # Context requires dict
             context = {'candles': {'4h': df, '1h': df, '15m': df}} # Simplification: Assuming single TF provided as data matches strategy expectations
             
             return pipeline.run_vector(context)
             
        results = run_grid_search(
            data=data,
            param_grid=self.param_grid,
            strategy_callable=strategy_wrapper
        )
        
        if not results:
            return {}
            
        return results[0]['params'] # Best Result

    def _backtest(self, data: pd.DataFrame, params: Dict[str, Any]):
        """
        Run single backtest on Data.
        """
        run_config = self._apply_params(self.config, params)
        pipeline = StrategyAssembler.assemble(run_config)
        context = {'candles': {'4h': data, '1h': data, '15m': data}}
        
        entries, exits = pipeline.run_vector(context)
        
        import vectorbt as vbt
        portfolio = vbt.Portfolio.from_signals(
            data['close'],
            entries,
            exits,
            freq='1H' # Approx
        )
        
        # Extract Metrics
        metrics = {
            'total_return': float(portfolio.total_return()),
            'sharpe_ratio': float(portfolio.sharpe_ratio()) if not np.isnan(portfolio.sharpe_ratio()) else 0.0,
            'max_drawdown': float(portfolio.max_drawdown())
        }
        
        return metrics, portfolio.value()

    def _apply_params(self, config_template: Dict, flat_params: Dict) -> Dict:
        """
        Recursively update config parameters with flattened optimization values.
        Convention: parameter key in grid matches nested structure? 
        OR: Simply param keys in grid are "BlockID_ParamName"
        """
        # For prototype, we assume the config 'logic_blocks' have 'id' and we map simple keys?
        # Actually simpler: The param grid keys MUST match the block parameter names if unique,
        # or be prefixed like "TrendBlock_period".
        
        # Deep Copy
        import copy
        new_conf = copy.deepcopy(config_template)
        
        # Naive implementation: Iterate blocks, check if their params are in flat_params
        for block in new_conf.get('logic_blocks', []):
             # block has: id, name, parameters
             b_params = block.get('parameters', {})
             for k in b_params.keys():
                  # Check if override exists in flat_params
                  if k in flat_params:
                      b_params[k] = flat_params[k]
                  # Also support Name_Key syntax
                  name_key = f"{block.get('name')}_{k}"
                  if name_key in flat_params:
                      b_params[k] = flat_params[name_key]
                      
        return new_conf
