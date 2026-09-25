import sys
import os

# Asegúrate de agregar 'src' al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# === FORZAR CARGA COMPLETA DE ttkbootstrap ===
# Esto es CRÍTICO para que el .exe funcione en Windows 7 y Windows 10/11.
# ttkbootstrap aplica "monkey patches" a Tkinter al importarse. Si no se
# aplican ANTES de crear los widgets, aparece:
#   _tkinter.TclError: unknown option "-bootstyle"
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

# Ahora sí importar la vista principal
from presentation.views.main_view import MainView

if __name__ == "__main__":
    app = MainView()
    app.mainloop()