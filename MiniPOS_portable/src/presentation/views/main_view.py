# src/presentation/views/main_view.py
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap import Style, Toplevel
from ttkbootstrap.dialogs import Messagebox
import os, shutil, sys
from datetime import datetime
from application.use_case.product_use_case import ProductCase
from application.use_case.sale_use_case import SaleCase
from infrastucture.db.db_manager import DBManager
from presentation.views.payment_view import PaymentView


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
        self.title("INVENTARIO - MiniPOS Portable v2.0")
        self.geometry("950x680")

        self.current_theme = 'darkly'
        self.style = Style(theme=self.current_theme)
        self.configure(bg=self.style.colors.bg)

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
        self.load_products()

        self.bind('<F2>', lambda event: self.add_product_popup())
        self.bind('<F3>', lambda event: self.open_payments())
        self.after(200, lambda: apply_titlebar_theme(self, self.current_theme == 'darkly'))
        self.after(300, lambda: self.scan_entry.focus_set())

        self.popup_open = False
        self._keep_scanner_focused()

    def _keep_scanner_focused(self):
        if not self.popup_open:
            try:
                fw = self.focus_get()
                if fw != self.search_entry and not isinstance(fw, ttk.Entry):
                    self.scan_entry.focus_set()
            except Exception:
                pass
        self.after(800, self._keep_scanner_focused)

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

        # --- BARRA DE ESCANEO ---
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(10, 5), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear código aquí:", font=("Arial", 10, "bold"),
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var, width=35, font=("Arial", 11))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.lookup_barcode)
        ttk.Button(scan_frame, text="🔍 Buscar Código",
                   command=lambda: self.lookup_barcode(None)).pack(side="left", padx=5)

        # --- BÚSQUEDA MANUAL ---
        search_frame = ttk.Frame(self, bootstyle="dark")
        search_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(search_frame, text="🔍 Búsqueda manual:",
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_products)

        # --- TABLA DE INVENTARIO ---
        frame = ttk.Frame(self, bootstyle="dark")
        frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Barcode", "Price", "Stock"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Producto")
        self.tree.heading("Barcode", text="Código de Barras / QR")
        self.tree.heading("Price", text="Precio")
        self.tree.heading("Stock", text="Stock")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=280)
        self.tree.column("Barcode", width=180)
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Stock", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.view_product_popup)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # --- BOTONES INFERIORES ---
        btn_frame = ttk.Frame(self, bootstyle="dark")
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)",
                   command=self.add_product_popup).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🛒 PAGOS (F3)", bootstyle="success",
                   command=self.open_payments).pack(side="left", padx=5)

    # ================= ABRIR PAGOS =================
    def open_payments(self):
        self.popup_open = True
        pv = PaymentView(self, self.product_use_case, self.sale_use_case, self.current_theme)
        pv.bind("<Destroy>", lambda e: self._on_payments_closed())
        pv.protocol("WM_DELETE_WINDOW", lambda: self._close_payments(pv))

    def _close_payments(self, pv):
        self.popup_open = False
        pv.destroy()
        self.scan_entry.focus_set()

    def _on_payments_closed(self):
        self.popup_open = False
        self.load_products()
        self.scan_entry.focus_set()

    # ================= REPORTES =================
    def generate_daily_report(self):
        hoy = datetime.now().strftime("%Y-%m-%d")
        sales = self.sale_use_case.get_sales_by_day(hoy)
        if not sales:
            Messagebox.show_info("No hay ventas registradas hoy.", "Reporte vacío", parent=self)
            return
        archivo = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"ventas_{hoy}.txt",
            filetypes=[("Texto", "*.txt")]
        )
        if not archivo:
            return
        total_dia = sum(s.total for s in sales)
        total_productos = sum(i.quantity for s in sales for i in s.items)
        lineas = []
        lineas.append("=" * 60)
        lineas.append("      REPORTE DE VENTAS DEL DÍA")
        lineas.append(f"      Fecha: {hoy}")
        lineas.append(f"      Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        lineas.append("=" * 60)
        lineas.append("")
        for s in sales:
            hora = s.date.split(" ")[1] if " " in s.date else ""
            lineas.append(f"Venta #{s.sale_id}  -  {hora}  -  {s.payment_method}")
            lineas.append(f"  {'Cant.':>5}  {'Producto':<30} {'P.Unit':>10} {'Subtotal':>12}")
            lineas.append(f"  {'-----':>5}  {'-'*30:<30} {'-'*10:>10} {'-'*12:>12}")
            for it in s.items:
                lineas.append(f"  {it.quantity:>5}  {it.product_name[:30]:<30} "
                              f"${it.unit_price:>9,.0f} ${it.subtotal:>11,.0f}".replace(",", "."))
            lineas.append(f"  {'':>5}  {'':<30} {'':>10} ${s.total:>11,.0f}".replace(",", "."))
            lineas.append("")
        lineas.append("=" * 60)
        lineas.append(f"TOTAL DEL DÍA:      ${total_dia:>12,.0f}".replace(",", "."))
        lineas.append(f"VENTAS REALIZADAS:  {len(sales)}")
        lineas.append(f"PRODUCTOS VENDIDOS: {total_productos} unidades")
        lineas.append("=" * 60)
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                f.write("\n".join(lineas))
            Messagebox.show_info(f"Reporte guardado:\n{archivo}", "Éxito", parent=self)
        except Exception as e:
            Messagebox.show_error(f"No se pudo guardar: {e}", "Error", parent=self)
        self.scan_entry.focus_set()

    def generate_monthly_report(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
        except ImportError:
            Messagebox.show_error("Falta la librería openpyxl.", "Error", parent=self)
            return

        ym = datetime.now().strftime("%Y-%m")
        sales = self.sale_use_case.get_sales_by_month(ym)
        if not sales:
            Messagebox.show_info("No hay ventas registradas este mes.", "Reporte vacío", parent=self)
            return
        archivo = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=f"ventas_{ym}.xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not archivo:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Ventas {ym}"
        headers = ["Fecha", "Venta #", "Método", "Producto", "Código", "Cant.", "P. Unit.", "Subtotal"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="305496")
            cell.alignment = Alignment(horizontal="center")

        for s in sales:
            for it in s.items:
                ws.append([
                    s.date, s.sale_id, s.payment_method, it.product_name, it.barcode,
                    it.quantity, it.unit_price, it.subtotal
                ])

        # Fila de total
        total_mes = sum(s.total for s in sales)
        ws.append([])
        ws.append(["", "", "", "", "", "", "TOTAL DEL MES:", total_mes])
        for cell in ws[ws.max_row]:
            cell.font = Font(bold=True)

        # Anchos de columna
        for col, ancho in zip("ABCDEFGH", [20, 10, 15, 30, 20, 8, 12, 12]):
            ws.column_dimensions[col].width = ancho

        try:
            wb.save(archivo)
            Messagebox.show_info(f"Reporte guardado:\n{archivo}", "Éxito", parent=self)
        except Exception as e:
            Messagebox.show_error(f"No se pudo guardar: {e}", "Error", parent=self)
        self.scan_entry.focus_set()

    # ================= AUTO-INICIO =================
    def _get_startup_bat_path(self):
        startup = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu',
                               'Programs', 'Startup')
        return os.path.join(startup, 'MiniPOS_Portable.bat')

    def _is_autostart_enabled(self):
        return os.path.exists(self._get_startup_bat_path())

    def toggle_autostart(self):
        bat_path = self._get_startup_bat_path()
        if self.autostart_var.get():
            try:
                with open(bat_path, 'w', encoding='utf-8') as f:
                    f.write(f'@echo off\nstart "" "{sys.executable}"\n')
                Messagebox.show_info("✅ Auto-inicio ACTIVADO.", "Auto-inicio", parent=self)
            except Exception as e:
                self.autostart_var.set(False)
                Messagebox.show_error(f"No se pudo activar: {e}", "Error", parent=self)
        else:
            try:
                if os.path.exists(bat_path):
                    os.remove(bat_path)
                Messagebox.show_info("❌ Auto-inicio DESACTIVADO.", "Auto-inicio", parent=self)
            except Exception as e:
                self.autostart_var.set(True)
                Messagebox.show_error(f"No se pudo desactivar: {e}", "Error", parent=self)
        self.scan_entry.focus_set()

    # ================= MENÚ CONTEXTUAL =================
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        menu = tk.Menu(self, tearoff=0, bg=self.style.colors.bg, fg=self.style.colors.fg,
                       activebackground=self.style.colors.selectbg, activeforeground=self.style.colors.selectfg,
                       bd=1, relief="solid")
        menu.add_command(label="👁️  Ver detalle", command=lambda: self.view_product_popup(None))
        menu.add_command(label="✏️  Editar producto", command=lambda: self.open_edit_from_item(item))
        menu.add_separator()
        menu.add_command(label="🗑️  Eliminar producto", command=lambda: self.confirm_delete(item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ================= DETALLE =================
    def view_product_popup(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        vals = self.tree.item(selected[0], 'values')
        product_id, name, barcode, price, stock = vals[0], vals[1], vals[2], vals[3], vals[4]

        self.popup_open = True
        popup = Toplevel(self)
        popup.title("Detalle del Producto")
        popup.geometry("420x440")
        popup.transient(self); popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", lambda: self._close_popup(popup))

        header = ttk.Frame(popup, bootstyle="dark"); header.pack(fill="x", pady=10)
        ttk.Label(header, text="📋 DETALLE DEL PRODUCTO", font=("Arial", 12, "bold"),
                  bootstyle="inverse-dark").pack()
        info = ttk.Frame(popup, bootstyle="dark"); info.pack(fill="both", expand=True, padx=25, pady=15)
        for texto, fuente in [
            (f"ID: {product_id}", ("Arial", 10)),
            (f"Nombre: {name}", ("Arial", 12, "bold")),
            (f"Código de Barras: {barcode}", ("Arial", 10)),
            (f"Precio: {price}", ("Arial", 12, "bold")),
            (f"Stock: {stock}", ("Arial", 10)),
        ]:
            ttk.Label(info, text=texto, font=fuente, bootstyle="inverse-dark").pack(anchor="w", pady=4)

        ttk.Separator(popup, orient="horizontal").pack(fill="x", padx=20, pady=5)
        btn_frame = ttk.Frame(popup, bootstyle="dark"); btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="✏️ Editar",
                   command=lambda: [self._close_popup(popup), self.open_edit_from_item(selected[0])]).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=lambda: self._close_popup(popup)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🗑", command=lambda: [self._close_popup(popup), self.confirm_delete(selected[0])],
                   bootstyle="danger", width=3).pack(side="left", padx=15)
        popup.after(200, lambda: apply_titlebar_theme(popup, self.current_theme == 'darkly'))

    def _close_popup(self, popup):
        self.popup_open = False
        popup.destroy()
        self.scan_entry.focus_set()

    def confirm_delete(self, item):
        vals = self.tree.item(item, 'values')
        product_id, name = vals[0], vals[1]
        if Messagebox.yesno(f"⚠️ ¿ELIMINAR el producto?\n\n{name}",
                            "Confirmar", parent=self) != "Yes":
            self.scan_entry.focus_set(); return
        if Messagebox.yesno(f"🚨 ÚLTIMA ADVERTENCIA 🚨\n\n¿Realmente eliminar '{name}'?",
                            "Confirmación final", parent=self) != "Yes":
            self.scan_entry.focus_set(); return
        self.product_use_case.delete_product(product_id)
        self.load_products()
        Messagebox.show_info(f"'{name}' eliminado.", "Listo", parent=self)
        self.scan_entry.focus_set()

    def open_edit_from_item(self, item):
        vals = self.tree.item(item, 'values')
        product_id = vals[0]; name = vals[1]; barcode = vals[2]
        price = float(vals[3].replace("$", "").replace(".", ""))
        stock = int(vals[4])

        self.popup_open = True
        popup = Toplevel(self)
        popup.title("Editar Producto")
        popup.geometry("370x500")
        popup.transient(self); popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", lambda: self._close_popup(popup))

        ttk.Label(popup, text=f"ID: {product_id} (No editable)").pack(pady=5)
        ttk.Label(popup, text="Nombre:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30); name_entry.insert(0, name); name_entry.pack(pady=5)
        ttk.Label(popup, text="Código de Barras:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30); barcode_entry.insert(0, barcode); barcode_entry.pack(pady=5)
        ttk.Label(popup, text="Precio:").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30); price_entry.insert(0, str(int(price))); price_entry.pack(pady=5)
        ttk.Label(popup, text="Stock:").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30); stock_entry.insert(0, str(stock)); stock_entry.pack(pady=5)

        def update():
            try:
                new_name = name_entry.get().strip()
                new_barcode = barcode_entry.get().strip()
                new_price = float(price_entry.get().replace("$", "").replace(".", "") or 0)
                new_stock = int(stock_entry.get() or 0)
            except ValueError:
                Messagebox.show_error("Datos inválidos", "Error", parent=popup); return
            self.product_use_case.update_product(product_id, new_name, new_barcode, new_price, new_stock)
            self.load_products(); self._close_popup(popup)
        ttk.Button(popup, text="Actualizar", command=update).pack(pady=15)
        popup.after(200, lambda: apply_titlebar_theme(popup, self.current_theme == 'darkly'))

    # ================= ESCANEO =================
    def lookup_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        encontrado = None
        for p in self.product_use_case.list_products():
            if str(p.barcode).strip() == codigo:
                encontrado = p; break

        if encontrado:
            self.search_var.set("")
            self.load_products()
            for item in self.tree.get_children():
                if str(self.tree.item(item, 'values')[2]).strip() == codigo:
                    self.tree.selection_set(item); self.tree.focus(item); self.tree.see(item); break
            Messagebox.show_info(
                f"✅ {encontrado.name}\nPrecio: ${encontrado.price:,.0f}\nStock: {encontrado.stock}".replace(",", "."),
                "Producto Encontrado", parent=self)
            self.scan_var.set(""); self.scan_entry.focus_set()
        else:
            r = Messagebox.yesno(
                f"⚠️ El código '{codigo}' NO está registrado.\n\n¿Deseas agregarlo?",
                "Producto No Registrado", parent=self)
            self.scan_var.set("")
            if r == "Yes":
                self.add_product_popup(barcode_prefill=codigo, auto_select=True)
            else:
                self.scan_entry.focus_set()

    # ================= AGREGAR =================
    def add_product_popup(self, barcode_prefill="", auto_select=False):
        self.popup_open = True
        popup = Toplevel(self)
        popup.title("Agregar Producto")
        popup.geometry("370x500")
        popup.transient(self); popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", lambda: self._close_popup(popup))

        ttk.Label(popup, text="Código de Barras / QR:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30); barcode_entry.pack(pady=5)
        if barcode_prefill:
            barcode_entry.insert(0, barcode_prefill)
        ttk.Label(popup, text="Nombre del Producto:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30); name_entry.pack(pady=5)
        ttk.Label(popup, text="Precio (ej. 15000):").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30); price_entry.pack(pady=5)
        ttk.Label(popup, text="Stock (Opcional, vacío = 0):").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30); stock_entry.pack(pady=5)

        if barcode_prefill:
            name_entry.focus_set()
        else:
            barcode_entry.focus_set()

        def save():
            name = name_entry.get().strip()
            barcode = barcode_entry.get().strip()
            if not name:
                Messagebox.show_error("El nombre es obligatorio", "Error", parent=popup); return
            try:
                pl = price_entry.get().replace("$", "").replace(".", "").strip()
                price = float(pl) if pl else 0.0
                ss = stock_entry.get().strip()
                stock = int(ss) if ss else 0
            except ValueError:
                Messagebox.show_error("Precio y Stock deben ser números", "Error", parent=popup); return
            self.product_use_case.add_product(name, barcode, price, stock)
            self.load_products()
            self._close_popup(popup)
            if auto_select and barcode:
                for item in self.tree.get_children():
                    if str(self.tree.item(item, 'values')[2]).strip() == barcode:
                        self.tree.selection_set(item); self.tree.focus(item); self.tree.see(item); break

        ttk.Button(popup, text="Guardar", command=save).pack(pady=15)
        popup.after(200, lambda: apply_titlebar_theme(popup, self.current_theme == 'darkly'))

    # ================= UTILIDADES =================
    def toggle_theme(self):
        self.current_theme = 'flatly' if self.current_theme == 'darkly' else 'darkly'
        self.style.theme_use(self.current_theme)
        self.configure(bg=self.style.colors.bg)
        apply_titlebar_theme(self, self.current_theme == 'darkly')
        self.scan_entry.focus_set()

    def filter_products(self, event=None):
        q = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.product_use_case.list_products():
            if q in str(p.name).lower() or q in str(p.barcode).lower():
                precio = f"${p.price:,.0f}".replace(",", ".")
                self.tree.insert("", "end", values=(p.product_id, p.name, p.barcode, precio, p.stock))

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.product_use_case.list_products():
            precio = f"${p.price:,.0f}".replace(",", ".")
            self.tree.insert("", "end", values=(p.product_id, p.name, p.barcode, precio, p.stock))

    def export_db(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db")])
        if archivo:
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, archivo)
            Messagebox.show_info("Base de datos exportada.", "Éxito", parent=self)
        self.scan_entry.focus_set()

    def import_db(self):
        archivo = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if archivo and Messagebox.yesno("¿Reemplazar datos actuales?", "Confirmar", parent=self) == "Yes":
            self.db_manager.close_connection()
            shutil.copy2(archivo, self.db_path)
            self.load_products()
            Messagebox.show_info("Base de datos importada.", "Éxito", parent=self)
        self.scan_entry.focus_set()