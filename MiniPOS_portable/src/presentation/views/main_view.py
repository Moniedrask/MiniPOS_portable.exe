import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap import Style
from ttkbootstrap.dialogs import Messagebox
import os, shutil, sys
from datetime import datetime
from application.use_case.product_use_case import ProductCase
from application.use_case.sale_use_case import SaleCase
from infrastucture.db.db_manager import DBManager
from presentation.views.payment_view import PaymentView
from presentation.views.inventory_view import InventoryView


def apply_titlebar_theme(window, is_dark):
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1 if is_dark else 0)
        for attr in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


class MainView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MiniPOS Portable v2.0")
        # ✅ Iniciar maximizada
        try:
            self.state('zoomed')
        except Exception:
            self.geometry("1400x900")

        self.current_theme = 'darkly'
        self.style = Style(theme=self.current_theme)
        self.configure(bg=self.style.colors.bg)
        self.is_fullscreen = False

        # Ruta portable
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.db_path = os.path.join(base_dir, "data", "ventas.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.db_manager = DBManager(self.db_path)
        self.product_use_case = ProductCase(self.db_manager)
        self.sale_use_case = SaleCase(self.db_manager)

        self.create_widgets()
        self.show_page("pagos")

        self.bind('<F2>', lambda e: self.inventory_view.add_product_popup() if self.current_page == "inventario" else None)
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.after(200, lambda: apply_titlebar_theme(self, self.current_theme == 'darkly'))

    def create_widgets(self):
        # --- MENÚ SUPERIOR ---
        menubar = tk.Menu(self, bg=self.style.colors.bg, fg=self.style.colors.fg,
                          activebackground=self.style.colors.selectbg,
                          activeforeground=self.style.colors.selectfg, bd=0)
        options_menu = tk.Menu(menubar, tearoff=0, bg=self.style.colors.bg, fg=self.style.colors.fg,
                               activebackground=self.style.colors.selectbg,
                               activeforeground=self.style.colors.selectfg)
        options_menu.add_command(label="🌓 Cambiar Tema", command=self.toggle_theme)
        options_menu.add_separator()
        self.autostart_var = tk.BooleanVar(value=self._is_autostart_enabled())
        options_menu.add_checkbutton(label="🚀 Iniciar con Windows", variable=self.autostart_var,
                                     command=self.toggle_autostart)
        options_menu.add_separator()
        options_menu.add_command(label="📄 Reporte del Día (TXT)", command=self.generate_daily_report)
        options_menu.add_command(label="📊 Reporte del Mes (Excel)", command=self.generate_monthly_report)
        options_menu.add_separator()
        options_menu.add_command(label="📤 Exportar Base de Datos", command=self.export_db)
        options_menu.add_command(label="📥 Importar Base de Datos", command=self.import_db)
        menubar.add_cascade(label="Opciones", menu=options_menu)
        self.config(menu=menubar)

        # --- BARRA DE PESTAÑAS ---
        tabs = ttk.Frame(self, bootstyle="dark")
        tabs.pack(fill="x", padx=10, pady=(10, 0))

        self.btn_pagos = ttk.Button(tabs, text="🛒  PAGOS", bootstyle="success",
                                    command=lambda: self.show_page("pagos"), width=20)
        self.btn_pagos.pack(side="left", padx=3, pady=3, ipady=8)

        self.btn_inv = ttk.Button(tabs, text="📦  INVENTARIO", bootstyle="secondary",
                                  command=lambda: self.show_page("inventario"), width=20)
        self.btn_inv.pack(side="left", padx=3, pady=3, ipady=8)

        # Atajos
        self.bind('<Control-Key-1>', lambda e: self.show_page("pagos"))
        self.bind('<Control-Key-2>', lambda e: self.show_page("inventario"))

        # --- CONTENEDOR DE PÁGINAS ---
        self.container = ttk.Frame(self, bootstyle="dark")
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        self.payment_view = PaymentView(self.container, self.product_use_case,
                                        self.sale_use_case, lambda: self.current_theme)
        self.inventory_view = InventoryView(self.container, self.product_use_case,
                                            lambda: self.current_theme)

        self.current_page = None

    def show_page(self, page):
        # Ocultar todas
        for w in (self.payment_view, self.inventory_view):
            w.pack_forget()

        if page == "pagos":
            self.payment_view.pack(fill="both", expand=True)
            self.btn_pagos.configure(bootstyle="success")
            self.btn_inv.configure(bootstyle="secondary")
            self.current_page = "pagos"
        else:
            self.inventory_view.load_products()
            self.inventory_view.pack(fill="both", expand=True)
            self.btn_pagos.configure(bootstyle="secondary")
            self.btn_inv.configure(bootstyle="success")
            self.current_page = "inventario"

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)

    def toggle_theme(self):
        self.current_theme = 'flatly' if self.current_theme == 'darkly' else 'darkly'
        self.style.theme_use(self.current_theme)
        self.configure(bg=self.style.colors.bg)
        apply_titlebar_theme(self, self.current_theme == 'darkly')

    # ============ AUTO-INICIO ============
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

    # ============ REPORTES ============
    def generate_daily_report(self):
        hoy = datetime.now().strftime("%Y-%m-%d")
        sales = self.sale_use_case.get_sales_by_day(hoy)
        if not sales:
            Messagebox.show_info("No hay ventas hoy.", "Reporte vacío", parent=self); return
        archivo = filedialog.asksaveasfilename(defaultextension=".txt",
                                               initialfile=f"ventas_{hoy}.txt",
                                               filetypes=[("Texto", "*.txt")])
        if not archivo: return
        total_dia = sum(s.total for s in sales)
        total_prod = sum(i.quantity for s in sales for i in s.items)
        L = []
        L.append("=" * 60)
        L.append("      REPORTE DE VENTAS DEL DÍA")
        L.append(f"      Fecha: {hoy}")
        L.append(f"      Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        L.append("=" * 60); L.append("")
        for s in sales:
            hora = s.date.split(" ")[1] if " " in s.date else ""
            L.append(f"Venta #{s.sale_id}  -  {hora}  -  {s.payment_method}")
            L.append(f"  {'Cant.':>8}  {'Producto':<30} {'P.Unit':>10} {'Subtotal':>12}")
            L.append(f"  {'-'*8:>8}  {'-'*30:<30} {'-'*10:>10} {'-'*12:>12}")
            for it in s.items:
                L.append(f"  {it.quantity:>8g}  {it.product_name[:30]:<30} "
                         f"${it.unit_price:>9,.0f} ${it.subtotal:>11,.0f}".replace(",", "."))
            L.append(f"  {'':>8}  {'':<30} {'':>10} ${s.total:>11,.0f}".replace(",", "."))
            L.append("")
        L.append("=" * 60)
        L.append(f"TOTAL DEL DÍA:      ${total_dia:>12,.0f}".replace(",", "."))
        L.append(f"VENTAS REALIZADAS:  {len(sales)}")
        L.append(f"PRODUCTOS VENDIDOS: {total_prod:g}")
        L.append("=" * 60)
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                f.write("\n".join(L))
            Messagebox.show_info(f"Reporte guardado:\n{archivo}", "Éxito", parent=self)
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
        archivo = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                               initialfile=f"ventas_{ym}.xlsx",
                                               filetypes=[("Excel", "*.xlsx")])
        if not archivo: return
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = f"Ventas {ym}"
        headers = ["Fecha", "Venta #", "Método", "Producto", "Código", "Cantidad", "Unidad",
                   "P. Unit.", "Subtotal"]
        ws.append(headers)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="305496")
            c.alignment = Alignment(horizontal="center")
        for s in sales:
            for it in s.items:
                ws.append([s.date, s.sale_id, s.payment_method, it.product_name, it.barcode,
                           it.quantity, "unidad", it.unit_price, it.subtotal])
        total = sum(s.total for s in sales)
        ws.append([]); ws.append(["", "", "", "", "", "", "", "TOTAL:", total])
        for c in ws[ws.max_row]: c.font = Font(bold=True)
        for col, w in zip("ABCDEFGHI", [20, 10, 15, 30, 20, 10, 10, 12, 12]):
            ws.column_dimensions[col].width = w
        try:
            wb.save(archivo)
            Messagebox.show_info(f"Reporte guardado:\n{archivo}", "Éxito", parent=self)
        except Exception as e:
            Messagebox.show_error(f"Error: {e}", "Error", parent=self)

    # ============ EXPORTAR / IMPORTAR ============
    def export_db(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db")])
        if archivo:
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, archivo)
            Messagebox.show_info("Base de datos exportada.", "Éxito", parent=self)

    def import_db(self):
        archivo = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if archivo and Messagebox.yesno("¿Reemplazar datos actuales?", "Confirmar", parent=self) == "Yes":
            self.db_manager.close_connection()
            shutil.copy2(archivo, self.db_path)
            self.inventory_view.load_products()
            Messagebox.show_info("Base de datos importada.", "Éxito", parent=self)