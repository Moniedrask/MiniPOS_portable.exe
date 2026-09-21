import tkinter as tk
from tkinter import filedialog, font as tkfont
import ttkbootstrap as ttk
from ttkbootstrap import Style
import os
import shutil
import sys
from datetime import datetime
from application.use_case.product_use_case import ProductCase
from application.use_case.sale_use_case import SaleCase
from infrastucture.db.db_manager import DBManager
from presentation.views.widgets import (
    apply_titlebar_theme, center_window, show_popup_smooth,
    get_menu_font, DarkMenuBar, MD
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
        self.title("MiniPOS Portable v2.0")
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

        if not self._check_startup_password():
            self.destroy()
            return

        self.create_widgets()
        self.show_page("pagos")
        self._apply_font_size()

        self.bind('<F2>', lambda e: self.inventory_view.add_product_popup()
                  if self.current_page == "inventario" else None)
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.after(200, lambda: apply_titlebar_theme(self, self.current_theme == 'darkly'))

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
        e.focus_set()
        resultado = {"ok": False}

        def verificar():
            if v.get() == pwd:
                resultado["ok"] = True
                pop.destroy()
            else:
                MD.show_error("Contraseña incorrecta", "Error", parent=pop)
                v.set("")

        ttk.Button(pop, text="Ingresar", command=verificar,
                   style="DarkGreen.TButton").pack(pady=10)
        e.bind("<Return>", lambda e: verificar())

        # ✅ Mostrar primero, luego grab
        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

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
        e1.focus_set()
        tk.Label(pop, text="Nueva contraseña:", bg=bg, fg=fg).pack()
        e2 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e2.pack(pady=5)
        tk.Label(pop, text="Confirmar nueva:", bg=bg, fg=fg).pack()
        e3 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e3.pack(pady=5)
        vaciar = tk.BooleanVar(value=False)
        ttk.Checkbutton(pop, text="Quitar contraseña (dejar vacío)",
                        variable=vaciar).pack(pady=8)

        def aplicar():
            if vaciar.get():
                self.db_manager.set_setting("startup_password", "")
                MD.show_info("Contraseña eliminada.", "Listo", parent=pop)
                pop.destroy()
                return
            if e1.get() != actual:
                MD.show_error("La contraseña actual no coincide.", "Error", parent=pop)
                return
            if len(e2.get()) < 4:
                MD.show_error("La nueva contraseña debe tener al menos 4 caracteres.",
                              "Error", parent=pop)
                return
            if e2.get() != e3.get():
                MD.show_error("Las contraseñas nuevas no coinciden.", "Error", parent=pop)
                return
            self.db_manager.set_setting("startup_password", e2.get())
            MD.show_info("Contraseña cambiada.", "Listo", parent=pop)
            pop.destroy()

        ttk.Button(pop, text="Guardar", command=aplicar,
                   style="DarkGreen.TButton").pack(pady=12)

        # ✅ Mostrar primero, luego grab
        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

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
        e1.focus_set()
        tk.Label(pop, text="Confirmar:", bg=bg, fg=fg).pack()
        e2 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e2.pack(pady=5)

        def guardar():
            if len(e1.get()) < 4:
                MD.show_error("Mínimo 4 caracteres.", "Error", parent=pop)
                return
            if e1.get() != e2.get():
                MD.show_error("No coinciden.", "Error", parent=pop)
                return
            self.db_manager.set_setting("startup_password", e1.get())
            MD.show_info("Contraseña activada. Se pedirá al iniciar.", "Listo", parent=pop)
            pop.destroy()

        ttk.Button(pop, text="Guardar", command=guardar,
                   style="DarkGreen.TButton").pack(pady=12)

        # ✅ Mostrar primero, luego grab
        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

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
            self.autostart_var = tk.BooleanVar(value=self._is_autostart_enabled())
            menu.add_checkbutton(label="🚀 Iniciar con Windows",
                                 variable=self.autostart_var,
                                 command=self.toggle_autostart)
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
        tabs.pack(fill="x", padx=10, pady=(10, 0))
        self.btn_pagos = ttk.Button(tabs, text="🛒  PAGOS", style="DarkGreen.TButton",
                                    command=lambda: self.show_page("pagos"), width=20)
        self.btn_pagos.pack(side="left", padx=3, pady=3, ipady=8)
        self.btn_inv = ttk.Button(tabs, text="📦  INVENTARIO", style="DarkGreen.TButton",
                                  command=lambda: self.show_page("inventario"), width=20)
        self.btn_inv.pack(side="left", padx=3, pady=3, ipady=8)

        self.bind('<Control-Key-1>', lambda e: self.show_page("pagos"))
        self.bind('<Control-Key-2>', lambda e: self.show_page("inventario"))

        self.container = ttk.Frame(self, bootstyle="dark")
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        self.payment_view = PaymentView(self.container, self.product_use_case,
                                        self.sale_use_case, lambda: self.current_theme)
        self.inventory_view = InventoryView(self.container, self.product_use_case,
                                            lambda: self.current_theme)
        self.current_page = None

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

    # =========== RESUMEN DE VENTAS ===========
    def show_sales_summary(self):
        win = tk.Toplevel(self)
        win.title("Resumen de Ventas")
        win.geometry("1150x720")
        win.transient(self)
        win.configure(bg=self.style.colors.bg)
        win.withdraw()
        bg = self.style.colors.bg
        fg = self.style.colors.fg

        tk.Label(win, text="📊 RESUMEN DE VENTAS (agrupado por cliente)",
                 font=("Arial", 18, "bold"), bg=bg, fg=fg).pack(pady=15)

        s = self.sale_use_case.get_summary()
        cards = tk.Frame(win, bg=bg)
        cards.pack(pady=5)

        cards_data = [
            ("HOY", s["hoy"], "#0d6efd"),
            ("MES", s["mes"], "#0d6efd"),
            ("TOTAL", s["total"], "#0a4d1f"),
            ("FIADOS", s["fiados"], "#d97706"),
        ]
        for i, (titulo, (cnt, tot), color) in enumerate(cards_data):
            c = tk.Frame(cards, bg=color, padx=18, pady=12)
            c.grid(row=0, column=i, padx=8)
            tk.Label(c, text=titulo, font=("Arial", 12, "bold"),
                     bg=color, fg="#ffffff").pack()
            tk.Label(c, text=f"{cnt} ventas", font=("Arial", 11),
                     bg=color, fg="#ffffff").pack()
            tk.Label(c, text=f"${tot:,.0f}".replace(",", "."),
                     font=("Arial", 16, "bold"),
                     bg=color, fg="#ffffff").pack()

        filt_frame = tk.Frame(win, bg=bg)
        filt_frame.pack(pady=5)
        filtro_var = tk.StringVar(value="all")
        for val, txt in [("all", "Todas"), ("today", "Hoy"), ("month", "Este mes")]:
            ttk.Radiobutton(filt_frame, text=txt, variable=filtro_var,
                            value=val, bootstyle="info",
                            command=lambda: recargar()).pack(side="left", padx=8)

        tk.Label(win, text="Doble clic para ver detalle. Ctrl+F12 para eliminar la venta más reciente.",
                 font=("Arial", 10, "italic"), bg=bg, fg=fg).pack(pady=5)

        tree = ttk.Treeview(win,
                            columns=("Cliente", "Ventas", "Total", "Pagado", "Pendiente"),
                            show='headings', height=14)
        for c, t, w in [("Cliente", "Cliente", 260), ("Ventas", "# Ventas", 90),
                        ("Total", "Total", 140), ("Pagado", "Pagado", 140),
                        ("Pendiente", "Pendiente", 140)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=10)

        grupos_map = {}

        def restaurar_foco():
            try:
                win.lift()
                win.focus_force()
            except Exception:
                pass

        def recargar():
            for r in tree.get_children():
                tree.delete(r)
            grupos_map.clear()
            filtro = filtro_var.get()
            if filtro == "today":
                sales = self.sale_use_case.get_sales_by_day(datetime.now().strftime("%Y-%m-%d"))
            elif filtro == "month":
                sales = self.sale_use_case.get_sales_by_month(datetime.now().strftime("%Y-%m"))
            else:
                sales = self.sale_use_case.get_all_sales(limit=1000)
            grupos = self.sale_use_case.group_sales_by_customer(sales)
            for g in grupos:
                iid = tree.insert("", "end", values=(
                    g["customer_name"],
                    g["count"],
                    f"${g['total']:,.0f}".replace(",", "."),
                    f"${g['paid']:,.0f}".replace(",", "."),
                    f"${g['pending']:,.0f}".replace(",", ".")))
                grupos_map[iid] = g

        recargar()

        def ver_detalle(event=None):
            sel = tree.selection()
            if not sel:
                return
            g = grupos_map.get(sel[0])
            if not g:
                return
            det = tk.Toplevel(win)
            det.title(f"Detalle - {g['customer_name']}")
            det.geometry("950x560")
            det.transient(win)
            det.configure(bg=bg)
            det.withdraw()
            tk.Label(det, text=f"👤 {g['customer_name']}  |  {g['count']} ventas",
                     font=("Arial", 14, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(det, text=f"Total: ${g['total']:,.0f}   |   "
                               f"Pagado: ${g['paid']:,.0f}   |   "
                               f"Pendiente: ${g['pending']:,.0f}".replace(",", "."),
                     font=("Arial", 11), bg=bg, fg=fg).pack(pady=5)
            t2 = ttk.Treeview(det,
                              columns=("ID", "Fecha", "Método", "Productos", "Total", "Estado"),
                              show='headings', height=12)
            for c, t_, w in [("ID", "#", 50), ("Fecha", "Fecha", 140),
                             ("Método", "Método", 110), ("Productos", "Productos", 260),
                             ("Total", "Total", 100), ("Estado", "Estado", 120)]:
                t2.heading(c, text=t_)
                t2.column(c, width=w, anchor="center")
            t2.pack(fill="both", expand=True, padx=15, pady=10)
            for sale in sorted(g["sales"], key=lambda x: x.date):
                resumen_items = ", ".join(
                    f"{it.quantity:g}x {it.product_name[:20]}"
                    for it in sale.items[:3])
                if len(sale.items) > 3:
                    resumen_items += f" (+{len(sale.items) - 3} más)"
                estado = "✅ Pagado"
                if sale.is_credit:
                    estado = "💳 Fiado" if not sale.is_paid else "✅ Fiado pagado"
                t2.insert("", "end", values=(
                    sale.sale_id, sale.date, sale.payment_method,
                    resumen_items,
                    f"${sale.total:,.0f}".replace(",", "."), estado))
            ttk.Button(det, text="Cerrar",
                       command=lambda: [det.destroy(), restaurar_foco()]).pack(pady=10)

            # ✅ Mostrar primero, luego grab
            show_popup_smooth(det)
            try:
                det.grab_set()
                det.focus_force()
            except Exception:
                pass

        tree.bind("<Double-1>", ver_detalle)

        def on_ctrl_f12(event=None):
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona un cliente primero.",
                                "Sin selección", parent=win)
                restaurar_foco()
                return
            g = grupos_map.get(sel[0])
            if not g or not g["sales"]:
                return
            venta_reciente = max(g["sales"], key=lambda x: x.sale_id)
            sid = venta_reciente.sale_id
            if MD.yesno(
                    f"⚠️ ¿Eliminar la venta más reciente de '{g['customer_name']}'?\n\n"
                    f"Venta #{sid} - ${venta_reciente.total:,.0f}\n"
                    f"Esto restaurará el stock.".replace(",", "."),
                    "Confirmar eliminación", parent=win) != "Yes":
                restaurar_foco()
                return
            pw = self._ask_password_1234(win)
            if not pw:
                restaurar_foco()
                return
            self.sale_use_case.delete_sale(sid)
            MD.show_info(f"Venta #{sid} eliminada y stock restaurado.",
                         "Listo", parent=win)
            recargar()
            if self.current_page == "inventario":
                self.inventory_view.load_products()
            restaurar_foco()

        win.bind("<Control-F12>", on_ctrl_f12)
        tree.bind("<Control-F12>", on_ctrl_f12)

        bf = tk.Frame(win, bg=bg)
        bf.pack(pady=10)
        ttk.Button(bf, text="📋 Ver detalle", command=ver_detalle,
                   bootstyle="info").pack(side="left", padx=5)
        ttk.Button(bf, text="🔄 Refrescar", command=recargar,
                   bootstyle="secondary").pack(side="left", padx=5)

        # ✅ Mostrar primero, luego grab
        show_popup_smooth(win)
        try:
            win.grab_set()
            win.focus_force()
        except Exception:
            pass

    def _ask_password_1234(self, parent):
        pop = tk.Toplevel(parent)
        pop.title("Contraseña requerida")
        pop.geometry("340x200")
        pop.transient(parent)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg
        fg = self.style.colors.fg

        tk.Label(pop, text="🔒 Contraseña de administrador:",
                 font=("Arial", 12, "bold"), bg=bg, fg=fg).pack(pady=20)
        v = tk.StringVar()
        e = ttk.Entry(pop, textvariable=v, show="•", width=20,
                      font=("Arial", 14), justify="center")
        e.pack(pady=5)
        e.focus_set()
        ok = {"v": False}

        def ver():
            if v.get() == "1234":
                ok["v"] = True
                pop.destroy()
            else:
                MD.show_error("Contraseña incorrecta", "Error", parent=pop)
                v.set("")

        ttk.Button(pop, text="Aceptar", command=ver,
                   style="DarkGreen.TButton").pack(pady=15)
        e.bind("<Return>", lambda e: ver())

        # ✅ Mostrar primero, luego grab
        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

        parent.wait_window(pop)
        return ok["v"]

    # =========== FIADOS ===========
    def show_credit_sales(self):
        win = tk.Toplevel(self)
        win.title("Fiados - Cuentas por cobrar")
        win.geometry("1100x700")
        win.transient(self)
        win.configure(bg=self.style.colors.bg)
        win.withdraw()
        bg = self.style.colors.bg
        fg = self.style.colors.fg

        tk.Label(win, text="💳 CUENTAS POR COBRAR (agrupado por cliente)",
                 font=("Arial", 18, "bold"), bg=bg, fg=fg).pack(pady=15)

        resumen_lbl = tk.Label(win, text="", font=("Arial", 12, "bold"),
                               bg=bg, fg=fg)
        resumen_lbl.pack(pady=5)

        frame = ttk.Frame(win, bootstyle="dark")
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        tree = ttk.Treeview(frame,
                            columns=("Cliente", "Fiados", "Total", "Abonado", "Pendiente"),
                            show='headings', height=15)
        for c, t, w in [("Cliente", "Cliente", 260), ("Fiados", "# Fiados", 90),
                        ("Total", "Total fiado", 150), ("Abonado", "Abonado", 150),
                        ("Pendiente", "Pendiente", 150)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True)

        grupos_map = {}

        def restaurar_foco():
            try:
                win.lift()
                win.focus_force()
            except Exception:
                pass

        def recargar():
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
                    g["customer_name"],
                    g["count"],
                    f"${g['total']:,.0f}".replace(",", "."),
                    f"${g['paid']:,.0f}".replace(",", "."),
                    f"${g['pending']:,.0f}".replace(",", ".")))
                grupos_map[iid] = g
            resumen_lbl.configure(
                text=f"👥 {len(grupos)} clientes con deuda   |   "
                     f"💰 Total por cobrar: ${total_global:,.0f}".replace(",", "."))

        recargar()

        def ver_detalle(event=None):
            sel = tree.selection()
            if not sel:
                return
            g = grupos_map.get(sel[0])
            if not g:
                return
            det = tk.Toplevel(win)
            det.title(f"Fiados de {g['customer_name']}")
            det.geometry("950x560")
            det.transient(win)
            det.configure(bg=bg)
            det.withdraw()
            tk.Label(det, text=f"👤 {g['customer_name']}",
                     font=("Arial", 14, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(det, text=f"Total: ${g['total']:,.0f}   |   "
                               f"Abonado: ${g['paid']:,.0f}   |   "
                               f"Pendiente: ${g['pending']:,.0f}".replace(",", "."),
                     font=("Arial", 11), bg=bg, fg=fg).pack(pady=5)
            t2 = ttk.Treeview(det,
                              columns=("ID", "Fecha", "Productos", "Total",
                                       "Abonado", "Pendiente"),
                              show='headings', height=12)
            for c, t_, w in [("ID", "#", 50), ("Fecha", "Fecha", 130),
                             ("Productos", "Productos", 280), ("Total", "Total", 90),
                             ("Abonado", "Abonado", 90), ("Pendiente", "Pendiente", 100)]:
                t2.heading(c, text=t_)
                t2.column(c, width=w, anchor="center")
            t2.pack(fill="both", expand=True, padx=15, pady=10)
            for sale in sorted(g["sales"], key=lambda x: x.date):
                resumen_items = ", ".join(
                    f"{it.quantity:g}x {it.product_name[:18]}"
                    for it in sale.items[:3])
                if len(sale.items) > 3:
                    resumen_items += f" (+{len(sale.items) - 3} más)"
                t2.insert("", "end", values=(
                    sale.sale_id, sale.date, resumen_items,
                    f"${sale.total:,.0f}".replace(",", "."),
                    f"${sale.amount_paid:,.0f}".replace(",", "."),
                    f"${sale.pending():,.0f}".replace(",", ".")))
            ttk.Button(det, text="Cerrar",
                       command=lambda: [det.destroy(), restaurar_foco()]).pack(pady=10)

            show_popup_smooth(det)
            try:
                det.grab_set()
                det.focus_force()
            except Exception:
                pass

        tree.bind("<Double-1>", ver_detalle)

        def abonar():
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona un cliente primero.",
                                "Sin selección", parent=win)
                restaurar_foco()
                return
            g = grupos_map.get(sel[0])
            if not g:
                return
            ventas_pend = [v for v in g["sales"] if v.pending() > 0.01]
            if not ventas_pend:
                MD.show_info("Este cliente no tiene deudas pendientes.", "Listo", parent=win)
                restaurar_foco()
                return
            venta = sorted(ventas_pend, key=lambda x: x.sale_id)[0]
            pendiente = venta.pending()
            self._abonar_dialog(win, venta.sale_id, venta, pendiente, recargar)

        def marcar_pagado():
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona un cliente primero.",
                                "Sin selección", parent=win)
                restaurar_foco()
                return
            g = grupos_map.get(sel[0])
            if not g:
                return
            if MD.yesno(
                    f"¿Marcar TODOS los fiados pendientes de '{g['customer_name']}' como PAGADOS?\n"
                    f"Total a marcar: ${g['pending']:,.0f}".replace(",", "."),
                    "Confirmar", parent=win) != "Yes":
                restaurar_foco()
                return
            for v in g["sales"]:
                if v.pending() > 0.01:
                    self.sale_use_case.mark_as_paid(v.sale_id)
            recargar()
            MD.show_info("Fiados marcados como pagados.", "Listo", parent=win)
            restaurar_foco()

        def on_ctrl_f12(event=None):
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona un cliente primero.",
                                "Sin selección", parent=win)
                restaurar_foco()
                return
            g = grupos_map.get(sel[0])
            if not g or not g["sales"]:
                return
            venta_reciente = max(g["sales"], key=lambda x: x.sale_id)
            sid = venta_reciente.sale_id
            if MD.yesno(
                    f"⚠️ ¿Eliminar el fiado más reciente de '{g['customer_name']}'?\n\n"
                    f"Venta #{sid} - ${venta_reciente.total:,.0f}\n"
                    f"Esto restaurará el stock.".replace(",", "."),
                    "Confirmar eliminación", parent=win) != "Yes":
                restaurar_foco()
                return
            pw = self._ask_password_1234(win)
            if not pw:
                restaurar_foco()
                return
            self.sale_use_case.delete_sale(sid)
            MD.show_info(f"Fiado #{sid} eliminado y stock restaurado.",
                         "Listo", parent=win)
            recargar()
            if self.current_page == "inventario":
                self.inventory_view.load_products()
            restaurar_foco()

        win.bind("<Control-F12>", on_ctrl_f12)
        tree.bind("<Control-F12>", on_ctrl_f12)

        bf = tk.Frame(win, bg=bg)
        bf.pack(pady=10)
        ttk.Button(bf, text="📋 Ver detalle", command=ver_detalle,
                   bootstyle="info").pack(side="left", padx=5)
        ttk.Button(bf, text="💵 Abonar (más antigua)",
                   command=abonar, style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="✅ Marcar todo pagado",
                   command=marcar_pagado, style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="🔄 Refrescar", command=recargar,
                   bootstyle="secondary").pack(side="left", padx=5)

        show_popup_smooth(win)
        try:
            win.grab_set()
            win.focus_force()
        except Exception:
            pass

    def _abonar_dialog(self, parent, sale_id, venta, pendiente, on_done):
        pop = tk.Toplevel(parent)
        pop.title(f"Abonar a venta #{sale_id}")
        pop.geometry("420x400")
        pop.transient(parent)
        pop.configure(bg=self.style.colors.bg)
        pop.withdraw()
        bg = self.style.colors.bg
        fg = self.style.colors.fg

        tk.Label(pop, text="💵 Registrar Abono",
                 font=("Arial", 16, "bold"), bg=bg, fg=fg).pack(pady=15)
        cliente = venta.customer_name if venta.customer_name else "(sin nombre)"
        tk.Label(pop, text=f"Cliente: {cliente}", font=("Arial", 12),
                 bg=bg, fg=fg).pack(pady=5)
        tk.Label(pop, text=f"Total: ${venta.total:,.0f}".replace(",", "."),
                 font=("Arial", 12), bg=bg, fg=fg).pack(pady=3)
        tk.Label(pop, text=f"Abonado: ${venta.amount_paid:,.0f}".replace(",", "."),
                 font=("Arial", 12), bg=bg, fg=fg).pack(pady=3)
        tk.Label(pop, text=f"Pendiente: ${pendiente:,.0f}".replace(",", "."),
                 font=("Arial", 14, "bold"),
                 bg="#0a4d1f", fg="#a8e6a8",
                 padx=10, pady=8).pack(pady=10)

        tk.Label(pop, text="Monto del abono:",
                 bg=bg, fg=fg).pack(pady=(10, 3))
        monto_var = tk.StringVar()
        e = ttk.Entry(pop, textvariable=monto_var, width=20,
                      font=("Arial", 16), justify="center")
        e.pack(pady=5)
        e.focus_set()

        def aplicar():
            try:
                monto = float(monto_var.get().replace("$", "").replace(".", "").replace(",", "."))
                if monto <= 0:
                    raise ValueError
            except ValueError:
                MD.show_error("Monto inválido", "Error", parent=pop)
                return
            if monto > pendiente + 0.01:
                if MD.yesno(
                        f"El monto (${monto:,.0f}) es mayor al pendiente (${pendiente:,.0f}).\n"
                        f"¿Registrar solo ${pendiente:,.0f}?".replace(",", "."),
                        "Confirmar", parent=pop) != "Yes":
                    return
                monto = pendiente
            self.sale_use_case.add_payment(sale_id, monto)
            pop.destroy()
            MD.show_info(f"✅ Abono de ${monto:,.0f} registrado.".replace(",", "."),
                         "Listo", parent=parent)
            on_done()
            try:
                parent.lift()
                parent.focus_force()
            except Exception:
                pass

        e.bind("<Return>", lambda e: aplicar())
        bf = tk.Frame(pop, bg=bg)
        bf.pack(pady=15)
        ttk.Button(bf, text="Registrar abono", command=aplicar,
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar",
                   command=pop.destroy).pack(side="left", padx=5)

        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

    # =========== AUTO-INICIO ===========
    def _get_startup_bat_path(self):
        startup = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows',
                               'Start Menu', 'Programs', 'Startup')
        return os.path.join(startup, 'MiniPOS_Portable.bat')

    def _is_autostart_enabled(self):
        return os.path.exists(self._get_startup_bat_path())

    def toggle_autostart(self):
        bat = self._get_startup_bat_path()
        if self.autostart_var.get():
            try:
                with open(bat, 'w', encoding='utf-8') as f:
                    f.write(f'@echo off\nstart "" "{sys.executable}"\n')
                MD.show_info("✅ Auto-inicio ACTIVADO.", "Auto-inicio", parent=self)
            except Exception as e:
                self.autostart_var.set(False)
                MD.show_error(f"Error: {e}", "Error", parent=self)
        else:
            try:
                if os.path.exists(bat):
                    os.remove(bat)
                MD.show_info("❌ Auto-inicio DESACTIVADO.", "Auto-inicio", parent=self)
            except Exception as e:
                self.autostart_var.set(True)
                MD.show_error(f"Error: {e}", "Error", parent=self)

    # =========== REPORTES ===========
    def generate_daily_report(self):
        hoy = datetime.now().strftime("%Y-%m-%d")
        sales = self.sale_use_case.get_sales_by_day(hoy)
        if not sales:
            MD.show_info("No hay ventas hoy.", "Reporte vacío", parent=self)
            return
        arch = filedialog.asksaveasfilename(defaultextension=".txt",
                                            initialfile=f"ventas_{hoy}.txt",
                                            filetypes=[("Texto", "*.txt")])
        if not arch:
            return
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
            L.append(f"Venta #{s.sale_id}  -  {hora}  -  {s.payment_method}{cliente}{fiado}")
            L.append(f"  {'Cant.':>8}  {'Producto':<30} {'P.Unit':>10} {'Subtotal':>12}")
            for it in s.items:
                L.append(f"  {it.quantity:>8g}  {it.product_name[:30]:<30} "
                         f"${it.unit_price:>9,.0f} ${it.subtotal:>11,.0f}".replace(",", "."))
            L.append(f"  {'':>8}  {'':<30} {'':>10} ${s.total:>11,.0f}".replace(",", "."))
            L.append("")
        L += ["=" * 60,
              f"TOTAL DEL DÍA:      ${total_dia:>12,.0f}".replace(",", "."),
              f"VENTAS REALIZADAS:  {len(sales)}",
              f"PRODUCTOS VENDIDOS: {total_prod:g}", "=" * 60]
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
            MD.show_error("Falta openpyxl.", "Error", parent=self)
            return
        ym = datetime.now().strftime("%Y-%m")
        sales = self.sale_use_case.get_sales_by_month(ym)
        if not sales:
            MD.show_info("No hay ventas este mes.", "Reporte vacío", parent=self)
            return
        arch = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            initialfile=f"ventas_{ym}.xlsx",
                                            filetypes=[("Excel", "*.xlsx")])
        if not arch:
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Ventas {ym}"
        ws.append(["Fecha", "Venta #", "Cliente", "Método", "Fiado", "Producto",
                   "Código", "Cantidad", "Unidad", "P. Unit.", "Subtotal"])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="305496")
            c.alignment = Alignment(horizontal="center")
        for s in sales:
            for it in s.items:
                ws.append([s.date, s.sale_id, s.customer_name, s.payment_method,
                           "Sí" if s.is_credit else "No", it.product_name, it.barcode,
                           it.quantity, "unidad", it.unit_price, it.subtotal])
        total = sum(s.total for s in sales)
        ws.append([])
        ws.append(["", "", "", "", "", "", "", "", "", "TOTAL:", total])
        for col, w in zip("ABCDEFGHIJK", [20, 10, 25, 15, 10, 30, 20, 10, 10, 12, 12]):
            ws.column_dimensions[col].width = w
        try:
            wb.save(arch)
            MD.show_info(f"Guardado:\n{arch}", "Listo", parent=self)
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    # =========== EXPORTAR / IMPORTAR ===========
    def export_db(self):
        arch = filedialog.asksaveasfilename(defaultextension=".db",
                                            filetypes=[("SQLite", "*.db")])
        if arch:
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, arch)
            MD.show_info("Base de datos exportada.", "Listo", parent=self)

    def import_db(self):
        arch = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if arch and MD.yesno("¿Reemplazar datos?", "Confirmar", parent=self) == "Yes":
            self.db_manager.close_connection()
            shutil.copy2(arch, self.db_path)
            self.inventory_view.load_products()
            MD.show_info("Importada.", "Listo", parent=self)