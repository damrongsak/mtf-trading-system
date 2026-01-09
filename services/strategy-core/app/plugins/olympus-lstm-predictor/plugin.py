import logging
import random
from app.plugins.plugin_engine import BasePlugin, HookManager

logger = logging.getLogger(__name__)

class LSTMPredictorPlugin(BasePlugin):
    """
    Example Alpha Plugin: LSTM Price Predictor.
    """
    def __init__(self, user_id, context, config=None):
        config = config or {}
        super().__init__(user_id, context, config)
        self.metadata.update({
            "name": "Olympus LSTM Predictor",
            "version": "1.0.0",
            "description": "Predicts next candle close using LSTM model (Mock)",
            "author": "Olympus AI"
        })
        self.model_path = config.get("model_path", "default_lstm.h5")
        
    def activate(self):
        logger.info(f"🚀 LSTM Plugin Activated for User {self.user_id}")
        # Load model here...
        
    def deactivate(self):
        logger.info(f"🛑 LSTM Plugin Deactivated for User {self.user_id}")
        
    def register_hooks(self, hook_manager: HookManager):
        hook_manager.add_action("on_market_data", self.predict_price)
        hook_manager.add_filter("filter_signal", self.enrich_signal)
        
    def predict_price(self, data):
        """
        Action: Called when new market data arrives.
        """
        symbol = data.get("instrument") or data.get("symbol")
        price = (float(data.get("bid", 0)) + float(data.get("ask", 0))) / 2
        
        # Mock Prediction
        prediction = price * (1 + (random.uniform(-0.001, 0.001)))
        
        logger.info(f"🔮 [LSTM] {symbol} Price: {price:.5f} -> Pred: {prediction:.5f}")
        
    def enrich_signal(self, signal, state=None):
        """
        Filter: Modify the trading signal based on Plugin Mode.
        """
        mode = self.config.get("mode", "PRUDENT").upper()
        
        if not self.config.get("enrich_enabled", True):
            return signal

        original_confidence = signal.get("confidence", 0.5)
        
        if mode == "RECKLESS":
            # RECKLESS: Pure ML confidence, ignored market regime
            new_confidence = min(original_confidence + 0.2, 1.0)
            signal['reason'] = signal.get("reason", "") + " [LSTM-Reckless]"
        
        else: # PRUDENT (Default)
            # PRUDENT: Apply Volatility Scaling (Mocking Eq 5 from Paper)
            # Confidence = Model_Conf * (1 - Volatility_Penalty)
            volatility = 0.02 # distinct from ATR, assuming annual vol proxy
            eqn_5_modifier = 1.0 / (1.0 + volatility * 10) 
            
            new_confidence = original_confidence * eqn_5_modifier
            signal['reason'] = signal.get("reason", "") + " [LSTM-Prudent]"
            
            # Risk Gate: Reject low confidence in Prudent mode
            if new_confidence < 0.6:
                logger.info(f"🛡️ [LSTM] Prudent Mode rejected signal (Conf: {new_confidence:.2f} < 0.6)")
                return None

        signal['confidence'] = new_confidence
        logger.info(f"✨ [LSTM-{mode}] Adjusted signal: {original_confidence:.2f} -> {new_confidence:.2f}")
            
        return signal
