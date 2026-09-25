import sys
import os

# Asegúrate de agregar 'src' al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# ============================================================
# 1. Cargar ttkbootstrap (aplica parches si puede)
# ============================================================
import ttkbootstrap
import ttkbootstrap.style
import ttkbootstrap.widgets
import ttkbootstrap.publisher
import ttkbootstrap.window

# Módulos opcionales (si alguno falla, no rompe la app)
for _mod in (
    "ttkbootstrap.tableview",
    "ttkbootstrap.tooltip",
    "ttkbootstrap.scrolled",
    "ttkbootstrap.dialogs",
    "ttkbootstrap.icons",
    "ttkbootstrap.toast",
):
    try:
        __import__(_mod)
    except Exception:
        pass


# ============================================================
# 2. RED DE SEGURIDAD: tolerancia a "unknown option -bootstyle"
#
# Problema conocido: al empaquetar ttkbootstrap con PyInstaller,
# los "monkey patches" a Tkinter no se aplican correctamente en
# Windows 7 y Windows 10 (bug estructural del empaquetado).
#
# Solución: envolver el __init__ de los widgets ttk para que si
# falla por "bootstyle", se reintente sin ese parámetro.
# Así la app SIEMPRE arranca. Si los parches funcionan, se ve
# bonita (con colores). Si no, se ve con el tema global pero
# totalmente funcional.
# ============================================================
def _install_bootstyle_safety_net():
    try:
        from tkinter import ttk as _ttk
    except Exception:
        return

    def _make_wrapper(orig):
        def _wrapper(self, *args, **kwargs):
            try:
                return orig(self, *args, **kwargs)
            except Exception as _e:
                msg = str(_e)
                if "bootstyle" in msg and "bootstyle" in kwargs:
                    # Reintentar sin bootstyle
                    kwargs.pop("bootstyle", None)
                    return orig(self, *args, **kwargs)
                raise
        _wrapper._bootstyle_safety_installed = True
        return _wrapper

    # Iterar TODAS las clases del módulo ttk y envolver su __init__
    for _name in dir(_ttk):
        try:
            _cls = getattr(_ttk, _name)
        except Exception:
            continue
        if not isinstance(_cls, type):
            continue
        try:
            _orig = _cls.__init__
        except Exception:
            continue
        if getattr(_orig, "_bootstyle_safety_installed", False):
            continue
        try:
            _cls.__init__ = _make_wrapper(_orig)
        except Exception:
            pass

    # También parchear tkinter.Widget para widgets base
    try:
        import tkinter as _tk
        for _name in dir(_tk):
            try:
                _cls = getattr(_tk, _name)
            except Exception:
                continue
            if not isinstance(_cls, type):
                continue
            if not hasattr(_cls, "__init__"):
                continue
            try:
                _orig = _cls.__init__
            except Exception:
                continue
            if getattr(_orig, "_bootstyle_safety_installed", False):
                continue
            try:
                _cls.__init__ = _make_wrapper(_orig)
            except Exception:
                pass
    except Exception:
        pass


_install_bootstyle_safety_net()


# ============================================================
# 3. Ahora sí importar la vista principal
# ============================================================
from presentation.views.main_view import MainView

if __name__ == "__main__":
    app = MainView()
    app.mainloop()