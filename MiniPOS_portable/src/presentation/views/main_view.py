import tkinter as tk
from tkinter import filedialog, font as tkfont
import ttkbootstrap as ttk
from ttkbootstrap import Style, Toplevel
from ttkbootstrap.dialogs import Messagebox
import os, shutil, sys
from datetime import datetime
from application.use_case.product_use_case import ProductCase
from application.use_case.sale_use_case import SaleCase
from infrastucture.db.db_manager import DBManager
from presentation.views.payment_view import PaymentView, center_window, apply_titlebar_theme
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
        self.title("MiniPOS Portable v2.1")
        try: self.state('zoomed')
        except Exception: self.geometry("1400x900")

        self.current_theme = 'darkly'
        self.style = Style(theme=self.current_theme)
        self.configure(bg=self.style.colors.bg)
        self.is_fullscreen = False

        # Rutas
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.db_path = os.path.join(base_dir, "data", "ventas.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.db_manager = DBManager(self.db_path)
        self.product_use_case = ProductCase(self.db_manager)
        self.sale_use_case = SaleCase(self.db_manager)

        # ✅ Contraseña de inicio
        if not self._check_startup_password():
            self.destroy(); return

        self.create_widgets()
        self.show_page("pagos")
        self._apply_font_size()

        self.bind('<F2>', lambda e: self.inventory_view.add_product_popup() if self.current_page == "inventario" else None)
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.bind('<Control-F12>', lambda e: self._handle_ctrl_f12())
        self.after(200, lambda: apply_titlebar_theme(self, self.current_theme == 'darkly'))

    # =========== CONTRASEÑA ===========
    def _check_startup_password(self):
        pwd = self.db_manager.get_setting("startup_password", "")
        if not pwd:
            return True  # No hay contraseña, se abre normal
        # Pedir contraseña al iniciar
        pop = Toplevel(self); pop.title("MiniPOS - Iniciar sesión")
        pop.geometry("380x220"); pop.transient(self); pop.grab_set()
        ttk.Label(pop, text="🔒 Contraseña requerida", font=("Arial", 14, "bold")).pack(pady=15)
        v = tk.StringVar()
        e = ttk.Entry(pop, textvariable=v, show="•", width=25, font=("Arial", 14), justify="center")
        e.pack(pady=10); e.focus_set()
        resultado = {"ok": False}
        def verificar():
            if v.get() == pwd:
                resultado["ok"] = True; pop.destroy()
            else:
                Messagebox.show_error("Contraseña incorrecta", "Error", parent=pop); v.set("")
        ttk.Button(pop, text="Ingresar", command=verificar, bootstyle="success").pack(pady=10)
        e.bind("<Return>", lambda e: verificar())
        pop.after(100, lambda: center_window(pop))
        self.wait_window(pop)
        return resultado["ok"]

    def _change_password(self):
        if not is_admin():
            Messagebox.show_warning("Debes ejecutar la app COMO ADMINISTRADOR\npara cambiar la contraseña.",
                                    "Permisos insuficientes", parent=self); return
        actual = self.db_manager.get_setting("startup_password", "")
        pop = Toplevel(self); pop.title("Cambiar contraseña")
        pop.geometry("400x360"); pop.transient(self); pop.grab_set()
        ttk.Label(pop, text="🔐 Cambiar contraseña", font=("Arial", 14, "bold")).pack(pady=15)
        ttk.Label(pop, text="Contraseña actual:").pack()
        e1 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12)); e1.pack(pady=5); e1.focus_set()
        ttk.Label(pop, text="Nueva contraseña:").pack()
        e2 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12)); e2.pack(pady=5)
        ttk.Label(pop, text="Confirmar nueva:").pack()
        e3 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12)); e3.pack(pady=5)
        vaciar = tk.BooleanVar(value=False)
        ttk.Checkbutton(pop, text="Quitar contraseña (dejar vacío)", variable=vaciar).pack(pady=8)
        def aplicar():
            if vaciar.get():
                self.db_manager.set_setting("startup_password", "")
                Messagebox.show_info("Contraseña eliminada.", "OK", parent=pop); pop.destroy(); return
            if e1.get() != actual:
                Messagebox.show_error("La contraseña actual no coincide.", "Error", parent=pop); return
            if len(e2.get()) < 4:
                Messagebox.show_error("La nueva contraseña debe tener al menos 4 caracteres.", "Error", parent=pop); return
            if e2.get() != e3.get():
                Messagebox.show_error("Las contraseñas nuevas no coinciden.", "Error", parent=pop); return
            self.db_manager.set_setting("startup_password", e2.get())
            Messagebox.show_info("Contraseña cambiada.", "OK", parent=pop); pop.destroy()
        ttk.Button(pop, text="Guardar", command=aplicar, bootstyle="success").pack(pady=12)
        pop.after(100, lambda: center_window(pop))

    def _setup_password_first_time(self):
        """Activa la contraseña por primera vez (no requiere admin)."""
        pop = Toplevel(self); pop.title("Configurar contraseña")
        pop.geometry("380x280"); pop.transient(self); pop.grab_set()
        ttk.Label(pop, text="🔐 Crear contraseña de inicio",
                  font=("Arial", 14, "bold")).pack(pady=15)
        ttk.Label(pop, text="Nueva contraseña (mín. 4 caracteres):").pack()
        e1 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12)); e1.pack(pady=5); e1.focus_set()
        ttk.Label(pop, text="Confirmar:").pack()
        e2 = ttk.Entry(pop, show="•", width=25, font=("Arial", 12)); e2.pack(pady=5)
        def guardar():
            if len(e1.get()) < 4:
                Messagebox.show_error("Mínimo 4 caracteres.", "Error", parent=pop); return
            if e1.get() != e2.get():
                Messagebox.show_error("No coinciden.", "Error", parent=pop); return
            self.db_manager.set_setting("startup_password", e1.get())
            Messagebox.show_info("Contraseña activada. Se pedirá al iniciar.", "OK", parent=pop)
            pop.destroy()
        ttk.Button(pop, text="Guardar", command=guardar, bootstyle="success").pack(pady=12)
        pop.after(100, lambda: center_window(pop))

    # =========== TAMAÑO DE FUENTE ===========
    def _apply_font_size(self):
        size = int(self.db_manager.get_setting("font_size", "11"))
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(size=size)
            except Exception:
                pass
        self.font_size = size

    def _change_font_size(self, delta):
        new = max(8, min(20, self.font_size + delta))
        self.db_manager.set_setting("font_size", str(new))
        self.font_size = new
        self._apply_font_size()
        Messagebox.show_info(f"Tamaño de letra: {new}", "Fuente", parent=self)

    # =========== UI ===========
    def create_widgets(self):
        menubar = tk.Menu(self, bg=self.style.colors.bg, fg=self.style.colors.fg,
                          activebackground=self.style.colors.selectbg,
                          activeforeground=self.style.colors.selectfg, bd=0)
        # --- Opciones ---
        om = tk.Menu(menubar, tearoff=0, bg=self.style.colors.bg, fg=self.style.colors.fg,
                     activebackground=self.style.colors.selectbg,
                     activeforeground=self.style.colors.selectfg)
        om.add_command(label="🌓 Cambiar Tema", command=self.toggle_theme)
        om.add_separator()
        # --- Fuente ---
        fm = tk.Menu(om, tearoff=0, bg=self.style.colors.bg, fg=self.style.colors.fg,
                     activebackground=self.style.colors.selectbg,
                     activeforeground=self.style.colors.selectfg)
        fm.add_command(label="➕ Aumentar letra", command=lambda: self._change_font_size(1))
        fm.add_command(label="➖ Reducir letra", command=lambda: self._change_font_size(-1))
        om.add_cascade(label="🔤 Tamaño de letra", menu=fm)
        # --- Contraseña ---
        pm = tk.Menu(om, tearoff=0, bg=self.style.colors.bg, fg=self.style.colors.fg,
                     activebackground=self.style.colors.selectbg,
                     activeforeground=self.style.colors.selectfg)
        pm.add_command(label="🆕 Activar/Crear contraseña", command=self._setup_password_first_time)
        pm.add_command(label="🔐 Cambiar contraseña (admin)", command=self._change_password)
        om.add_cascade(label="🔑 Contraseña de inicio", menu=pm)
        om.add_separator()
        self.autostart_var = tk.BooleanVar(value=self._is_autostart_enabled())
        om.add_checkbutton(label="🚀 Iniciar con Windows", variable=self.autostart_var,
                           command=self.toggle_autostart)
        om.add_separator()
        om.add_command(label="📄 Reporte del Día (TXT)", command=self.generate_daily_report)
        om.add_command(label="📊 Reporte del Mes (Excel)", command=self.generate_monthly_report)
        om.add_separator()
        om.add_command(label="📤 Exportar Base de Datos", command=self.export_db)
        om.add_command(label="📥 Importar Base de Datos", command=self.import_db)
        menubar.add_cascade(label="Opciones", menu=om)
        # --- Ventas (nuevo) ---
        vm = tk.Menu(menubar, tearoff=0, bg=self.style.colors.bg, fg=self.style.colors.fg,
                     activebackground=self.style.colors.selectbg,
                     activeforeground=self.style.colors.selectfg)
        vm.add_command(label="📊 Resumen de Ventas", command=self.show_sales_summary)
        vm.add_command(label="💳 Fiados (cuentas por cobrar)", command=self.show_credit_sales)
        menubar.add_cascade(label="Ventas", menu=vm)
        self.config(menu=menubar)

        # --- Pestañas ---
        tabs = ttk.Frame(self, bootstyle="dark"); tabs.pack(fill="x", padx=10, pady=(10, 0))
        self.btn_pagos = ttk.Button(tabs, text="🛒  PAGOS", bootstyle="success",
                                    command=lambda: self.show_page("pagos"), width=20)
        self.btn_pagos.pack(side="left", padx=3, pady=3, ipady=8)
        self.btn_inv = ttk.Button(tabs, text="📦  INVENTARIO", bootstyle="secondary",
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
        for w in (self.payment_view, self.inventory_view): w.pack_forget()
        if page == "pagos":
            self.payment_view.pack(fill="both", expand=True)
            self.btn_pagos.configure(bootstyle="success"); self.btn_inv.configure(bootstyle="secondary")
            self.current_page = "pagos"
        else:
            self.inventory_view.load_products()
            self.inventory_view.pack(fill="both", expand=True)
            self.btn_pagos.configure(bootstyle="secondary"); self.btn_inv.configure(bootstyle="success")
            self.current_page = "inventario"

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)

    def toggle_theme(self):
        self.current_theme = 'flatly' if self.current_theme == 'darkly' else 'darkly'
        self.style.theme_use(self.current_theme)
        self.configure(bg=self.style.colors.bg)
        apply_titlebar_theme(self, self.current_theme == 'darkly')

    # =========== RESUMEN DE VENTAS / CTRL+F12 ===========
    def _handle_ctrl_f12(self):
        """Ctrl+F12 dentro de la ventana de resumen elimina la venta seleccionada."""
        if self.current_page == "ventas_window":
            return
        # El binding se maneja dentro de la ventana de resumen

    def show_sales_summary(self):
        self.current_page = "ventas_window"
        win = Toplevel(self); win.title("Resumen de Ventas")
        win.geometry("1000x650"); win.transient(self); win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: self._close_sales_win(win))

        ttk.Label(win, text="📊 RESUMEN DE VENTAS", font=("Arial", 18, "bold")).pack(pady=15)
        s = self.sale_use_case.get_summary()
        cards = ttk.Frame(win); cards.pack(pady=10)
        for i, (titulo, (cnt, tot), style_) in enumerate([
            ("HOY", s["hoy"], "info"), ("MES", s["mes"], "primary"),
            ("TOTAL", s["total"], "success"), ("FIADOS", s["fiados"], "warning")]):
            c = ttk.Frame(cards, bootstyle=style_, padding=15)
            c.grid(row=0, column=i, padx=8)
            ttk.Label(c, text=titulo, font=("Arial", 12, "bold"),
                      bootstyle=f"inverse-{style_}").pack()
            ttk.Label(c, text=f"{cnt} ventas", font=("Arial", 11),
                      bootstyle=f"inverse-{style_}").pack()
            ttk.Label(c, text=f"${tot:,.0f}".replace(",", "."),
                      font=("Arial", 16, "bold"), bootstyle=f"inverse-{style_}").pack()

        ttk.Label(win, text="Últimas ventas (Selecciona una y presiona Ctrl+F12 para eliminarla):",
                  font=("Arial", 10, "italic")).pack(pady=10)

        tree = ttk.Treeview(win, columns=("ID", "Fecha", "Cliente", "Método", "Total", "Estado"),
                            show='headings', height=15)
        for c, t, w in [("ID","#",50),("Fecha","Fecha",150),("Cliente","Cliente",200),
                        ("Método","Método",120),("Total","Total",120),("Estado","Estado",100)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=10)

        sales = self.sale_use_case.get_all_sales(limit=300)
        for s_ in sales:
            estado = "✅ Pagado"
            if s_.is_credit:
                estado = "💳 Fiado" if not s_.is_paid else "✅ Fiado pagado"
            tree.insert("", "end", values=(
                s_.sale_id, s_.date,
                s_.customer_name or "-", s_.payment_method,
                f"${s_.total:,.0f}".replace(",", "."), estado))

        def on_ctrl_f12(event=None):
            sel = tree.selection()
            if not sel:
                Messagebox.show_warning("Selecciona una venta primero.", "Sin selección", parent=win); return
            vals = tree.item(sel[0], 'values')
            sid = int(vals[0])
            # Confirmación
            if Messagebox.yesno(f"⚠️ ¿Eliminar la venta #{sid}?\n\nEsto restaurará el stock.",
                                "Confirmar eliminación", parent=win) != "Yes":
                return
            # Pedir contraseña 1234
            pw = self._ask_password_1234(win)
            if not pw: return
            self.sale_use_case.delete_sale(sid)
            Messagebox.show_info(f"Venta #{sid} eliminada y stock restaurado.", "OK", parent=win)
            win.destroy()
            self.show_sales_summary()
            self.current_page = "ventas_window"

        win.bind("<Control-F12>", on_ctrl_f12)
        win.bind("<Control-F12>", on_ctrl_f12)  # por si acaso
        # También desde el árbol
        tree.bind("<Control-F12>", on_ctrl_f12)

        win.after(100, lambda: center_window(win))
        win.after(200, lambda: apply_titlebar_theme(win, self.current_theme == 'darkly'))

    def _ask_password_1234(self, parent):
        pop = Toplevel(parent); pop.title("Contraseña requerida")
        pop.geometry("340x200"); pop.transient(parent); pop.grab_set()
        ttk.Label(pop, text="🔒 Contraseña de administrador:",
                  font=("Arial", 12, "bold")).pack(pady=20)
        v = tk.StringVar()
        e = ttk.Entry(pop, textvariable=v, show="•", width=20, font=("Arial", 14), justify="center")
        e.pack(pady=5); e.focus_set()
        ok = {"v": False}
        def ver():
            if v.get() == "1234":
                ok["v"] = True; pop.destroy()
            else:
                Messagebox.show_error("Contraseña incorrecta", "Error", parent=pop); v.set("")
        ttk.Button(pop, text="Aceptar", command=ver, bootstyle="success").pack(pady=15)
        e.bind("<Return>", lambda e: ver())
        pop.after(100, lambda: center_window(pop))
        parent.wait_window(pop)
        return ok["v"]

    def _close_sales_win(self, win):
        self.current_page = None
        win.destroy()

    def show_credit_sales(self):
        win = Toplevel(self); win.title("Fiados - Cuentas por cobrar")
        win.geometry("900x600"); win.transient(self); win.grab_set()

        ttk.Label(win, text="💳 CUENTAS POR COBRAR (FIADOS)",
                  font=("Arial", 18, "bold")).pack(pady=15)

        tree = ttk.Treeview(win, columns=("ID", "Fecha", "Cliente", "Total", "Estado"),
                            show='headings', height=15)
        for c, t, w in [("ID","#",50),("Fecha","Fecha",150),("Cliente","Cliente",250),
                        ("Total","Total",120),("Estado","Estado",120)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=10)

        def recargar():
            for r in tree.get_children(): tree.delete(r)
            for s_ in self.sale_use_case.get_credit_sales(only_unpaid=True):
                tree.insert("", "end", values=(
                    s_.sale_id, s_.date, s_.customer_name or "-",
                    f"${s_.total:,.0f}".replace(",", "."),
                    "💳 Pendiente" if not s_.is_paid else "✅ Pagado"))
        recargar()

        def marcar_pagado():
            sel = tree.selection()
            if not sel: return
            sid = int(tree.item(sel[0], 'values')[0])
            if Messagebox.yesno(f"¿Marcar la venta #{sid} como PAGADA?",
                                "Confirmar", parent=win) == "Yes":
                self.sale_use_case.mark_as_paid(sid)
                recargar()
                Messagebox.show_info("Marcada como pagada.", "OK", parent=win)

        ttk.Button(win, text="✅ Marcar como pagada", command=marcar_pagado,
                   bootstyle="success").pack(pady=10)
        win.after(100, lambda: center_window(win))
        win.after(200, lambda: apply_titlebar_theme(win, self.current_theme == 'darkly'))

    # =========== AUTO-INICIO ===========
    def _get_startup_bat_path(self):
        startup = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu',
                               'Programs', 'Startup')
        return os.path.join(startup, 'MiniPOS_Portable.bat')

    def _is_autostart_enabled(self):
        return os.path.exists(self._get_startup_bat_path())

    def toggle_autostart(self):
        bat = self._get_startup_bat_path()
        if self.autostart_var.get():
            try:
                with open(bat, 'w', encoding='utf-8') as f:
                    f.write(f'@echo off\nstart "" "{sys.executable}"\n')
                Messagebox.show_info("✅ Auto-inicio ACTIVADO.", "Auto-inicio", parent=self)
            except Exception as e:
                self.autostart_var.set(False)
                Messagebox.show_error(f"Error: {e}", "Error", parent=self)
        else:
            try:
                if os.path.exists(bat): os.remove(bat)
                Messagebox.show_info("❌ Auto-inicio DESACTIVADO.", "Auto-inicio", parent=self)
            except Exception as e:
                self.autostart_var.set(True)
                Messagebox.show_error(f"Error: {e}", "Error", parent=self)

    # =========== REPORTES ===========
    def generate_daily_report(self):
        hoy = datetime.now().strftime("%Y-%m-%d")
        sales = self.sale_use_case.get_sales_by_day(hoy)
        if not sales:
            Messagebox.show_info("No hay ventas hoy.", "Reporte vacío", parent=self); return
        arch = filedialog.asksaveasfilename(defaultextension=".txt",
                                            initialfile=f"ventas_{hoy}.txt",
                                            filetypes=[("Texto", "*.txt")])
        if not arch: return
        total_dia = sum(s.total for s in sales)
        total_prod = sum(i.quantity for s in sales for i in s.items)
        L = ["=" * 60, "      REPORTE DE VENTAS DEL DÍA", f"      Fecha: {hoy}",
             f"      Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", "=" * 60, ""]
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
            with open(arch, "w", encoding="utf-8") as f: f.write("\n".join(L))
            Messagebox.show_info(f"Guardado:\n{arch}", "OK", parent=self)
        except Exception as e:
            Messagebox.show_error(f"Error: {e}", "Error", parent=self)

    def generate_monthly_report(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
        except ImportError:
            Messagebox.show_error("Falta openpyxl.", "Error", parent=self); return
        ym = datetime.now().strftime("%Y-%m")
        sales = self.sale_use_case.get_sales_by_month(ym)
        if not sales:
            Messagebox.show_info("No hay ventas este mes.", "Reporte vacío", parent=self); return
        arch = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            initialfile=f"ventas_{ym}.xlsx",
                                            filetypes=[("Excel", "*.xlsx")])
        if not arch: return
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = f"Ventas {ym}"
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
        ws.append([]); ws.append(["", "", "", "", "", "", "", "", "", "TOTAL:", total])
        for col, w in zip("ABCDEFGHIJK", [20, 10, 25, 15, 10, 30, 20, 10, 10, 12, 12]):
            ws.column_dimensions[col].width = w
        try:
            wb.save(arch)
            Messagebox.show_info(f"Guardado:\n{arch}", "OK", parent=self)
        except Exception as e:
            Messagebox.show_error(f"Error: {e}", "Error", parent=self)

    # =========== EXPORTAR / IMPORTAR ===========
    def export_db(self):
        arch = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db")])
        if arch:
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, arch)
            Messagebox.show_info("Base de datos exportada.", "OK", parent=self)

    def import_db(self):
        arch = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if arch and Messagebox.yesno("¿Reemplazar datos?", "Confirmar", parent=self) == "Yes":
            self.db_manager.close_connection()
            shutil.copy2(arch, self.db_path)
            self.inventory_view.load_products()
            Messagebox.show_info("Importada.", "OK", parent=self)