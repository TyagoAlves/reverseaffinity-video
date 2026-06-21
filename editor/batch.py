import os
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtCore import Qt


def batch_export_layers(layer_stack, base_path, fmt='png', suffix_template='_{name}',
                        options=None, parent=None):
    ext = f'.{fmt.lstrip(".")}'
    layers = [l for l in layer_stack.layers if l.visible and l.name != 'Background']
    if not layers:
        return False

    progress = QProgressDialog("Exporting layers...", "Cancel", 0, len(layers), parent)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)

    success = True
    for i, layer in enumerate(layers):
        if progress.wasCanceled():
            break

        safe_name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in layer.name)
        suffix = suffix_template.replace('{name}', safe_name).replace('{i}', str(i))
        name_base, _ = os.path.splitext(base_path)
        out_path = f"{name_base}{suffix}{ext}"

        try:
            composite = layer_stack.layers[layer_stack.layers.index(layer)].image
            ok = composite.save(out_path, fmt.upper())
            if not ok:
                success = False
        except Exception:
            success = False

        progress.setValue(i + 1)

    progress.close()
    return success


def batch_export_layers_separate(layer_stack, dir_path, base_name='layer',
                                 fmt='png', options=None, parent=None):
    ext = f'.{fmt.lstrip(".")}'
    layers = [l for l in layer_stack.layers if l.visible]
    if not layers:
        return False

    progress = QProgressDialog("Exporting layers...", "Cancel", 0, len(layers), parent)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)

    success = True
    for i, layer in enumerate(layers):
        if progress.wasCanceled():
            break

        safe_name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in layer.name)
        out_path = os.path.join(dir_path, f"{base_name}_{safe_name}{ext}")

        try:
            ok = layer.image.save(out_path, fmt.upper())
            if not ok:
                success = False
        except Exception:
            success = False

        progress.setValue(i + 1)

    progress.close()
    return success
