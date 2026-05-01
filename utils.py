import os
import platform
import subprocess


def open_folder(path):
    """Ouvre un dossier dans l'explorateur de fichiers (cross-platform)."""
    if not os.path.exists(path):
        return False
    system = platform.system()
    if system == "Windows":
        os.startfile(path)
    elif system == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
    return True


def draw_section(layout, props, prop_name, label):
    box = layout.box()
    row = box.row(align=True)
    is_open = getattr(props, prop_name)
    icon = "TRIA_DOWN" if is_open else "TRIA_RIGHT"
    row.prop(props, prop_name, icon=icon, icon_only=True, emboss=False)
    row.label(text=label)
    return box if is_open else None
