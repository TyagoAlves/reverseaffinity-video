from plugins import PluginBase
import numpy as np


class InvertFilterPlugin(PluginBase):
    name = "Invert Colors Filter"
    author = "reverseaffinity"
    version = "1.0"
    description = "Adds an Invert Colors filter via plugin system"

    def register_filters(self):
        return [
            ("Invert Colors", self.invert_colors),
        ]

    def invert_colors(self, image, *args):
        return 255 - image

    def register_menu_items(self, menu_bar):
        filter_menu = None
        for action in menu_bar.actions():
            if action.text().replace("&", "").lower() in ("filter", "filtro"):
                filter_menu = action.menu()
                break
        if filter_menu:
            filter_menu.addAction(self.name, lambda: self._run_from_menu(filter_menu))

    def _run_from_menu(self, menu):
        parent = menu.parent()
        if hasattr(parent, 'canvas'):
            canvas = parent.canvas
            if canvas.layer_stack.active:
                canvas._save_state("Invert (Plugin)")
                canvas.layer_stack.active.image = self.invert_colors(
                    canvas.layer_stack.active.image
                )
                canvas._refresh()

    def on_load(self, ctx):
        print(f"[Plugin] {self.name} loaded")
