import os
import importlib.util
import inspect
import logging

logger = logging.getLogger("reverseaffinity.plugins")


class PluginBase:
    name = "Unnamed Plugin"
    author = ""
    version = "0.1"
    description = ""

    def on_load(self, app_context):
        pass

    def on_unload(self, app_context):
        pass

    def register_tools(self):
        return []

    def register_filters(self):
        return []

    def register_file_formats(self):
        return []

    def register_menu_items(self, menu_bar):
        pass

    def register_panels(self, tab_widget):
        pass


class PluginManager:
    def __init__(self, plugin_dir=None):
        if plugin_dir is None:
            plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.plugin_dir = os.path.abspath(plugin_dir)
        self.plugins = []

    def discover(self):
        self.plugins.clear()
        if not os.path.isdir(self.plugin_dir):
            logger.warning("Plugin directory not found: %s", self.plugin_dir)
            return
        for fname in sorted(os.listdir(self.plugin_dir)):
            if fname.startswith("_") or not fname.endswith(".py"):
                continue
            path = os.path.join(self.plugin_dir, fname)
            if not os.path.isfile(path):
                continue
            mod = self._load_module(fname[:-3], path)
            if mod is None:
                continue
            for _, cls in inspect.getmembers(mod, inspect.isclass):
                if cls is not PluginBase and issubclass(cls, PluginBase):
                    instance = cls()
                    self.plugins.append(instance)
                    logger.info("Loaded plugin: %s v%s", instance.name, instance.version)
        return self.plugins

    def _load_module(self, mod_name, path):
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                return None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            logger.exception("Failed to load plugin: %s", path)
            return None

    def load_all(self, app_context):
        for plugin in self.plugins:
            try:
                plugin.on_load(app_context)
            except Exception:
                logger.exception("Error loading plugin: %s", plugin.name)

    def unload_all(self, app_context):
        for plugin in self.plugins:
            try:
                plugin.on_unload(app_context)
            except Exception:
                pass
