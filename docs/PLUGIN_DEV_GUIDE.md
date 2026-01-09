# Plugin Developer Guide

The **MTF Trading System** (Strategy Core) uses a modular **Plugin Architecture** to extend functionality without modifying the core engine. This guide explains how to build, deploy, and manage plugins.

## 🏗️ Architecture

Plugins are python packages located in `services/strategy-core/app/plugins/`.
The **Plugin Engine** is responsible for:
1.  **Discovery**: Finding valid plugins in the directory.
2.  **Loading**: importing the `plugin.py` module.
3.  **Lifecycle**: Calling `activate()` / `deactivate()`.
4.  **Hooks**: Registering **Actions** and **Filters** for event-driven logic.

### Directory Structure

```text
services/strategy-core/app/plugins/
├── plugin_engine.py       # Core Logic
├── risk-guardrail/        # [Plugin] Checks risk limits
│   └── plugin.py          # Entry point
└── olympus-lstm-predictor # [Plugin] ML Model
    ├── plugin.py
    └── model.h5
```

---

## 🚀 Creating a New Plugin

To create a new plugin, follow these steps:

1.  Create a folder: `services/strategy-core/app/plugins/my-new-plugin/`
2.  Create a file: `plugin.py` inside that folder.

### Base Template (`plugin.py`)

Every plugin must inherit from `BasePlugin`.

```python
from app.plugins.plugin_engine import BasePlugin, HookManager
import logging

logger = logging.getLogger(__name__)

class MyNewPlugin(BasePlugin):
    """
    A brief description of what your plugin does.
    """
    
    # --- 1. Metadata ---
    def __init__(self, user_id, context, config=None):
        super().__init__(user_id, context, config)
        self.metadata.update({
            "name": "My Custom Plugin",
            "version": "1.0.0",
            "description": "Explaining what this plugin does...",
            "author": "Your Name"
        })

    # --- 2. Lifecycle Methods ---
    def activate(self):
        """Called when the plugin is loaded/enabled."""
        logger.info(f"✅ My Plugin Activated for User: {self.user_id}")

    def deactivate(self):
        """Called when the plugin is unloaded/disabled."""
        logger.info(f"🛑 My Plugin Deactivated")

    # --- 3. Hook Registration ---
    def register_hooks(self, hook_manager: HookManager):
        """
        Register your Actions and Filters here.
        """
        # Action: Listen to events (Fire-and-forget)
        hook_manager.add_action("on_market_data", self.on_market_data)
        
        # Filter: Modify data pipelines (Intercept & Change)
        hook_manager.add_filter("filter_signal", self.check_signal)

    # --- 4. Logic Implementation ---
    def on_market_data(self, data):
        """Triggered when new market data (tick/candle) arrives."""
        symbol = data.get('symbol')
        price = data.get('close') or data.get('bid')
        logger.debug(f"[{self.metadata['name']}] Saw {symbol} at {price}")

    def check_signal(self, signal, state=None):
        """
        Intercept a trading signal.
        Return:
          - modified_signal (dict): To pass it along
          - None: To BLOCK the signal entirely
        """
        confidence = signal.get('confidence', 0.0)
        
        # Example Logic: Reject low confidence
        if confidence < 0.5:
            logger.warning(f"Blocking signal due to low confidence: {confidence}")
            return None 
            
        return signal
```

---

## 🪝 Hook System Reference

The system uses two types of hooks:

### 1. Actions (`add_action`)
Events that happen in the system. Your callback receives data but does not return anything.

| Hook Name | Arguments | Description |
| :--- | :--- | :--- |
| `on_market_data` | `data` (dict) | Fired when a new tick or candle arrives. |
| `on_plugin_error` | `error_ctx` (dict) | Fired when any plugin raises an exception. |

### 2. Filters (`add_filter`)
Pipelines where data is passed through. Your callback **MUST** return a value (modified or original). returning `None` usually stops the pipeline.

| Hook Name | Arguments | Returns | Description |
| :--- | :--- | :--- | :--- |
| `filter_signal` | `signal` (dict), `state` (obj) | `dict` or `None` | Process a trading signal before execution. Return `None` to block. |
| `filter_trade_request` | `payload` (dict) | `dict` or `None` | Final check before sending order to Execution Service. |

---

## ⚠️ Important Rules

1.  **Method Naming**: You **MUST** use `register_hooks(self, hook_manager)`.
    *   ❌ Incorrect: `register()`
    *   ✅ Correct: `register_hooks()`
2.  **Registration**: Use `hook_manager.add_action` or `hook_manager.add_filter`.
    *   ❌ Incorrect: `register_filter()`
    *   ✅ Correct: `add_filter()`
3.  **Non-Blocking**: Do not put heavy blocking code (like `time.sleep`) in hooks. Use `asyncio.create_task` if you need to run long background operations, or offload to a separate worker.
4.  **Error Handling**: If your plugin crashes, the `on_plugin_error` hook is triggered, but try to use `try/except` blocks within your functions.

## 🧪 Testing Your Plugin
To test your plugin without the full engine:

1.  Add a `tests/` folder in your plugin directory.
2.  Mock `HookManager` and `BasePlugin`.
3.  Instantiate your class and call `register_hooks`.
4.  Manually invoke your callback methods with dummy data.
