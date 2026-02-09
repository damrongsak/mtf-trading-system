import importlib.util
import inspect
import logging
import os
from typing import Any, Callable, Dict, List, Optional
from abc import ABC, abstractmethod

# Configure logging
logger = logging.getLogger("plugin_engine")

# --- 1. Base Plugin Class ---

class BasePlugin(ABC):
    """
    The base class that all Olympus plugins must inherit from.
    """
    def __init__(self, user_id: str, context: Dict[str, Any], config: Dict[str, Any] = None):
        self.user_id = user_id
        self.context = context  # Shared context (e.g., DB connections, API clients)
        self.config = config or {} # User-specific configuration
        self.metadata = {
            "name": "Base Plugin",
            "version": "1.0.0",
            "description": "Standard base plugin",
            "author": "Unknown"
        }

    @abstractmethod
    def activate(self):
        """Called when the plugin is enabled."""
        pass

    @abstractmethod
    def deactivate(self):
        """Called when the plugin is disabled."""
        pass

    def register_hooks(self, hook_manager: 'HookManager'):
        """
        Override this to register actions and filters.
        Example:
            hook_manager.add_action("on_market_data", self.process_data)
        """
        pass

# --- 2. Hook Manager (Actions & Filters) ---

class HookManager:
    """
    Manages Actions (triggers) and Filters (data modifiers).
    Inspired by WordPress's hook system.
    """
    def __init__(self):
        self.actions: Dict[str, List[Callable]] = {}
        self.filters: Dict[str, List[Callable]] = {}

    def add_action(self, tag: str, callback: Callable) -> None:
        """Register a callback for an action tag."""
        if tag not in self.actions:
            self.actions[tag] = []
        self.actions[tag].append(callback)
        logger.debug(f"Action registered: {tag} -> {callback.__name__}")

    def do_action(self, tag: str, *args, **kwargs) -> None:
        """Triggers a specific action hook."""
        if tag in self.actions:
            logger.debug(f"Triggering action: {tag}")
            for callback in self.actions[tag]:
                try:
                    import asyncio
                    res = callback(*args, **kwargs)
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)
                except Exception as e:
                    logger.error(f"Error in action '{tag}' callback '{callback.__name__}': {e}")
                    # Trigger system-level error hook if not recursive
                    if tag != "on_plugin_error":
                        self.do_action("on_plugin_error", {"tag": tag, "error": str(e), "plugin": getattr(callback, "__module__", "unknown")})

    def add_filter(self, tag: str, callback: Callable) -> None:
        """Register a callback for a filter tag."""
        if tag not in self.filters:
            self.filters[tag] = []
        self.filters[tag].append(callback)
        logger.debug(f"Filter registered: {tag} -> {callback.__name__}")

    def apply_filters(self, tag: str, value: Any, *args, **kwargs) -> Any:
        """Modifies a value through a chain of filters."""
        if tag in self.filters:
            for callback in self.filters[tag]:
                try:
                    value = callback(value, *args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in filter '{tag}' callback '{callback.__name__}': {e}")
                    if tag != "on_plugin_error":
                        self.do_action("on_plugin_error", {"tag": tag, "error": str(e), "plugin": getattr(callback, "__module__", "unknown")})
        return value

# --- 3. Plugin Loader ---

class PluginLoader:
    """
    Dynamically loads plugins from the /plugins directory.
    """
    def __init__(self, hook_manager: HookManager, plugin_dir: str):
        self.hook_manager = hook_manager
        self.plugin_dir = plugin_dir
        self.loaded_plugins: Dict[str, BasePlugin] = {} # Key: "{user_id}_{plugin_id}"

    def load_plugin_for_user(self, plugin_id: str, user_id: str, context: Dict[str, Any], config: Dict[str, Any] = None) -> bool:
        """
        Loads and activates a specific plugin for a user.
        """
        plugin_path = os.path.join(self.plugin_dir, plugin_id, "plugin.py")
        
        if not os.path.isfile(plugin_path):
            logger.error(f"Plugin file not found: {plugin_path}")
            return False

        try:
            # unique module name to avoid conflicts
            module_name = f"plugins.{plugin_id}.{user_id}" 
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find the class that inherits from BasePlugin
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                    plugin_class = obj
                    break
            
            if not plugin_class:
                logger.error(f"No BasePlugin subclass found in {plugin_id}")
                return False

            # Instantiate and activate
            instance = plugin_class(user_id, context, config)
            instance.activate()
            instance.register_hooks(self.hook_manager)
            
            instance_key = f"{user_id}_{plugin_id}"
            self.loaded_plugins[instance_key] = instance
            logger.info(f"✅ Plugin '{plugin_id}' loaded for User: {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load plugin {plugin_id}: {e}")
            return False

    def unload_plugin_for_user(self, plugin_id: str, user_id: str):
        """
        Deactivates and removes a plugin instance.
        """
        instance_key = f"{user_id}_{plugin_id}"
        if instance_key in self.loaded_plugins:
            instance = self.loaded_plugins[instance_key]
            try:
                instance.deactivate()
                # Note: Unregistering hooks is complex because HookManager doesn't track owner.
                # Ideally, we'd wrap callbacks or have HookManager track instance IDs.
                # For MVP, we accept that hooks might linger until restart, or we implement remove_action/filter.
                del self.loaded_plugins[instance_key]
                logger.info(f"🛑 Plugin '{plugin_id}' unloaded for User: {user_id}")
            except Exception as e:
                logger.error(f"Error unloading plugin {plugin_id}: {e}")
