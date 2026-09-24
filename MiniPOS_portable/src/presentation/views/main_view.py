import tkinter as tk
from tkinter import filedialog, font as tkfont
import ttkbootstrap as ttk
from ttkbootstrap import Style
import os
import shutil
import sys
import queue
import threading
from datetime import datetime, timedelta

from application.use_case.product_use_case import ProductCase
from application.use_case.sale_use_case import SaleCase
from infrastucture.db.db_manager import DBManager
from presentation.views.widgets import (
    apply_titlebar_theme, center_window, show_popup_smooth,
    get_menu_font, DarkMenuBar, MD, make_scrollable,
    make_scrolled_treeview,
    get_business_info, save_business_info, make_inline_business_header,
)
from presentation.views.payment_view import PaymentView
from presentation.views.inventory_view import InventoryView


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _parse_float(s):
    try:
        return float(str(s).replace("$", "").replace(".", "").replace(",", ".").strip() or 0)
    except Exception:
        return 0.0


class MainView(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.state('zoomed')
        except Exception:
            self.geometry("1400x900")

        # Tema (leído desde settings)
        db_init = None
        try:
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     "..", "..", ".."))
            db_init_path = os.path.join(base, "data", "ventas.db")
            if os.path.exists(db_init_path):
                from infrastucture.db.db_manager import DBManager as _DBM
                db_init = _DBM(db_init_path)
        except Exception:
            db_init = None

        self.current_theme = 'darkly'
        if db_init:
            try:
                self.current_theme = db_init.get_setting("theme", "darkly") or "darkly"
            except Exception:
                pass
        self.style = Style(theme=self.current_theme)
        self.configure(bg=self.style.colors.bg)
        self.is_fullscreen = False
        self._setup_dark_green_style()

        # Base de datos
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     "..", "..", ".."))
        self.base_dir = base_dir
        self.db_path = os.path.join(base_dir, "data", "ventas.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.db_manager = DBManager(self.db_path)
        self.product_use_case = ProductCase(self.db_manager)
        self.sale_use_case = SaleCase(self.db_manager)

        # Bandeja
        self.tray_icon = None
        self.tray_thread = None
        self.tray_queue = queue.Queue()
        self._reset_check_timer = None
        self._backup_check_timer = None

        # Auto-reset, auto-backup y caja
        self._do_auto_reset(silent=True)
        self._do_auto_backup(silent=True)
        try:
            self.sale_use_case.get_or_create_today_cash_session()
        except Exception:
            pass

        self._update_window_title()

        if not self._check_startup_password():
            self.destroy()
            return

        self.create_widgets()
        self.show_page("pagos")
        self._apply_font_size()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._poll_tray_queue)
        self.after(3000, self._schedule_daily_reset_check)
        self.after(4000, self._schedule_backup_check)

        self.bind('<F2>', lambda e: self.inventory_view.add_product_popup()
                  if self.current_page == "inventario" else None)
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.after(200, lambda: apply_titlebar_theme(
            self, self.current_theme == 'darkly'))

    # ============================================================
    # AUTO-RESET
    # ============================================================
    def _do_auto_reset(self, silent=False):
        try:
            reinicio = self.sale_use_case.auto_reset_if_new_day()
            if reinicio and not silent:
                MD.show_info("🕛 Ha cambiado el día.\n\n"
                             "El contador de ventas se reinició automáticamente.",
                             "Reinicio automático", parent=self)
            return reinicio
        except Exception:
            return False

    def _schedule_daily_reset_check(self):
        self._check_daily_reset()

    def _check_daily_reset(self):
        try:
            reinicio = self._do_auto_reset(silent=False)
            if reinicio:
                try:
                    self.inventory_view.load_products()
                except Exception:
                    pass
                try:
                    self.sale_use_case.get_or_create_today_cash_session()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._reset_check_timer = self.after(60000, self._check_daily_reset)
        except Exception:
            pass

    # ============================================================
    # BACKUP AUTOMÁTICO
    # ============================================================
    def _get_backup_folder(self):
        try:
            custom = self.db_manager.get_setting("backup_folder", "") or ""
            if custom:
                return custom
        except Exception:
            pass
        return os.path.join(os.path.dirname(self.db_path), "backups")

    def _is_auto_backup_enabled(self):
        try:
            return self.db_manager.get_setting("auto_backup_enabled", "1") == "1"
        except Exception:
            return True

    def _get_last_backup_date(self):
        try:
            return self.db_manager.get_setting("last_backup_date", "") or ""
        except Exception:
            return ""

    def _set_last_backup_date(self, date_str):
        try:
            self.db_manager.set_setting("last_backup_date", date_str)
        except Exception:
            pass

    def _do_auto_backup(self, silent=False):
        try:
            if not self._is_auto_backup_enabled():
                return False
            hoy = datetime.now().strftime("%Y-%m-%d")
            if self._get_last_backup_date() == hoy:
                return False
            folder = self._get_backup_folder()
            os.makedirs(folder, exist_ok=True)
            destino = os.path.join(folder, f"ventas_{hoy}.db")
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, destino)
            self._set_last_backup_date(hoy)
            self.db_manager.get_connection()
            return True
        except Exception:
            try:
                self.db_manager.get_connection()
            except Exception:
                pass
            return False

    def _schedule_backup_check(self):
        self._check_auto_backup()

    def _check_auto_backup(self):
        try:
            self._do_auto_backup(silent=False)
        except Exception:
            pass
        try:
            self._backup_check_timer = self.after(3600000, self._check_auto_backup)
        except Exception:
            pass

    # ============================================================
    # TÍTULO
    # ============================================================
    def _update_window_title(self):
        try:
            info = get_business_info(self.db_manager)
            tipo = (info.get("type") or "").strip()
            nombre = (info.get("name") or "").strip()
            base = "MiniPOS Portable v2.5"
            if tipo and nombre:
                self.title(f"{base} — {tipo}, {nombre}")
            elif nombre:
                self.title(f"{base} — {nombre}")
            elif tipo:
                self.title(f"{base} — {tipo}")
            else:
                self.title(base)
        except Exception:
            self.title("MiniPOS Portable v2.5")

    def _refresh_business_header(self):
        try:
            if hasattr(self, "business_header") and self.business_header:
                self.business_header["refresh"]()
        except Exception:
            pass

    # ============================================================
    # BANDEJA
    # ============================================================
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
        r = MD.yesno("¿Salir de MiniPOS Portable?\n\n"
                     "Tus datos quedan guardados automáticamente.",
                     "Confirmar salida", parent=self)
        if r == "Yes":
            self._real_quit()

    def _real_quit(self):
        try:
            if self._reset_check_timer:
                self.after_cancel(self._reset_check_timer)
        except Exception:
            pass
        try:
            if self._backup_check_timer:
                self.after_cancel(self._backup_check_timer)
        except Exception:
            pass
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
                self.deiconify(); self.iconify()
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

        def on_show(icon, item): self.tray_queue.put("show")
        def on_quit(icon, item): self.tray_queue.put("quit")
        menu = pystray.Menu(
            pystray.MenuItem("Mostrar MiniPOS", on_show, default=True),
            pystray.MenuItem("Salir", on_quit))
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
            self.deiconify(); self.state('zoomed')
            self.lift(); self.focus_force()
        except Exception:
            pass

    # ============================================================
    # ESTILOS
    # ============================================================
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

    # ============================================================
    # CONTRASEÑA
    # ============================================================
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
            pop.grab_set(); pop.focus_force()
        except Exception:
            pass

        def set_focus():
            try:
                if pop.winfo_exists(): e.focus_set()
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
                pop.destroy(); return "break"
            if e1.get() != actual:
                MD.show_error("La contraseña actual no coincide.", "Error",
                              parent=pop); return "break"
            if len(e2.get()) < 4:
                MD.show_error("La nueva contraseña debe tener al menos 4 caracteres.",
                              "Error", parent=pop); return "break"
            if e2.get() != e3.get():
                MD.show_error("Las contraseñas nuevas no coinciden.", "Error",
                              parent=pop); return "break"
            self.db_manager.set_setting("startup_password", e2.get())
            MD.show_info("Contraseña cambiada.", "Listo", parent=pop)
            pop.destroy(); return "break"

        ttk.Button(pop, text="Guardar", command=aplicar,
                   style="DarkGreen.TButton").pack(pady=12)
        for e in (e1, e2, e3):
            e.bind("<Return>", aplicar)
        show_popup_smooth(pop)
        try:
            pop.grab_set(); pop.focus_force()
        except Exception:
            pass
        pop.after(50, lambda: e1.focus_set() if pop.winfo_exists() else None)

    # ============================================================
    # TAMAÑO DE FUENTE
    # ============================================================
    def _apply_font_size(self):
        size = int(self.db_manager.get_setting("font_size", "11") or 11)
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

    # ============================================================
    # UI
    # ============================================================
    def create_widgets(self):
        top_bar = ttk.Frame(self, bootstyle="dark")
        top_bar.pack(fill="x", side="top")

        menubar_wrap = ttk.Frame(top_bar, bootstyle="dark")
        menubar_wrap.pack(side="left", fill="y")
        self.menubar = DarkMenuBar(menubar_wrap,
                                    lambda: self.current_theme == 'darkly')
        self.menubar.pack(side="left")

        try:
            bg = self.style.colors.bg
        except Exception:
            bg = "#1a1a1a"
        right_wrap = tk.Frame(top_bar, bg=bg)
        right_wrap.pack(side="right", padx=(0, 15))
        self.business_header = make_inline_business_header(
            right_wrap, self.db_manager, bg=bg)
        self.business_header["frame"].pack(side="right", pady=6)

        # ---------- MENÚ OPCIONES ----------
        def build_opciones(menu):
            menu.add_command(label="⚙️ Ajustes...",
                             command=self.open_settings_view)
            menu.add_separator()
            menu.add_command(label="🌓 Cambiar Tema", command=self.toggle_theme)
            menu.add_command(label="🏪 Datos del negocio",
                             command=self.open_settings_view)
            menu.add_separator()
            menu.add_command(label="📈 Margen de ganancia por defecto",
                             command=self._configure_default_margin)
            menu.add_command(label="⚠️ Alerta de stock bajo",
                             command=self._configure_low_stock)
            menu.add_command(label="💾 Respaldo automático",
                             command=self._configure_backup)
            menu.add_separator()
            menu.add_command(label="📜 Exportar Historial de Precios",
                             command=self.export_price_history)
            menu.add_command(label="📦 Exportar Inventario a Excel",
                             command=self.export_inventory_excel)
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
            sub_pwd.add_command(label="🔐 Cambiar contraseña",
                                command=self._change_password)
            menu.add_cascade(label="🔑 Contraseña", menu=sub_pwd)

            menu.add_separator()
            self.tray_var = tk.BooleanVar(
                value=self.db_manager.get_setting("close_to_tray", "0") == "1")
            menu.add_checkbutton(
                label="🔽 Al presionar X ocultar en la bandeja",
                variable=self.tray_var,
                command=self._toggle_close_to_tray)

            menu.add_separator()
            menu.add_command(label="📄 Reporte del Día (TXT)",
                             command=self.generate_daily_report)
            menu.add_command(label="📊 Reporte del Mes (Excel)",
                             command=self.generate_monthly_report)
            menu.add_separator()
            menu.add_command(label="📤 Exportar Base de Datos",
                             command=self.export_db)
            menu.add_command(label="📥 Importar Base de Datos",
                             command=self.import_db)

        # ---------- MENÚ VENTAS ----------
        def build_ventas(menu):
            menu.add_command(label="📊 Resumen de Ventas (agrupado)",
                             command=self.show_sales_summary)
            menu.add_command(label="💳 Fiados (agrupado por cliente)",
                             command=self.show_credit_sales)
            menu.add_separator()
            menu.add_command(label="↩️ Devoluciones / Notas crédito",
                             command=self.open_returns_window)
            menu.add_separator()
            menu.add_command(label="💰 Cierre de Caja del día",
                             command=self.show_cash_closing)
            menu.add_command(label="💵 Movimiento de Caja (retiro/gasto)",
                             command=self._open_cash_movement)
            menu.add_separator()
            menu.add_command(label="📊 Gráficos y estadísticas",
                             command=self.open_charts)

        # ---------- MENÚ INVENTARIO ----------
        def build_inventario(menu):
            menu.add_command(label="📦 Ver inventario",
                             command=lambda: self.show_page("inventario"))
            menu.add_separator()
            menu.add_command(label="🖨️ Generar etiquetas PDF",
                             command=self._open_labels_from_menu)
            menu.add_command(label="🔔 Alertas de vencimiento",
                             command=self._open_expiry_alerts_from_menu)
            menu.add_command(label="💰 Historial de precios global",
                             command=self._open_price_history_from_menu)

        self.menubar.add_menu("Opciones", build_opciones)
        self.menubar.add_menu("Ventas", build_ventas)
        self.menubar.add_menu("Inventario", build_inventario)

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

        self.payment_view = PaymentView(
            self.container, self.product_use_case, self.sale_use_case,
            self.db_manager, lambda: self.current_theme,
            on_business_click=None)
        self.inventory_view = InventoryView(
            self.container, self.product_use_case,
            self.db_manager, lambda: self.current_theme,
            on_business_click=None)
        # Compartir sale_case con inventory_view (para devoluciones y gráficos)
        self.inventory_view._sale_case = self.sale_use_case

        self.current_page = None

    # ============================================================
    # ACCIONES DE MENÚ
    # ============================================================
    def open_settings_view(self):
        from presentation.views.settings_view import SettingsView
        SettingsView(self, self.db_manager, self.product_use_case,
                     self.sale_use_case,
                     on_theme_change=self._on_theme_change,
                     on_font_change=self._on_font_change,
                     on_business_change=self._on_business_change,
                     on_change_password=self._change_password)

    def _on_theme_change(self, theme):
        self.current_theme = theme
        try:
            self.style.theme_use(theme)
        except Exception:
            pass
        self.configure(bg=self.style.colors.bg)
        self._setup_dark_green_style()
        apply_titlebar_theme(self, theme == 'darkly')

    def _on_font_change(self, size):
        try:
            self._change_font_size(0)
        except Exception:
            pass

    def _on_business_change(self):
        self._update_window_title()
        self._refresh_business_header()

    def _open_labels_from_menu(self):
        try:
            self.inventory_view.print_labels()
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    def _open_expiry_alerts_from_menu(self):
        try:
            self.inventory_view.open_expiry_alerts()
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    def _open_price_history_from_menu(self):
        try:
            self.inventory_view.open_price_history_global()
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    def open_returns_window(self):
        from presentation.views.widgets import ReturnsWindow
        ReturnsWindow(self, self.sale_use_case,
                      on_done=self._refresh_all_views)

    def open_charts(self):
        from presentation.views.widgets import ChartsWindow
        ChartsWindow(self, self.sale_use_case)

    def _refresh_all_views(self):
        try:
            self.inventory_view.load_products()
        except Exception:
            pass
        try:
            self.payment_view._load_recent_sales()
        except Exception:
            pass
        try:
            self.refresh_summary() if hasattr(self, "refresh_summary") else None
        except Exception:
            pass

    def _toggle_close_to_tray(self):
        val = "1" if self.tray_var.get() else "0"
        self.db_manager.set_setting("close_to_tray", val)
        if val == "1":
            MD.show_info("✅ Modo bandeja activado.", "Modo bandeja", parent=self)
        else:
            MD.show_info("ℹ️ Modo normal activado.", "Modo normal", parent=self)

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
        try:
            bg = self.style.colors.bg
            if hasattr(self, "business_header") and self.business_header:
                frm = self.business_header["frame"]
                frm.configure(bg=bg)
                for child in frm.winfo_children():
                    try:
                        child.configure(bg=bg)
                    except Exception:
                        pass
        except Exception:
            pass

    # ============================================================
    # CONFIGURACIONES SIMPLES
    # ============================================================
    def _configure_default_margin(self):
        actual = self.db_manager.get_setting("default_margin", "20") or "20"
        pop = tk.Toplevel(self)
        pop.title("📈 Margen por defecto")
        pop.geometry("400x260")
        pop.transient(self)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg; fg = self.style.colors.fg
        tk.Label(pop, text="📈 Margen por defecto", font=("Arial", 13, "bold"),
                 bg=bg, fg=fg).pack(pady=(15, 4))
        tk.Label(pop, text="Se usa al crear productos nuevos.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))
        tk.Label(pop, text="% Ganancia:", bg=bg, fg=fg).pack()
        v = tk.StringVar(value=actual)
        e = ttk.Entry(pop, textvariable=v, width=15,
                      font=("Arial", 14), justify="center")
        e.pack(pady=8); e.select_range(0, tk.END)

        def guardar(ev=None):
            try:
                val = float(v.get().replace(",", ".").strip() or "0")
                if val < 0: val = 0
            except ValueError:
                MD.show_error("Valor inválido", "Error", parent=pop); return "break"
            self.db_manager.set_setting("default_margin", str(val))
            pop.destroy()
            MD.show_info(f"✅ Margen: {val:g}%", "Listo", parent=self)
            return "break"
        ttk.Button(pop, text="Guardar", command=guardar,
                   style="DarkGreen.TButton").pack(pady=12)
        e.bind("<Return>", guardar)
        show_popup_smooth(pop)
        pop.after(80, e.focus_set)

    def _configure_low_stock(self):
        actual = self.db_manager.get_setting("low_stock_threshold", "5") or "5"
        pop = tk.Toplevel(self)
        pop.title("⚠️ Alerta de stock bajo")
        pop.geometry("400x260")
        pop.transient(self)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg; fg = self.style.colors.fg
        tk.Label(pop, text="⚠️ Alerta de stock bajo",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(15, 4))
        tk.Label(pop, text="Productos con stock ≤ este valor se marcan en rojo.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))
        tk.Label(pop, text="Unidades mínimas:", bg=bg, fg=fg).pack()
        v = tk.StringVar(value=actual)
        e = ttk.Entry(pop, textvariable=v, width=15,
                      font=("Arial", 14), justify="center")
        e.pack(pady=8); e.select_range(0, tk.END)

        def guardar(ev=None):
            try:
                val = int(float(v.get().strip() or "0"))
                if val < 0: val = 0
            except ValueError:
                MD.show_error("Valor inválido", "Error", parent=pop); return "break"
            self.db_manager.set_setting("low_stock_threshold", str(val))
            pop.destroy()
            try: self.inventory_view.load_products()
            except Exception: pass
            MD.show_info(f"✅ Alerta: stock ≤ {val}", "Listo", parent=self)
            return "break"
        ttk.Button(pop, text="Guardar", command=guardar,
                   style="DarkGreen.TButton").pack(pady=12)
        e.bind("<Return>", guardar)
        show_popup_smooth(pop)
        pop.after(80, e.focus_set)

    def _configure_backup(self):
        habilitado = self._is_auto_backup_enabled()
        pop = tk.Toplevel(self)
        pop.title("💾 Respaldo automático")
        pop.geometry("560x400")
        pop.transient(self)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg; fg = self.style.colors.fg
        tk.Label(pop, text="💾 Respaldo automático diario",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(15, 4))
        tk.Label(pop, text="Copia de la BD cada día.", font=("Arial", 9, "italic"),
                 bg=bg, fg="#a8e6a8").pack(pady=(0, 10))
        var_enabled = tk.BooleanVar(value=habilitado)
        ttk.Checkbutton(pop, text="✅ Activar",
                        variable=var_enabled,
                        bootstyle="success-round-toggle").pack(pady=8)
        tk.Label(pop, text="Carpeta de respaldos:", bg=bg, fg=fg).pack()
        carpeta_var = tk.StringVar(value=self._get_backup_folder())
        entry_frame = tk.Frame(pop, bg=bg)
        entry_frame.pack(pady=4, fill="x", padx=20)
        ttk.Entry(entry_frame, textvariable=carpeta_var, width=45).pack(
            side="left", fill="x", expand=True)

        def elegir_carpeta():
            folder = filedialog.askdirectory(initialdir=carpeta_var.get() or self.base_dir,
                                             parent=pop)
            if folder: carpeta_var.set(folder)
        ttk.Button(entry_frame, text="📁", command=elegir_carpeta,
                   bootstyle="info", width=3).pack(side="left", padx=4)

        def guardar():
            self.db_manager.set_setting("auto_backup_enabled",
                                        "1" if var_enabled.get() else "0")
            self.db_manager.set_setting("backup_folder", carpeta_var.get().strip())
            pop.destroy()
            MD.show_info("✅ Configuración guardada.", "Listo", parent=self)

        def respaldar_ahora():
            folder = carpeta_var.get().strip()
            try:
                os.makedirs(folder, exist_ok=True)
                hoy = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                destino = os.path.join(folder, f"ventas_manual_{hoy}.db")
                self.db_manager.close_connection()
                shutil.copy2(self.db_path, destino)
                self.db_manager.get_connection()
                MD.show_info(f"✅ Respaldo:\n{destino}", "Listo", parent=pop)
            except Exception as e:
                MD.show_error(f"Error: {e}", "Error", parent=pop)

        bf = tk.Frame(pop, bg=bg)
        bf.pack(side="bottom", pady=15)
        ttk.Button(bf, text="💾 Guardar", command=guardar,
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="📥 Respaldar ahora",
                   command=respaldar_ahora, bootstyle="info").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar", command=pop.destroy).pack(side="left", padx=5)
        show_popup_smooth(pop)

    # ============================================================
    # EXPORTACIONES
    # ============================================================
    def export_inventory_excel(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
        except ImportError:
            MD.show_error("Falta openpyxl.", "Error", parent=self)
            return
        hoy = datetime.now().strftime("%Y-%m-%d")
        arch = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=f"inventario_{hoy}.xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not arch: return
        try:
            products = self.product_use_case.list_products()
        except Exception:
            products = []
        if not products:
            MD.show_info("No hay productos.", "Sin datos", parent=self); return
        wb = openpyxl.Workbook()
        ws = wb.active; ws.title = "Inventario"
        headers = ["ID", "Nombre", "Grupo", "Código", "Costo", "% Gan.",
                   "Precio real", "Precio redondeado", "Stock",
                   "Vence", "Estado", "Valor costo", "Valor venta"]
        ws.append(headers)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="305496")
            c.alignment = Alignment(horizontal="center")
        total_costo = 0.0; total_venta = 0.0
        for p in products:
            valor_costo = (getattr(p, "cost", 0) or 0) * (p.stock or 0)
            valor_venta = (getattr(p, "rounded_price", 0) or p.price or 0) * (p.stock or 0)
            total_costo += valor_costo; total_venta += valor_venta
            estado = "Activo"
            if getattr(p, "paused", 0):
                estado = "Pausado"
            elif getattr(p, "expiry_date", ""):
                try:
                    fecha = datetime.strptime(p.expiry_date, "%Y-%m-%d").date()
                    dias = (fecha - datetime.now().date()).days
                    if dias < 0: estado = f"Vencido ({abs(dias)}d)"
                    elif dias <= 7: estado = f"Vence en {dias}d"
                except Exception:
                    pass
            ws.append([
                p.product_id, p.name, getattr(p, "group_name", "") or "-",
                p.barcode or "-",
                getattr(p, "cost", 0) or 0,
                getattr(p, "margin_percent", 20) or 20,
                p.price or 0,
                getattr(p, "rounded_price", 0) or p.price or 0,
                p.stock or 0,
                getattr(p, "expiry_date", "") or "-",
                estado, valor_costo, valor_venta])
        ws.append([])
        ws.append(["", "", "", "", "", "", "", "", "", "", "TOTALES:",
                   total_costo, total_venta])
        for c in ws[ws.max_row]: c.font = Font(bold=True)
        for col, w in zip("ABCDEFGHIJKLM",
                          [8, 30, 15, 18, 10, 8, 12, 14, 10, 12, 15, 14, 14]):
            ws.column_dimensions[col].width = w
        try:
            wb.save(arch)
            MD.show_info(f"✅ Exportado:\n{arch}", "Éxito", parent=self)
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    def export_price_history(self):
        try:
            data = self.product_use_case.get_all_price_history()
        except Exception:
            data = []
        if not data:
            MD.show_info("No hay historial.", "Sin datos", parent=self); return
        hoy = datetime.now().strftime("%Y-%m-%d")
        arch = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"historial_precios_{hoy}.txt",
            filetypes=[("Texto", "*.txt")])
        if not arch: return
        try:
            with open(arch, "w", encoding="utf-8") as f:
                f.write("HISTORIAL DE PRECIOS\n" + "=" * 100 + "\n")
                f.write(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                f.write(f"Registros: {len(data)}\n" + "=" * 100 + "\n\n")
                for r in data:
                    f.write(f"[{r['date']}] {r['product_name']} ({r['product_barcode']})\n")
                    f.write(f"   Real: ${r['old_price']:,.0f} → ${r['new_price']:,.0f}\n")
                    f.write(f"   Redondeado: ${r.get('old_rounded_price',0):,.0f} → "
                            f"${r.get('new_rounded_price',0):,.0f}\n\n")
            MD.show_info(f"Guardado:\n{arch}", "Listo", parent=self)
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    # ============================================================
    # CAJA
    # ============================================================
    def _open_cash_movement(self):
        pop = tk.Toplevel(self)
        pop.title("💵 Movimiento de Caja")
        pop.geometry("420x360")
        pop.transient(self)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg; fg = self.style.colors.fg
        tk.Label(pop, text="💵 Movimiento de Caja",
                 font=("Arial", 14, "bold"), bg=bg, fg=fg).pack(pady=(15, 4))
        tk.Label(pop, text="Registra retiros, gastos o ingresos.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))
        tk.Label(pop, text="Tipo:", bg=bg, fg=fg).pack()
        tipo_var = tk.StringVar(value="retiro")
        tf = tk.Frame(pop, bg=bg); tf.pack(pady=5)
        for val, txt in [("retiro", "Retiro"), ("gasto", "Gasto"),
                         ("ingreso", "Ingreso")]:
            ttk.Radiobutton(tf, text=txt, variable=tipo_var, value=val,
                            bootstyle="info").pack(side="left", padx=6)
        tk.Label(pop, text="Monto:", bg=bg, fg=fg).pack(pady=(10, 3))
        monto_var = tk.StringVar()
        e = ttk.Entry(pop, textvariable=monto_var, width=20,
                      font=("Arial", 14), justify="center")
        e.pack(pady=5)
        tk.Label(pop, text="Notas (opcional):", bg=bg, fg=fg).pack(pady=(10, 3))
        notas_var = tk.StringVar()
        ttk.Entry(pop, textvariable=notas_var, width=40).pack(pady=5)

        def guardar():
            try:
                monto = float(monto_var.get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                if monto <= 0: raise ValueError
            except ValueError:
                MD.show_error("Monto inválido", "Error", parent=pop); return
            try:
                self.sale_use_case.register_cash_movement(
                    tipo_var.get(), monto, notas_var.get().strip())
                pop.destroy()
                MD.show_info(f"✅ {tipo_var.get().capitalize()} de "
                             f"${monto:,.0f} registrado.".replace(",", "."),
                             "Listo", parent=self)
            except Exception as ex:
                MD.show_error(f"Error: {ex}", "Error", parent=pop)

        e.bind("<Return>", lambda ev: guardar())
        bf = tk.Frame(pop, bg=bg); bf.pack(pady=15)
        ttk.Button(bf, text="💾 Guardar", command=guardar,
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar", command=pop.destroy).pack(side="left", padx=5)
        show_popup_smooth(pop)
        pop.after(80, e.focus_set)

    def show_cash_closing(self):
        win = tk.Toplevel(self)
        win.title("💰 Cierre de Caja")
        win.geometry("760x820")
        win.transient(self)
        win.configure(bg=self.style.colors.bg)
        win.withdraw()
        bg = self.style.colors.bg; fg = self.style.colors.fg
        fecha_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        resumen_lbl = tk.Label(win, text="", font=("Arial", 11), bg=bg, fg=fg,
                               justify="left", anchor="w", wraplength=680)

        def generar_reporte():
            fecha = fecha_var.get().strip()
            try:
                datetime.strptime(fecha, "%Y-%m-%d")
            except Exception:
                MD.show_error("Fecha inválida.", "Error", parent=win); return
            data = self.sale_use_case.get_cash_closing(fecha)
            lineas = [
                f"📅 CIERRE DE CAJA — {data['date']}",
                f"🕛 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", "",
                "─── RESUMEN DE VENTAS ───",
                f"🧾 Ventas: {data['cantidad_ventas']}",
                f"📦 Productos: {data['productos_vendidos']:g}",
                f"💵 Subtotal: ${data['total_subtotal']:,.0f}".replace(",", "."),
                f"🎁 Descuentos: -${data['total_descuento']:,.0f}".replace(",", "."),
                f"💰 TOTAL: ${data['total_ventas']:,.0f}".replace(",", "."),
                "", "─── MÉTODOS ───",
            ]
            for m in ("Efectivo", "Transferencia", "Tarjeta", "Otro", "Fiado"):
                info = data["metodos"].get(m)
                if info:
                    lineas.append(f"  • {m:<14} {info['count']:>3}  "
                                  f"${info['total']:>12,.0f}".replace(",", "."))
            lineas += [
                "", "─── MOVIMIENTOS ───",
                f"💵 Inicial: ${data.get('initial_cash', 0):,.0f}".replace(",", "."),
                f"💰 Efectivo ventas: ${data['metodos'].get('Efectivo', {}).get('total', 0):,.0f}".replace(",", "."),
                f"➕ Ingresos: ${data.get('ingresos', 0):,.0f}".replace(",", "."),
                f"➖ Retiros: -${data.get('retiros', 0):,.0f}".replace(",", "."),
                f"➖ Gastos: -${data.get('gastos', 0):,.0f}".replace(",", "."),
                f"↩️ Devoluciones: -${data.get('total_devuelto', 0):,.0f}".replace(",", "."),
                "", "════════════════════════",
                f"💰 ESPERADO: ${data['efectivo_esperado']:,.0f}".replace(",", "."),
                "════════════════════════",
            ]
            if data.get("counted_cash", 0) > 0:
                diff = data.get("difference", 0)
                signo = "+" if diff > 0 else ""
                estado = "SOBRANTE" if diff > 0 else ("FALTANTE" if diff < 0 else "CUADRA")
                lineas += [
                    f"💵 Contado: ${data['counted_cash']:,.0f}".replace(",", "."),
                    f"📊 Diferencia: {signo}${diff:,.0f} ({estado})".replace(",", ".")]
            else:
                lineas += ["💵 Contado: (sin registrar)",
                           "👉 Usa 'Contar efectivo' para cuadrar"]
            resumen_lbl.configure(text="\n".join(lineas))

        def contar_efectivo():
            session = self.sale_use_case.get_or_create_today_cash_session()
            summary = self.sale_use_case.get_cash_session_summary(
                session_id=session["session_id"]) if session else None
            expected = summary["expected_cash"] if summary else 0.0
            pop = tk.Toplevel(win)
            pop.title("💵 Contar efectivo")
            pop.geometry("440x360")
            pop.transient(win)
            pop.configure(bg=bg)
            pop.withdraw()
            tk.Label(pop, text="💵 CONTAR EFECTIVO",
                     font=("Arial", 14, "bold"), bg=bg, fg=fg).pack(pady=(15, 6))
            tk.Label(pop, text=f"Esperado: ${expected:,.0f}".replace(",", "."),
                     font=("Arial", 13, "bold"), bg="#0a4d1f", fg="#a8e6a8",
                     padx=12, pady=8).pack(pady=8)
            tk.Label(pop, text="¿Cuánto efectivo hay?", bg=bg, fg=fg).pack(pady=(10, 4))
            contado_var = tk.StringVar()
            e = ttk.Entry(pop, textvariable=contado_var, width=20,
                          font=("Arial", 16), justify="center")
            e.pack(pady=5); e.focus_set()
            diff_lbl = tk.Label(pop, text="", font=("Arial", 12, "bold"),
                                bg=bg, fg=fg)
            diff_lbl.pack(pady=8)

            def actualizar_diff(*args):
                try:
                    valor = float(contado_var.get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                except ValueError:
                    valor = 0.0
                diff = valor - expected
                if diff > 0:
                    diff_lbl.configure(text=f"📈 SOBRANTE: ${diff:,.0f}".replace(",", "."),
                                       fg="#7dd87d")
                elif diff < 0:
                    diff_lbl.configure(text=f"📉 FALTANTE: ${abs(diff):,.0f}".replace(",", "."),
                                       fg="#ff8888")
                else:
                    diff_lbl.configure(text="✅ CUADRA", fg="#7dd87d")
            contado_var.trace_add("write", actualizar_diff)
            tk.Label(pop, text="Notas:", bg=bg, fg=fg).pack(pady=(8, 3))
            notas_var = tk.StringVar()
            ttk.Entry(pop, textvariable=notas_var, width=40).pack(pady=4)

            def guardar():
                try:
                    valor = float(contado_var.get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                except ValueError:
                    MD.show_error("Valor inválido", "Error", parent=pop); return
                try:
                    self.sale_use_case.update_counted_cash(
                        session["session_id"], valor, notas_var.get().strip())
                    pop.destroy(); generar_reporte()
                    MD.show_info("✅ Efectivo registrado.", "Listo", parent=win)
                except Exception as ex:
                    MD.show_error(f"Error: {ex}", "Error", parent=pop)

            bf = tk.Frame(pop, bg=bg); bf.pack(pady=15)
            ttk.Button(bf, text="💾 Guardar", command=guardar,
                       style="DarkGreen.TButton").pack(side="left", padx=5)
            ttk.Button(bf, text="Cancelar", command=pop.destroy).pack(side="left", padx=5)
            show_popup_smooth(pop)

        def exportar_txt():
            fecha = fecha_var.get().strip()
            arch = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=f"cierre_caja_{fecha}.txt",
                filetypes=[("Texto", "*.txt")], parent=win)
            if not arch: return
            try:
                with open(arch, "w", encoding="utf-8") as f:
                    f.write(resumen_lbl.cget("text"))
                MD.show_info(f"Guardado:\n{arch}", "Listo", parent=win)
            except Exception as e:
                MD.show_error(f"Error: {e}", "Error", parent=win)

        container = tk.Frame(win, bg=bg)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        def build_content(parent):
            tk.Label(parent, text="💰 CIERRE DE CAJA",
                     font=("Arial", 18, "bold"), bg=bg, fg=fg).pack(pady=(10, 6))
            row = tk.Frame(parent, bg=bg); row.pack(pady=6)
            tk.Label(row, text="Fecha:", bg=bg, fg=fg).pack(side="left", padx=5)
            ttk.Entry(row, textvariable=fecha_var, width=15,
                      justify="center").pack(side="left", padx=5)
            ttk.Button(row, text="🔍 Generar", command=generar_reporte,
                       style="DarkGreen.TButton").pack(side="left", padx=8)
            resumen_lbl.pack(fill="both", expand=True, padx=10, pady=10)

        def build_bottom(parent):
            ttk.Button(parent, text="💵 Contar efectivo",
                       command=contar_efectivo,
                       style="DarkGreen.TButton").pack(side="left", padx=6)
            ttk.Button(parent, text="📄 Exportar TXT",
                       command=exportar_txt,
                       bootstyle="info").pack(side="left", padx=6)
            ttk.Button(parent, text="Cerrar",
                       command=win.destroy).pack(side="right", padx=6)

        make_scrollable(container, build_content, build_bottom, bg=bg)
        generar_reporte()
        show_popup_smooth(win)
        try:
            win.grab_set(); win.focus_force()
        except Exception:
            pass

    # ============================================================
    # RESUMEN DE VENTAS (simplificado, pero completo)
    # ============================================================
    def show_sales_summary(self):
        from presentation.views.widgets import make_scrollable as _ms
        win = tk.Toplevel(self)
        win.title("Resumen de Ventas")
        win.geometry("1200x780")
        win.transient(self)
        win.configure(bg=self.style.colors.bg)
        win.withdraw()
        bg = self.style.colors.bg; fg = self.style.colors.fg
        container = tk.Frame(win, bg=bg)
        container.pack(fill="both", expand=True)
        grupos_map = {}
        marcados = set()
        refs = {}

        def build_content(parent):
            tk.Label(parent, text="📊 RESUMEN DE VENTAS",
                     font=("Arial", 18, "bold"), bg=bg, fg=fg).pack(pady=(12, 6))
            filtro_var = tk.StringVar(value="today")
            refs["filtro_var"] = filtro_var
            ff = tk.Frame(parent, bg=bg); ff.pack(pady=4)
            for val, txt in [("today", "Hoy"), ("month", "Este mes"), ("all", "Todas")]:
                ttk.Radiobutton(ff, text=txt, variable=filtro_var, value=val,
                                bootstyle="info",
                                command=lambda: recargar()).pack(side="left", padx=8)
            tf, tree = make_scrolled_treeview(
                parent,
                columns=("Cliente", "Ventas", "Total", "Pagado", "Pendiente"),
                headings=[
                    ("Cliente", "Cliente", 260, "w"),
                    ("Ventas", "# Ventas", 90, "center"),
                    ("Total", "Total", 140, "center"),
                    ("Pagado", "Pagado", 140, "center"),
                    ("Pendiente", "Pendiente", 140, "center"),
                ],
                bootstyle="dark")
            tf.pack(fill="both", expand=True, padx=15, pady=8)
            refs["tree"] = tree

        def recargar():
            tree = refs.get("tree")
            if not tree: return
            for r in tree.get_children():
                tree.delete(r)
            grupos_map.clear()
            f = refs["filtro_var"].get()
            if f == "today":
                sales = self.sale_use_case.get_sales_by_day(
                    datetime.now().strftime("%Y-%m-%d"))
            elif f == "month":
                sales = self.sale_use_case.get_sales_by_month(
                    datetime.now().strftime("%Y-%m"))
            else:
                sales = self.sale_use_case.get_all_sales(limit=1000)
            for g in self.sale_use_case.group_sales_by_customer(sales):
                iid = tree.insert("", "end", values=(
                    g["customer_name"], g["count"],
                    f"${g['total']:,.0f}".replace(",", "."),
                    f"${g['paid']:,.0f}".replace(",", "."),
                    f"${g['pending']:,.0f}".replace(",", ".")))
                grupos_map[iid] = g

        def build_bottom(parent):
            ttk.Button(parent, text="🔄 Refrescar",
                       command=recargar,
                       bootstyle="secondary").pack(side="left", padx=6)
            ttk.Button(parent, text="Cerrar",
                       command=win.destroy).pack(side="right", padx=6)

        make_scrollable(container, build_content, build_bottom, bg=bg)
        recargar()
        show_popup_smooth(win)
        try:
            win.grab_set(); win.focus_force()
        except Exception:
            pass

    # ============================================================
    # FIADOS (versión simplificada)
    # ============================================================
    def show_credit_sales(self):
        win = tk.Toplevel(self)
        win.title("Fiados - Cuentas por cobrar")
        win.geometry("1150x720")
        win.transient(self)
        win.configure(bg=self.style.colors.bg)
        win.withdraw()
        bg = self.style.colors.bg; fg = self.style.colors.fg
        container = tk.Frame(win, bg=bg)
        container.pack(fill="both", expand=True)
        grupos_map = {}
        refs = {}

        def build_content(parent):
            tk.Label(parent, text="💳 CUENTAS POR COBRAR",
                     font=("Arial", 18, "bold"), bg=bg, fg=fg).pack(pady=(12, 6))
            lbl = tk.Label(parent, text="", font=("Arial", 12, "bold"),
                           bg=bg, fg=fg)
            lbl.pack(pady=4)
            refs["resumen"] = lbl
            tf, tree = make_scrolled_treeview(
                parent,
                columns=("Cliente", "Fiados", "Total", "Abonado", "Pendiente"),
                headings=[
                    ("Cliente", "Cliente", 260, "w"),
                    ("Fiados", "# Fiados", 90, "center"),
                    ("Total", "Total", 130, "center"),
                    ("Abonado", "Abonado", 130, "center"),
                    ("Pendiente", "Pendiente", 140, "center"),
                ],
                bootstyle="dark")
            tf.pack(fill="both", expand=True, padx=15, pady=8)
            refs["tree"] = tree
            tree.bind("<Double-1>", lambda e: abonar())

        def recargar():
            tree = refs.get("tree")
            if not tree: return
            for r in tree.get_children():
                tree.delete(r)
            grupos_map.clear()
            ventas = self.sale_use_case.get_credit_sales(only_unpaid=True)
            ventas = [v for v in ventas if v.pending() > 0.01]
            grupos = self.sale_use_case.group_sales_by_customer(ventas)
            total_global = 0.0
            for g in grupos:
                total_global += g["pending"]
                iid = tree.insert("", "end", values=(
                    g["customer_name"], g["count"],
                    f"${g['total']:,.0f}".replace(",", "."),
                    f"${g['paid']:,.0f}".replace(",", "."),
                    f"${g['pending']:,.0f}".replace(",", ".")))
                grupos_map[iid] = g
            try:
                refs["resumen"].configure(
                    text=f"👥 {len(grupos)} clientes | Total: "
                         f"${total_global:,.0f}".replace(",", "."))
            except Exception:
                pass

        def abonar():
            tree = refs.get("tree")
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona un cliente.", "Sin selección",
                                parent=win); return
            g = grupos_map.get(sel[0])
            if not g: return
            pendientes = [v for v in g["sales"] if v.pending() > 0.01]
            if not pendientes:
                MD.show_info("Sin deudas pendientes.", "Listo", parent=win); return
            venta = sorted(pendientes, key=lambda x: x.sale_id)[0]
            self._abonar_dialog(win, venta, venta.pending(), recargar)

        def build_bottom(parent):
            ttk.Button(parent, text="💵 Abonar",
                       command=abonar,
                       style="DarkGreen.TButton").pack(side="left", padx=6)
            ttk.Button(parent, text="🔄 Refrescar",
                       command=recargar,
                       bootstyle="secondary").pack(side="left", padx=6)
            ttk.Button(parent, text="Cerrar",
                       command=win.destroy).pack(side="right", padx=6)

        make_scrollable(container, build_content, build_bottom, bg=bg)
        recargar()
        show_popup_smooth(win)
        try:
            win.grab_set(); win.focus_force()
        except Exception:
            pass

    def _abonar_dialog(self, parent, venta, pendiente, on_done):
        pop = tk.Toplevel(parent)
        pop.title(f"Abonar a venta #{venta.display_number:02d}")
        pop.geometry("440x480")
        pop.transient(parent)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg; fg = self.style.colors.fg

        tk.Label(pop, text="💵 Registrar Abono",
                 font=("Arial", 16, "bold"), bg=bg, fg=fg).pack(pady=(15, 6))
        cliente = venta.customer_name or "(sin nombre)"
        tk.Label(pop, text=f"Cliente: {cliente}", bg=bg, fg=fg).pack(pady=4)
        tk.Label(pop, text=f"Venta #{venta.display_number:02d}",
                 bg=bg, fg="#a8e6a8", font=("Arial", 11, "italic")).pack(pady=2)
        tk.Label(pop, text=f"Total: ${venta.total:,.0f}".replace(",", "."),
                 bg=bg, fg=fg).pack(pady=3)
        tk.Label(pop, text=f"Pendiente: ${pendiente:,.0f}".replace(",", "."),
                 font=("Arial", 14, "bold"), bg="#0a4d1f", fg="#a8e6a8",
                 padx=10, pady=8).pack(pady=10)

        tk.Label(pop, text="Método:", bg=bg, fg=fg).pack(pady=(8, 3))
        metodo_var = tk.StringVar(value="Efectivo")
        mf = tk.Frame(pop, bg=bg); mf.pack(pady=3)
        for m in ["Efectivo", "Transferencia", "Tarjeta", "Otro"]:
            ttk.Radiobutton(mf, text=m, variable=metodo_var, value=m,
                            bootstyle="info").pack(side="left", padx=4)

        tk.Label(pop, text="Monto:", bg=bg, fg=fg).pack(pady=(10, 3))
        monto_var = tk.StringVar()
        e = ttk.Entry(pop, textvariable=monto_var, width=20,
                      font=("Arial", 16), justify="center")
        e.pack(pady=5)

        def aplicar(ev=None):
            try:
                monto = float(monto_var.get().replace("$", "").replace(".", "").replace(",", "."))
                if monto <= 0: raise ValueError
            except ValueError:
                MD.show_error("Monto inválido", "Error", parent=pop); return "break"
            if monto > pendiente + 0.01:
                if MD.yesno(f"El monto supera el pendiente.\n"
                            f"¿Registrar solo ${pendiente:,.0f}?".replace(",", "."),
                            "Confirmar", parent=pop) != "Yes":
                    return "break"
                monto = pendiente
            self.sale_use_case.add_payment(
                venta.sale_id, monto,
                method=metodo_var.get(),
                customer_name=venta.customer_name or "")
            pop.destroy()
            MD.show_info(f"✅ Abono de ${monto:,.0f} registrado.".replace(",", "."),
                         "Listo", parent=parent)
            on_done()
            try:
                parent.lift(); parent.focus_force()
            except Exception:
                pass
            return "break"

        e.bind("<Return>", aplicar)
        bf = tk.Frame(pop, bg=bg); bf.pack(pady=15)
        ttk.Button(bf, text="Registrar", command=aplicar,
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar", command=pop.destroy).pack(side="left", padx=5)
        show_popup_smooth(pop)
        try:
            pop.grab_set(); pop.focus_force()
        except Exception:
            pass
        pop.after(50, lambda: e.focus_set() if pop.winfo_exists() else None)

    # ============================================================
    # REPORTES
    # ============================================================
    def generate_daily_report(self):
        hoy = datetime.now().strftime("%Y-%m-%d")
        sales = self.sale_use_case.get_sales_by_day(hoy)
        if not sales:
            MD.show_info("No hay ventas hoy.", "Vacío", parent=self); return
        arch = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"ventas_{hoy}.txt",
            filetypes=[("Texto", "*.txt")])
        if not arch: return
        total_dia = sum(s.total for s in sales)
        total_prod = sum(i.quantity for s in sales for i in s.items)
        L = ["=" * 60, "      REPORTE DE VENTAS DEL DÍA",
             f"      Fecha: {hoy}",
             f"      Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
             "=" * 60, ""]
        for s in sales:
            hora = s.date.split(" ")[1] if " " in s.date else ""
            cliente = f" - {s.customer_name}" if s.customer_name else ""
            fiado = " [FIADO]" if s.is_credit else ""
            L.append(f"Venta #{s.display_number:02d} - {hora} - "
                     f"{s.payment_method}{cliente}{fiado}")
            for it in s.items:
                L.append(f"  {it.quantity:>8g}  {it.product_name[:30]:<30} "
                         f"${it.unit_price:>9,.0f} ${it.subtotal:>11,.0f}"
                         .replace(",", "."))
            L.append(f"  {'':>8}  {'':<30} {'':>10} ${s.total:>11,.0f}"
                     .replace(",", "."))
            L.append("")
        L += ["=" * 60,
              f"TOTAL DEL DÍA: ${total_dia:>12,.0f}".replace(",", "."),
              f"VENTAS: {len(sales)}",
              f"PRODUCTOS: {total_prod:g}", "=" * 60]
        try:
            with open(arch, "w", encoding="utf-8") as f:
                f.write("\n".join(L))
            MD.show_info(f"Guardado:\n{arch}", "Listo", parent=self)
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    def generate_monthly_report(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
        except ImportError:
            MD.show_error("Falta openpyxl.", "Error", parent=self); return
        ym = datetime.now().strftime("%Y-%m")
        sales = self.sale_use_case.get_sales_by_month(ym)
        if not sales:
            MD.show_info("No hay ventas este mes.", "Vacío", parent=self); return
        arch = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=f"ventas_{ym}.xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not arch: return
        wb = openpyxl.Workbook(); ws = wb.active
        ws.title = f"Ventas {ym}"
        ws.append(["Venta #", "Fecha", "Cliente", "Método", "Fiado",
                   "Producto", "Código", "Cantidad", "P. Unit.", "Subtotal"])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="305496")
            c.alignment = Alignment(horizontal="center")
        for s in sales:
            for it in s.items:
                ws.append([f"#{s.display_number:02d}", s.date, s.customer_name,
                           s.payment_method, "Sí" if s.is_credit else "No",
                           it.product_name, it.barcode, it.quantity,
                           it.unit_price, it.subtotal])
        total = sum(s.total for s in sales)
        ws.append([]); ws.append(["", "", "", "", "", "", "", "", "TOTAL:", total])
        for col, w in zip("ABCDEFGHIJ", [10, 20, 25, 15, 8, 30, 20, 10, 12, 12]):
            ws.column_dimensions[col].width = w
        try:
            wb.save(arch)
            MD.show_info(f"Guardado:\n{arch}", "Listo", parent=self)
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    # ============================================================
    # EXPORTAR / IMPORTAR BD
    # ============================================================
    def export_db(self):
        arch = filedialog.asksaveasfilename(defaultextension=".db",
                                            filetypes=[("SQLite", "*.db")])
        if arch:
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, arch)
            MD.show_info("BD exportada.", "Listo", parent=self)

    def import_db(self):
        arch = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if arch and MD.yesno("¿Reemplazar datos?", "Confirmar",
                             parent=self) == "Yes":
            self.db_manager.close_connection()
            shutil.copy2(arch, self.db_path)
            self.inventory_view.load_products()
            MD.show_info("Importada.", "Listo", parent=self)