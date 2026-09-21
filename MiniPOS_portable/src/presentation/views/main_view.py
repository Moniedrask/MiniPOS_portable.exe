import tkinter as tk
from tkinter import filedialog, font as tkfont
import ttkbootstrap as ttk
from ttkbootstrap import Style, Toplevel
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

    # =========== ESTILO VERDE OSCURO GLOBAL ===========
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
        pop.grab_set()
        pop.protocol("WM_DELETE_WINDOW", lambda: self._cancel_login(pop))
        pop.withdraw()

        ttk.Label(pop, text="🔒 Contraseña requerida",
                  font=("Arial", 14, "bold")).pack(pady=15)
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
        show_popup_smooth(pop, self.current_theme == 'darkly')
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
        pop.grab_set()
        pop.withdraw()

        ttk.Label(pop, text="🔐 Cambiar contraseña",
                  font=("Arial", 14, "bold")).pack(pady=15)
        ttk.Label(pop, text="Contraseña actual:").pack()
        e1 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e1.pack(pady=5)
        e1.focus_set()
        ttk.Label(pop, text="Nueva contraseña:").pack()
        e2 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e2.pack(pady=5)
        ttk.Label(pop, text="Confirmar nueva:").pack()
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
        show_popup_smooth(pop, self.current_theme == 'darkly')

    def _setup_password_first_time(self):
        pop = tk.Toplevel(self)
        pop.title("Configurar contraseña")
        pop.geometry("380x280")
        pop.transient(self)
        pop.grab_set()
        pop.withdraw()
        ttk.Label(pop, text="🔐 Crear contraseña de inicio",
                  font=("Arial", 14, "bold")).pack(pady=15)
        ttk.Label(pop, text="Nueva contraseña (mín. 4 caracteres):").pack()
        e1 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12))
        e1.pack(pady=5)
        e1.focus_set()
        ttk.Label(pop, text="Confirmar:").pack()
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
        show_popup_smooth(pop, self.current_theme == 'darkly')

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
        # ✅ Menú superior oscuro personalizado
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
            menu.add_command(label="📊 Resumen de Ventas", command=self.show_sales_summary)
            menu.add_command(label="💳 Fiados (cuentas por cobrar)",
                             command=self.show_credit_sales)

        self.menubar.add_menu("Opciones", build_opciones)
        self.menubar.add_menu("Ventas", build_ventas)

        # --- Pestañas ---
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
        win.geometry("1000x650")
        win.transient(self)
        win.grab_set()
        win.withdraw()
        ttk.Label(win, text="📊 RESUMEN DE VENTAS",
                  font=("Arial", 18, "bold")).pack(pady=15)
        s = self.sale_use_case.get_summary()
        cards = ttk.Frame(win)
        cards.pack(pady=10)
        for i, (titulo, (cnt, tot), style_) in enumerate([
                ("HOY", s["hoy"], "info"),
                ("MES", s["mes"], "primary"),
                ("TOTAL", s["total"], "success"),
                ("FIADOS", s["fiados"], "warning")]):
            c = ttk.Frame(cards, bootstyle=style_, padding=15)
            c.grid(row=0, column=i, padx=8)
            ttk.Label(c, text=titulo, font=("Arial", 12, "bold"),
                      bootstyle=f"inverse-{style_}").pack()
            ttk.Label(c, text=f"{cnt} ventas", font=("Arial", 11),
                      bootstyle=f"inverse-{style_}").pack()
            ttk.Label(c, text=f"${tot:,.0f}".replace(",", "."),
                      font=("Arial", 16, "bold"),
                      bootstyle=f"inverse-{style_}").pack()

        ttk.Label(win, text="Últimas ventas (Selecciona una y presiona Ctrl+F12 para eliminarla):",
                  font=("Arial", 10, "italic")).pack(pady=10)

        tree = ttk.Treeview(win,
                            columns=("ID", "Fecha", "Cliente", "Método", "Total", "Estado"),
                            show='headings', height=15)
        for c, t, w in [("ID", "#", 50), ("Fecha", "Fecha", 150),
                        ("Cliente", "Cliente", 200), ("Método", "Método", 120),
                        ("Total", "Total", 120), ("Estado", "Estado", 100)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=10)

        sales = self.sale_use_case.get_all_sales(limit=300)
        for s_ in sales:
            estado = "✅ Pagado"
            if s_.is_credit:
                estado = "💳 Fiado" if not s_.is_paid else "✅ Fiado pagado"
            tree.insert("", "end", values=(
                s_.sale_id, s_.date, s_.customer_name or "-",
                s_.payment_method,
                f"${s_.total:,.0f}".replace(",", "."), estado))

        def on_ctrl_f12(event=None):
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona una venta primero.", "Sin selección", parent=win)
                return
            vals = tree.item(sel[0], 'values')
            sid = int(vals[0])
            if MD.yesno(f"⚠️ ¿Eliminar la venta #{sid}?\n\nEsto restaurará el stock.",
                        "Confirmar eliminación", parent=win) != "Yes":
                return
            pw = self._ask_password_1234(win)
            if not pw:
                return
            self.sale_use_case.delete_sale(sid)
            MD.show_info(f"Venta #{sid} eliminada y stock restaurado.", "Listo", parent=win)
            win.destroy()
            self.show_sales_summary()
            if self.current_page == "inventario":
                self.inventory_view.load_products()

        win.bind("<Control-F12>", on_ctrl_f12)
        tree.bind("<Control-F12>", on_ctrl_f12)
        show_popup_smooth(win, self.current_theme == 'darkly')

    def _ask_password_1234(self, parent):
        pop = tk.Toplevel(parent)
        pop.title("Contraseña requerida")
        pop.geometry("340x200")
        pop.transient(parent)
        pop.grab_set()
        pop.withdraw()
        ttk.Label(pop, text="🔒 Contraseña de administrador:",
                  font=("Arial", 12, "bold")).pack(pady=20)
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
        show_popup_smooth(pop, self.current_theme == 'darkly')
        parent.wait_window(pop)
        return ok["v"]

    # =========== FIADOS ===========
    def show_credit_sales(self):
        win = tk.Toplevel(self)
        win.title("Fiados - Cuentas por cobrar")
        win.geometry("1150x720")
        win.transient(self)
        win.grab_set()
        win.withdraw()

        ttk.Label(win, text="💳 CUENTAS POR COBRAR (FIADOS)",
                  font=("Arial", 18, "bold")).pack(pady=15)

        resumen_lbl = ttk.Label(win, text="", font=("Arial", 12, "bold"))
        resumen_lbl.pack(pady=5)

        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        tree = ttk.Treeview(frame,
                            columns=("Cliente", "Fecha", "Productos", "Total",
                                     "Abonado", "Pendiente", "Estado"),
                            show='headings', height=15)
        for c, t, w in [("Cliente", "Cliente", 180), ("Fecha", "Fecha", 140),
                        ("Productos", "Productos fiados", 280),
                        ("Total", "Total", 90), ("Abonado", "Abonado", 90),
                        ("Pendiente", "Pendiente", 100), ("Estado", "Estado", 100)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True)

        sales_map = {}

        def recargar():
            for r in tree.get_children():
                tree.delete(r)
            sales_map.clear()
            ventas = self.sale_use_case.get_credit_sales(only_unpaid=True)
            ventas.sort(key=lambda s: (s.customer_name or "zzz_sin_nombre").lower())
            total_pend = 0.0
            clientes = {}
            for s_ in ventas:
                cliente = s_.customer_name if s_.customer_name else "(sin nombre)"
                pendiente = s_.pending()
                total_pend += pendiente
                if s_.customer_name:
                    clientes[s_.customer_name] = clientes.get(s_.customer_name, 0) + pendiente
                # Resumen de productos de esta venta
                resumen_items = ", ".join(
                    f"{it.quantity:g}x {it.product_name[:18]}"
                    for it in s_.items[:3])
                if len(s_.items) > 3:
                    resumen_items += f" (+{len(s_.items) - 3} más)"
                estado = "✅ Pagado" if s_.is_paid else "💳 Pendiente"
                iid = tree.insert("", "end", values=(
                    cliente, s_.date, resumen_items,
                    f"${s_.total:,.0f}".replace(",", "."),
                    f"${s_.amount_paid:,.0f}".replace(",", "."),
                    f"${pendiente:,.0f}".replace(",", "."),
                    estado))
                sales_map[iid] = s_.sale_id

            # Resumen agrupado por cliente
            if clientes:
                texto_clientes = "  |  ".join(
                    f"{k}: ${v:,.0f}".replace(",", ".")
                    for k, v in list(clientes.items())[:5])
                if len(clientes) > 5:
                    texto_clientes += f"  (+{len(clientes) - 5} más)"
                resumen_lbl.configure(
                    text=f"📋 {len(ventas)} fiados   |   💰 Total: ${total_pend:,.0f}\n"
                         f"👥 Por cliente: {texto_clientes}".replace(",", "."))
            else:
                resumen_lbl.configure(text="")

        recargar()

        def ver_productos():
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona un fiado primero.", "Sin selección", parent=win)
                return
            sid = sales_map.get(sel[0])
            venta = None
            for v in self.sale_use_case.get_credit_sales(only_unpaid=False):
                if v.sale_id == sid:
                    venta = v
                    break
            if not venta:
                return
            detail_win = tk.Toplevel(win)
            detail_win.title(f"Productos fiados - Venta #{sid}")
            detail_win.geometry("600x480")
            detail_win.transient(win)
            detail_win.grab_set()
            detail_win.withdraw()
            cliente = venta.customer_name if venta.customer_name else "(sin nombre)"
            ttk.Label(detail_win, text=f"💳 Fiado a: {cliente}",
                      font=("Arial", 14, "bold")).pack(pady=10)
            ttk.Label(detail_win, text=f"Fecha: {venta.date}",
                      font=("Arial", 11)).pack(pady=3)
            t2 = ttk.Treeview(detail_win,
                              columns=("Prod", "Qty", "Unit", "Sub"),
                              show='headings', height=10)
            for c, t_, w in [("Prod", "Producto", 220), ("Qty", "Cant.", 70),
                             ("Unit", "P. Unit.", 100), ("Sub", "Subtotal", 110)]:
                t2.heading(c, text=t_)
                t2.column(c, width=w, anchor="center")
            t2.pack(fill="both", expand=True, padx=15, pady=10)
            for it in venta.items:
                t2.insert("", "end", values=(
                    it.product_name, f"{it.quantity:g}",
                    f"${it.unit_price:,.0f}".replace(",", "."),
                    f"${it.subtotal:,.0f}".replace(",", ".")))
            total_f = ttk.Label(detail_win,
                                text=f"Total: ${venta.total:,.0f}   |   "
                                     f"Abonado: ${venta.amount_paid:,.0f}   |   "
                                     f"Pendiente: ${venta.pending():,.0f}".replace(",", "."),
                                font=("Arial", 12, "bold"))
            total_f.pack(pady=10)
            ttk.Button(detail_win, text="Cerrar",
                       command=detail_win.destroy).pack(pady=10)
            show_popup_smooth(detail_win, self.current_theme == 'darkly')

        def abonar():
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona un fiado primero.", "Sin selección", parent=win)
                return
            sid = sales_map.get(sel[0])
            if not sid:
                return
            venta = None
            for v in self.sale_use_case.get_credit_sales(only_unpaid=True):
                if v.sale_id == sid:
                    venta = v
                    break
            if not venta:
                return
            pendiente = venta.pending()
            if pendiente <= 0:
                MD.show_info("Esta venta ya está pagada.", "Listo", parent=win)
                return
            self._abonar_dialog(win, sid, venta, pendiente, recargar)

        def marcar_pagado():
            sel = tree.selection()
            if not sel:
                return
            sid = sales_map.get(sel[0])
            if not sid:
                return
            if MD.yesno(f"¿Marcar la venta #{sid} como PAGADA por completo?",
                        "Confirmar", parent=win) == "Yes":
                self.sale_use_case.mark_as_paid(sid)
                recargar()
                MD.show_info("Marcada como pagada.", "Listo", parent=win)

        def on_ctrl_f12(event=None):
            sel = tree.selection()
            if not sel:
                MD.show_warning("Selecciona un fiado primero.", "Sin selección", parent=win)
                return
            sid = sales_map.get(sel[0])
            if not sid:
                return
            if MD.yesno(f"⚠️ ¿Eliminar el fiado #{sid}?\n\nEsto restaurará el stock.",
                        "Confirmar eliminación", parent=win) != "Yes":
                return
            pw = self._ask_password_1234(win)
            if not pw:
                return
            self.sale_use_case.delete_sale(sid)
            MD.show_info(f"Fiado #{sid} eliminado y stock restaurado.", "Listo", parent=win)
            recargar()
            if self.current_page == "inventario":
                self.inventory_view.load_products()

        win.bind("<Control-F12>", on_ctrl_f12)
        tree.bind("<Control-F12>", on_ctrl_f12)

        bf = ttk.Frame(win)
        bf.pack(pady=10)
        ttk.Button(bf, text="📋 Ver productos",
                   command=ver_productos,
                   bootstyle="info").pack(side="left", padx=5)
        ttk.Button(bf, text="💵 Abonar",
                   command=abonar,
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="✅ Marcar como pagado",
                   command=marcar_pagado,
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="🔄 Refrescar", command=recargar,
                   bootstyle="secondary").pack(side="left", padx=5)

        show_popup_smooth(win, self.current_theme == 'darkly')

    def _abonar_dialog(self, parent, sale_id, venta, pendiente, on_done):
        pop = tk.Toplevel(parent)
        pop.title(f"Abonar a venta #{sale_id}")
        pop.geometry("420x380")
        pop.transient(parent)
        pop.grab_set()
        pop.withdraw()

        ttk.Label(pop, text="💵 Registrar Abono",
                  font=("Arial", 16, "bold")).pack(pady=15)
        cliente = venta.customer_name if venta.customer_name else "(sin nombre)"
        ttk.Label(pop, text=f"Cliente: {cliente}", font=("Arial", 12)).pack(pady=5)
        ttk.Label(pop, text=f"Total: ${venta.total:,.0f}".replace(",", "."),
                  font=("Arial", 12)).pack(pady=3)
        ttk.Label(pop, text=f"Abonado: ${venta.amount_paid:,.0f}".replace(",", "."),
                  font=("Arial", 12)).pack(pady=3)
        ttk.Label(pop, text=f"Pendiente: ${pendiente:,.0f}".replace(",", "."),
                  font=("Arial", 14, "bold"),
                  background="#0a4d1f", foreground="#a8e6a8",
                  padding=8).pack(pady=10)

        ttk.Label(pop, text="Monto del abono:").pack(pady=(10, 3))
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

        e.bind("<Return>", lambda e: aplicar())
        bf = ttk.Frame(pop)
        bf.pack(pady=15)
        ttk.Button(bf, text="Registrar abono", command=aplicar,
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar", command=pop.destroy).pack(side="left", padx=5)
        show_popup_smooth(pop, self.current_theme == 'darkly')

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