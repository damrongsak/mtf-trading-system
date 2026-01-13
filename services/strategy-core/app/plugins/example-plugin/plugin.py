from app.plugins.plugin_engine import BasePlugin
import logging

logger = logging.getLogger(__name__)

class ExamplePlugin(BasePlugin):
    """
    An example plugin to demonstrate the Olympus Plugin Architecture.
    It logs market data and filters signals based on simple logic.
    """
    
    def __init__(self, user_id, context, config=None):
        super().__init__(user_id, context, config)
        self.metadata.update({
            "name": "Example Plugin",
            "version": "0.1.0",
            "description": "Demonstrates Actions (logging) and Filters (signal checks).",
            "author": "Antigravity",
            "category": "UTILITY" 
        })

    def activate(self):
        logger.info(f"🚀 Example Plugin Activated for User: {self.user_id}")
        # Initialize any resources here (e.g. load models, connect DB)

    def deactivate(self):
        logger.info(f"🛑 Example Plugin Deactivated")
        # Clean up resources

    def register_hooks(self, hook_manager):
        # 1. Action: Log every time we receive market data
        hook_manager.add_action("on_market_data", self.log_price)
        
        # 2. Filter: Block signals if confidence is too low (using config)
        hook_manager.add_filter("filter_signal", self.check_confidence)

    def log_price(self, data):
        """
        Action hook: Just logs the data. flow continues.
        """
        symbol = data.get('symbol', 'UNKNOWN')
        price = data.get('close', 0)
        logger.info(f"[ExamplePlugin] 📈 {symbol} price update: {price}")

    def check_confidence(self, signal, state=None):
        """
        Filter hook: Can block or modify the signal.
        """
        # Get threshold from config (default to 0.5 if not set)
        threshold = self.config.get('min_confidence', 0.5)
        
        confidence = signal.get('confidence', 0.0)
        
        if confidence < threshold:
            logger.warning(f"[ExamplePlugin] ✋ Blocking signal for {signal.get('symbol')} (Confidence {confidence} < {threshold})")
            return None # Block the signal
            
        return signal # Pass the signal through
