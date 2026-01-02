import os
import importlib.util
import inspect
from typing import Any, Callable, Dict, List, Optional

# --- 1. Base Plugin Class ---

class BasePlugin:
    """
    The base class that all Olympus plugins must inherit from.
    """
    def __init__(self, user_id: str, context: Dict[str, Any]):
        self.user_id = user_id
        self.context = context  # Shared context (e.g., DB connections, API clients)
        self.metadata = {
            "name": "Base Plugin",
            "version": "1.0.0",
            "description": "Standard base plugin"
        }

    def activate(self):
        """Called when the plugin is enabled."""
        pass

    def deactivate(self):
        """Called when the plugin is disabled."""
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

    def add_action(self, tag: str, callback: Callable):
        if tag not in self.actions:
            self.actions[tag] = []
        self.actions[tag].append(callback)

    def do_action(self, tag: str, *args, **kwargs):
        """Triggers a specific action hook."""
        if tag in self.actions:
            for callback in self.actions[tag]:
                callback(*args, **kwargs)

    def add_filter(self, tag: str, callback: Callable):
        if tag not in self.filters:
            self.filters[tag] = []
        self.filters[tag].append(callback)

    def apply_filters(self, tag: str, value: Any, *args, **kwargs) -> Any:
        """Modifies a value through a chain of filters."""
        if tag in self.filters:
            for callback in self.filters[tag]:
                value = callback(value, *args, **kwargs)
        return value

# --- 3. Plugin Loader ---

class PluginLoader:
    """
    Dynamically loads plugins from the /plugins directory.
    """
    def __init__(self, hook_manager: HookManager):
        self.hook_manager = hook_manager
        self.loaded_plugins: Dict[str, BasePlugin] = {}

    def load_from_directory(self, plugins_dir: str, user_id: str, context: Dict[str, Any]):
        """
        Scans the directory for plugin.py files and initializes them.
        """
        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir)
            return

        for folder in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, folder, "plugin.py")
            if os.path.isfile(plugin_path):
                self._load_plugin(plugin_path, folder, user_id, context)

    def _load_plugin(self, file_path: str, plugin_name: str, user_id: str, context: Dict[str, Any]):
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find the class that inherits from BasePlugin
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                    instance = obj(user_id, context)
                    instance.activate()
                    
                    # Register the plugin instance hooks (implementation specific)
                    # For this demo, we assume the plugin class has a 'register_hooks' method
                    if hasattr(instance, 'register_hooks'):
                        instance.register_hooks(self.hook_manager)
                    
                    self.loaded_plugins[f"{user_id}_{plugin_name}"] = instance
                    print(f"✅ Plugin '{plugin_name}' loaded for User: {user_id}")
                    
        except Exception as e:
            print(f"❌ Failed to load plugin {plugin_name}: {e}")

# --- Example of Core Execution (How Olympus would use this) ---

if __name__ == "__main__":
    # 1. Initialize Core
    hm = HookManager()
    loader = PluginLoader(hm)
    
    # 2. Setup Context (e.g., DB, Market Data Client)
    shared_ctx = {"db": "Postgres_Connection", "market": "Binance_Socket"}
    
    # 3. Load Plugins (In real app, this would be based on user settings)
    # loader.load_from_directory("./plugins", "user_123", shared_ctx)

    # Simple Demonstration of Hooks
    def example_filter(data):
        print(f"Filtering data: {data}")
        return data * 1.1 # Increase value by 10%

    hm.add_filter("calculate_signal", example_filter)
    
    final_signal = hm.apply_filters("calculate_signal", 100)
    print(f"Final Signal Value: {final_signal}")