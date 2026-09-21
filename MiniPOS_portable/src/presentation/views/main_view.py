import tkinter as tk
from tkinter import filedialog, font as tkfont
import ttkbootstrap as ttk
from ttkbootstrap import Style
import os
import shutil
import sys
import queue
import threading
from datetime import datetime
from application.use_case.product_use_case import ProductCase
from application.use_case.sale_use_case import SaleCase
from infrastucture.db.db_manager import DBManager
from presentation.views.widgets import (
    apply_titlebar_theme, center_window, show_popup_smooth,
    get_menu_font, DarkMenuBar, MD, make_scrollable, make_scrolled_treeview,
    get_business_info, save_business_info
)
from presentation.views.payment_view import PaymentView
from presentation.views.inventory_view import InventoryView


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class MainView(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.state('zoomed')
        except Exception:
            self.geometry("1400x900")

        self.current_theme = 'darkly'
        self.style = Style(theme=self.current_theme)
        self.configure(bg=self.style.colors.bg)
        self.is_fullscreen = False

        self._setup_dark_green_style()

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.db_path = os.path.join(base_dir, "data", "ventas.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.db_manager = DBManager(self.db_path)
        self.product_use_case = ProductCase(self.db_manager)
        self.sale_use_case = SaleCase(self.db_manager)

        self.tray_icon = None
        self.tray_thread = None
        self.tray_queue = queue.Queue()

        # ✅ Actualizar título con info del negocio
        self._update_window_title()

        if not self._check_startup_password():
            self.destroy()
            return

        self.create_widgets()
        self.show_page("pagos")
        self._apply_font_size()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._poll_tray_queue)

        self.bind('<F2>', lambda e: self.inventory_view.add_product_popup()
                  if self.current_page == "inventario" else None)
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.after(200, lambda: apply_titlebar_theme(self, self.current_theme == 'darkly'))

    def _update_window_title(self):
        try:
            info = get_business_info(self.db_manager)
            tipo = (info.get("type") or "").strip()
            nombre = (info.get("name") or "").strip()
            base = "MiniPOS Portable v2.0"
            if tipo and nombre:
                self.title(f"{base} — {tipo}, {nombre}")
            elif nombre:
                self.title(f"{base} — {nombre}")
            elif tipo:
                self.title(f"{base} — {tipo}")
            else:
                self.title(base)
        except Exception:
            self.title("MiniPOS Portable v2.0")

    # =========== BANDEJA ===========
    def _poll_tray_queue(self):
        try:
            while True:
                action = self.tray_queue.get_nowait()
                if action == "show":
                    self._show_from_tray()
                elif action == "quit":
                    self._real_quit()
                    return
        except queue.Empty:
            pass
        except Exception:
            pass
        try:
            self.after(300, self._poll_tray_queue)
        except Exception:
            pass

    def _on_close(self):
        to_tray = self.db_manager.get_setting("close_to_tray", "0") == "1"
        if to_tray:
            self._hide_to_tray()
            return
        r = MD.yesno(
            "¿Estás seguro que deseas salir de MiniPOS Portable?\n\n"
            "Tus datos quedan guardados automáticamente.",
            "Confirmar salida", parent=self)
        if r == "Yes":
            self._real_quit()

    def _real_quit(self):
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            self.db_manager.close_connection()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        sys.exit(0)

    def _hide_to_tray(self):
        try:
            self.withdraw()
        except Exception:
            pass
        if self.tray_icon is None:
            self._create_tray_icon()

    def _create_tray_icon(self):
        try:
            from PIL import Image, ImageDraw
            import pystray
        except ImportError:
            try:
                self.deiconify()
                self.iconify()
            except Exception:
                pass
            return

        img = Image.new("RGBA", (64, 64), (10, 77, 31, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([4, 4, 60, 60], outline=(168, 230, 168, 255), width=3)
        draw.rectangle([18, 24, 46, 28], fill=(168, 230, 168, 255))
        draw.rectangle([20, 16, 26, 48], fill=(168, 230, 168, 255))
        draw.rectangle([38, 16, 44, 48], fill=(168, 230, 168, 255))
        draw.rectangle([20, 30, 44, 34], fill=(168, 230, 168, 255))

        def on_show(icon, item):
            self.tray_queue.put("show")

        def on_quit(icon, item):
            self.tray_queue.put("quit")

        menu = pystray.Menu(
            pystray.MenuItem("Mostrar MiniPOS", on_show, default=True),
            pystray.MenuItem("Salir", on_quit),
        )

        self.tray_icon = pystray.Icon("MiniPOS", img, "MiniPOS Portable", menu)

        def run_tray():
            try:
                self.tray_icon.run()
            except Exception:
                pass

        self.tray_thread = threading.Thread(target=run_tray, daemon=True)
        self.tray_thread.start()

    def _show_from_tray(self):
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.tray_icon = None

        try:
            self.deiconify()
            self.state('zoomed')
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # =========== ESTILOS ===========
    def _setup_dark_green_style(self):
        try:
            self.style.configure(
                "DarkGreen.TButton",
                background="#0a4d1f", foreground="#c8e6c9",
                borderwidth=0, focuscolor="#0a4d1f",
                padding=8, font=("Arial", 11, "bold"))
            self.style.map(
                "DarkGreen.TButton",
                background=[("active", "#083d18"), ("pressed", "#062e12"),
                            ("disabled", "#555555")],
                foreground=[("active", "#ffffff"), ("disabled", "#999999")])
        except Exception:
            pass

    # =========== CONTRASEÑA ===========
    def _check_startup_password(self):
        pwd = self.db_manager.get_setting("startup_password", "")
        if not pwd:
            return True
        self.withdraw()
        pop = tk.Toplevel(self)
        pop.title("MiniPOS - Iniciar sesión")
        pop.geometry("380x230")
        pop.transient(self)
        pop.configure(bg=self.style.colors.bg)
        pop.protocol("WM_DELETE_WINDOW", lambda: self._cancel_login(pop))
        pop.withdraw()

        tk.Label(pop, text="🔒 Contraseña requerida",
                 font=("Arial", 14, "bold"),
                 bg=self.style.colors.bg, fg=self.style.colors.fg).pack(pady=15)
        v = tk.StringVar()
        e = ttk.Entry(pop, textvariable=v, show="•", width=25,
                      font=("Arial", 14), justify="center")
        e.pack(pady=10)
        resultado = {"ok": False}

        def verificar(ev=None):
            if v.get() == pwd:
                resultado["ok"] = True
                pop.destroy()
            else:
                MD.show_error("Contraseña incorrecta", "Error", parent=pop)
                v.set("")
            return "break"

        ttk.Button(pop, text="Ingresar", command=verificar,
                   style="DarkGreen.TButton").pack(pady=10)
        e.bind("<Return>", verificar)

        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

        def set_focus():
            try:
                if pop.winfo_exists():
                    e.focus_set()
            except Exception:
                pass
        pop.after(50, set_focus)
        pop.after(250, set_focus)

        self.wait_window(pop)
        if resultado["ok"]:
            self.deiconify()
            return True
        return False

    def _cancel_login(self, pop):
        pop.destroy()

    def _change_password(self):
        if not is_admin():
            MD.show_warning(
                "Debes ejecutar la app COMO ADMINISTRADOR\npara cambiar la contraseña.",
                "Permisos insuficientes", parent=self)
            return
        actual = self.db_manager.get_setting("startup_password", "")
        pop = tk.Toplevel(self)
        pop.title("Cambiar contraseña")
        pop.geometry("400x400")
        pop.transient(self)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg
        fg = self.style.colors.fg

        tk.Label(pop, text="🔐 Cambiar contraseña",
                 font=("Arial", 14, "bold"), bg=bg, fg=fg).pack(pady=15)
        tk.Label(pop, text="Contraseña actual:", bg=bg, fg=fg).pack()
        e1 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e1.pack(pady=5)
        tk.Label(pop, text="Nueva contraseña:", bg=bg, fg=fg).pack()
        e2 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e2.pack(pady=5)
        tk.Label(pop, text="Confirmar nueva:", bg=bg, fg=fg).pack()
        e3 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e3.pack(pady=5)
        vaciar = tk.BooleanVar(value=False)
        ttk.Checkbutton(pop, text="Quitar contraseña (dejar vacío)",
                        variable=vaciar).pack(pady=8)

        def aplicar(ev=None):
            if vaciar.get():
                self.db_manager.set_setting("startup_password", "")
                MD.show_info("Contraseña eliminada.", "Listo", parent=pop)
                pop.destroy()
                return "break"
            if e1.get() != actual:
                MD.show_error("La contraseña actual no coincide.", "Error", parent=pop)
                return "break"
            if len(e2.get()) < 4:
                MD.show_error("La nueva contraseña debe tener al menos 4 caracteres.",
                              "Error", parent=pop)
                return "break"
            if e2.get() != e3.get():
                MD.show_error("Las contraseñas nuevas no coinciden.", "Error", parent=pop)
                return "break"
            self.db_manager.set_setting("startup_password", e2.get())
            MD.show_info("Contraseña cambiada.", "Listo", parent=pop)
            pop.destroy()
            return "break"

        ttk.Button(pop, text="Guardar", command=aplicar,
                   style="DarkGreen.TButton").pack(pady=12)
        e1.bind("<Return>", aplicar)
        e2.bind("<Return>", aplicar)
        e3.bind("<Return>", aplicar)
        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

        def set_focus():
            try:
                if pop.winfo_exists():
                    e1.focus_set()
            except Exception:
                pass
        pop.after(50, set_focus)

    def _setup_password_first_time(self):
        pop = tk.Toplevel(self)
        pop.title("Configurar contraseña")
        pop.geometry("380x280")
        pop.transient(self)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg
        fg = self.style.colors.fg

        tk.Label(pop, text="🔐 Crear contraseña de inicio",
                 font=("Arial", 14, "bold"), bg=bg, fg=fg).pack(pady=15)
        tk.Label(pop, text="Nueva contraseña (mín. 4 caracteres):",
                 bg=bg, fg=fg).pack()
        e1 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e1.pack(pady=5)
        tk.Label(pop, text="Confirmar:", bg=bg, fg=fg).pack()
        e2 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e2.pack(pady=5)

        def guardar(ev=None):
            if len(e1.get()) < 4:
                MD.show_error("Mínimo 4 caracteres.", "Error", parent=pop)
                return "break"
            if e1.get() != e2.get():
                MD.show_error("No coinciden.", "Error", parent=pop)
                return "break"
            self.db_manager.set_setting("startup_password", e1.get())
            MD.show_info("Contraseña activada. Se pedirá al iniciar.", "Listo", parent=pop)
            pop.destroy()
            return "break"

        ttk.Button(pop, text="Guardar", command=guardar,
                   style="DarkGreen.TButton").pack(pady=12)
        e1.bind("<Return>", guardar)
        e2.bind("<Return>", guardar)
        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

        def set_focus():
            try:
                if pop.winfo_exists():
                    e1.focus_set()
            except Exception:
                pass
        pop.after(50, set_focus)

    # =========== DATOS DEL NEGOCIO ===========
    def _open_business_popup(self):
        """Popup para ver/editar los datos del negocio."""
        pop = tk.Toplevel(self)
        pop.title("🏪 Datos del negocio")
        pop.geometry("520x620")
        pop.transient(self)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg
        fg = self.style.colors.fg

        info = get_business_info(self.db_manager)

        container = tk.Frame(pop, bg=bg)
        container.pack(fill="both", expand=True)

        refs = {}

        def build_content(parent):
            tk.Label(parent, text="🏪 DATOS DEL NEGOCIO",
                     font=("Arial", 15, "bold"), bg=bg, fg=fg).pack(pady=(15, 4))
            tk.Label(parent,
                     text="Estos datos aparecen en la barra de título y en Pagos/Inventario.",
                     font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))

            campos = [
                ("type", "Tipo de negocio (ej. tienda, víveres, supermercado):"),
                ("name", "Nombre del negocio (ej. el chontico):"),
                ("owner", "Dueño (ej. Rosa):"),
                ("place", "Lugar / Dirección:"),
                ("phone", "Teléfono:"),
                ("employees", "Empleados (separados por coma):"),
            ]

            for key, label in campos:
                ttk.Label(parent, text=label, font=("Arial", 10)).pack(pady=(10, 3), padx=20, anchor="w")
                entry = ttk.Entry(parent, width=52, font=("Arial", 11))
                entry.pack(pady=3, padx=20)
                if info.get(key):
                    entry.insert(0, info.get(key))
                refs[key] = entry

            ttk.Label(parent, text="Notas adicionales:",
                      font=("Arial", 10)).pack(pady=(10, 3), padx=20, anchor="w")
            notas = tk.Text(parent, width=52, height=4, font=("Arial", 10),
                            bg=bg, fg=fg, insertbackground=fg,
                            relief="solid", borderwidth=1, wrap="word")
            notas.pack(pady=3, padx=20)
            if info.get("notes"):
                notas.insert("1.0", info.get("notes"))
            refs["notes"] = notas

        def build_bottom(parent):
            def guardar():
                data = {}
                for k in ("type", "name", "owner", "place", "phone", "employees"):
                    try:
                        data[k] = refs[k].get()
                    except Exception:
                        data[k] = ""
                try:
                    data["notes"] = refs["notes"].get("1.0", tk.END).strip()
                except Exception:
                    data["notes"] = ""

                try:
                    save_business_info(self.db_manager, data)
                    self._update_window_title()
                    try:
                        self.payment_view.refresh_business_header()
                    except Exception:
                        pass
                    try:
                        self.inventory_view.refresh_business_header()
                    except Exception:
                        pass
                    pop.destroy()
                    MD.show_info("✅ Datos del negocio guardados.", "Listo", parent=self)
                except Exception as e:
                    MD.show_error(f"Error al guardar: {e}", "Error", parent=pop)

            ttk.Button(parent, text="💾 Guardar", command=guardar,
                       style="DarkGreen.TButton").pack(side="right", padx=6)
            ttk.Button(parent, text="Cancelar",
                       command=pop.destroy).pack(side="right", padx=6)

        make_scrollable(container, build_content, build_bottom, bg=bg)

        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

        pop.after(100, lambda: refs.get("type").focus_set() if pop.winfo_exists() and refs.get("type") else None)

    # =========== TAMAÑO DE FUENTE ===========
    def _apply_font_size(self):
        size = int(self.db_manager.get_setting("font_size", "11"))
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(size=size)
            except Exception:
                pass
        self.font_size = size
        self._update_tree_rowheights(size)
        self._setup_dark_green_style()
        try:
            self.style.configure("DarkGreen.TButton", font=("Arial", size, "bold"))
        except Exception:
            pass

    def _update_tree_rowheights(self, size):
        row_height = size + 14
        try:
            self.style.configure("Treeview", rowheight=row_height, font=("Arial", size))
            self.style.configure("Treeview.Heading", font=("Arial", size, "bold"))
        except Exception:
            pass

    def _change_font_size(self, delta):
        new = max(8, min(20, self.font_size + delta))
        self.db_manager.set_setting("font_size", str(new))
        self.font_size = new
        self._apply_font_size()
        try:
            self.payment_view.refresh_cart()
        except Exception:
            pass
        try:
            self.inventory_view.load_products()
        except Exception:
            pass

    # =========== UI ===========
    def create_widgets(self):
        self.menubar = DarkMenuBar(self, lambda: self.current_theme == 'darkly')
        self.menubar.pack(fill="x", side="top")

        def build_opciones(menu):
            menu.add_command(label="🌓 Cambiar Tema", command=self.toggle_theme)
            menu.add_separator()
            # ✅ NUEVO: Datos del negocio
            menu.add_command(label="🏪 Datos del negocio",
                             command=self._open_business_popup)
            menu.add_separator()
            sub_font = tk.Menu(menu, tearoff=0,
                               bg=self.style.colors.bg, fg=self.style.colors.fg,
                               activebackground=self.style.colors.selectbg,
                               activeforeground=self.style.colors.selectfg,
                               font=get_menu_font())
            sub_font.add_command(label="➕ Aumentar letra",
                                 command=lambda: self._change_font_size(1))
            sub_font.add_command(label="➖ Reducir letra",
                                 command=lambda: self._change_font_size(-1))
            menu.add_cascade(label="🔤 Tamaño de letra", menu=sub_font)
            sub_pwd = tk.Menu(menu, tearoff=0,
                              bg=self.style.colors.bg, fg=self.style.colors.fg,
                              activebackground=self.style.colors.selectbg,
                              activeforeground=self.style.colors.selectfg,
                              font=get_menu_font())
            sub_pwd.add_command(label="🆕 Activar/Crear contraseña",
                                command=self._setup_password_first_time)
            sub_pwd.add_command(label="🔐 Cambiar contraseña (admin)",
                                command=self._change_password)
            menu.add_cascade(label="🔑 Contraseña de inicio", menu=sub_pwd)
            menu.add_separator()

            self.tray_var = tk.BooleanVar(
                value=self.db_manager.get_setting("close_to_tray", "0") == "1")
            menu.add_checkbutton(
                label="🔽 Al presionar X ocultar en la bandeja",
                variable=self.tray_var,
                command=self._toggle_close_to_tray)

            self.autostart_var = tk.BooleanVar(value=self._is_autostart_enabled())
            menu.add_checkbutton(label="🚀 Iniciar con Windows",
                                 variable=self.autostart_var,
                                 command=self.toggle_autostart)
            menu.add_separator()
            menu.add_command(label="🔄 Reiniciar contador de ventas (#)",
                             command=self.reset_sales_counter)
            menu.add_separator()
            menu.add_command(label="📄 Reporte del Día (TXT)",
                             command=self.generate_daily_report)
            menu.add_command(label="📊 Reporte del Mes (Excel)",
                             command=self.generate_monthly_report)
            menu.add_separator()
            menu.add_command(label="📤 Exportar Base de Datos", command=self.export_db)
            menu.add_command(label="📥 Importar Base de Datos", command=self.import_db)

        def build_ventas(menu):
            menu.add_command(label="📊 Resumen de Ventas (agrupado)",
                             command=self.show_sales_summary)
            menu.add_command(label="💳 Fiados (agrupado por cliente)",
                             command=self.show_credit_sales)

        self.menubar.add_menu("Opciones", build_opciones)
        self.menubar.add_menu("Ventas", build_ventas)

        tabs = ttk.Frame(self, bootstyle="dark")
        tabs.pack(fill="x", padx=10, pady=(6, 0))

        self.btn_pagos = ttk.Button(tabs, text="🛒 PAGOS",
                                    style="DarkGreen.TButton",
                                    command=lambda: self.show_page("pagos"),
                                    width=14)
        self.btn_pagos.pack(side="left", padx=3, pady=2)

        self.btn_inv = ttk.Button(tabs, text="📦 INVENTARIO",
                                  style="DarkGreen.TButton",
                                  command=lambda: self.show_page("inventario"),
                                  width=14)
        self.btn_inv.pack(side="left", padx=3, pady=2)

        self.bind('<Control-Key-1>', lambda e: self.show_page("pagos"))
        self.bind('<Control-Key-2>', lambda e: self.show_page("inventario"))

        self.container = ttk.Frame(self, bootstyle="dark")
        self.container.pack(fill="both", expand=True, padx=10, pady=6)

        # ✅ Pasar db_manager + callback a las vistas
        self.payment_view = PaymentView(
            self.container, self.product_use_case, self.sale_use_case,
            self.db_manager, lambda: self.current_theme,
            on_business_click=self._open_business_popup)
        self.inventory_view = InventoryView(
            self.container, self.product_use_case,
            self.db_manager, lambda: self.current_theme,
            on_business_click=self._open_business_popup)
        self.current_page = None

    def _toggle_close_to_tray(self):
        val = "1" if self.tray_var.get() else "0"
        self.db_manager.set_setting("close_to_tray", val)
        if val == "1":
            MD.show_info(
                "✅ Al presionar X la ventana se ocultará en la bandeja del sistema.\n"
                "Para abrirla, haz clic en el ícono (junto al reloj) y elige 'Mostrar MiniPOS'.",
                "Modo bandeja", parent=self)
        else:
            MD.show_info("ℹ️ Al presionar X se pedirá confirmación para salir.",
                         "Modo normal", parent=self)

    # =========== REINICIAR CONTADOR ===========
    def reset_sales_counter(self):
        r1 = MD.yesno(
            "🔄 ¿Reiniciar el contador de ventas?\n\n"
            "Las ventas y fiados NO se borran.\n"
            "Solo el número que aparece como 'Venta #XX' se reiniciará.\n"
            "La próxima venta aparecerá como #01.\n\n"
            "¿Deseas continuar?",
            "Confirmar reinicio", parent=self, default_yes=True)
        if r1 != "Yes":
            return
        pw = self._ask_password_1234(self)
        if not pw:
            return
        try:
            self.sale_use_case.reset_sale_number_counter()
            MD.show_info(
                "✅ Contador reiniciado.\nLa próxima venta será #01.",
                "Listo", parent=self)
        except Exception as e:
            MD.show_error(f"Error al reiniciar: {e}", "Error", parent=self)

    def show_page(self, page):
        for w in (self.payment_view, self.inventory_view):
            w.pack_forget()
        if page == "pagos":
            self.payment_view.pack(fill="both", expand=True)
            self.btn_pagos.configure(style="DarkGreen.TButton")
            self.btn_inv.configure(bootstyle="secondary")
            self.current_page = "pagos"
        else:
            self.inventory_view.load_products()
            self.inventory_view.pack(fill="both", expand=True)
            self.btn_pagos.configure(bootstyle="secondary")
            self.btn_inv.configure(style="DarkGreen.TButton")
            self.current_page = "inventario"

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)

    def toggle_theme(self):
        self.current_theme = 'flatly' if self.current_theme == 'darkly' else 'darkly'
        self.style.theme_use(self.current_theme)
        self.configure(bg=self.style.colors.bg)
        self._setup_dark_green_style()
        apply_titlebar_theme(self, self.current_theme == 'darkly')
        self._apply_font_size()

    # ... [resto de show_sales_summary, show_credit_sales, _abonar_dialog, 
    #      _ask_password_1234, auto-inicio, reportes, exportar/importar
    #      IGUAL QUE EN EL ÚLTIMO main_view.py que te pasé]