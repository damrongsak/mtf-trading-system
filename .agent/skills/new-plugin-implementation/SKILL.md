---
name: new-plugin-implementation
description: |
    Use this skill when you need to create, add, or implement a new plugin in the `strategy-core` service.
    This helps standardize plugin structure and hook usage.
---

# New Plugin Implementation
**Goal:** Create a standardized plugin in `services/strategy-core/app/plugins`.

## Prerequisites
*   Understand if the plugin is an **Action** (reacts to events) or a **Filter** (modifies data).
*   Identify the unique `plugin-id` (folder name).

## Process

1.  **Create Plugin Directory**
    *   Create directory: `services/strategy-core/app/plugins/<plugin-id>/`.
    *   Create an empty `__init__.py` inside.

2.  **Implement Plugin Class**
    *   Create `plugin.py`.
    *   Import `BasePlugin`: `from app.plugins.plugin_engine import BasePlugin`.
    *   Class name should match the folder name (CamelCase).
    *   **MUST** implement:
        *   `__init__`: Set metadata (`name`, `version`, `description`).
        *   `activate()`: Log start, initialize resources.
        *   `deactivate()`: Log stop, cleanup.
        *   `register_hooks(hook_manager)`: Register actions and filters.

3.  **Register Hooks**
    *   **Actions:** `hook_manager.add_action("tag", self.callback)`
        *   Use for logging, notifying side effects, or external integrations.
    *   **Filters:** `hook_manager.add_filter("tag", self.callback)`
        *   Use for modifying signals, data, or blocking execution (return `None`).

## Code Template
```python
from app.plugins.plugin_engine import BasePlugin
import logging

logger = logging.getLogger(__name__)

class MyNewPlugin(BasePlugin):
    def __init__(self, user_id, context, config=None):
        super().__init__(user_id, context, config)
        self.metadata.update({
            "name": "My New Plugin",
            "version": "1.0.0",
            "description": "Does amazing things."
        })

    def activate(self):
        logger.info(f"Plugin activated for {self.user_id}")

    def deactivate(self):
        logger.info("Plugin deactivated")

    def register_hooks(self, hook_manager):
        hook_manager.add_action("on_market_data", self.on_data)

    def on_data(self, data):
        logger.info(f"Received data: {data}")
```

## Best Practices
*   **Error Handling:** Never let a plugin crash the core. Wrap logic in `try/except`.
*   **Logging:** Use strict prefixing `[PluginName]` in logs.
*   **Config:** Use `self.config.get()` for all user-adjustable parameters.
