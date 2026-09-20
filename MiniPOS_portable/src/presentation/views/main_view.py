# src/presentation/views/main_view.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ttkbootstrap import Style, Toplevel  # ✅ Importamos Toplevel de ttkbootstrap
import os, shutil, sys
from application.use_case.product_use_case import ProductCase
from infrastucture.db.db_manager import DBManager

class MainView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("INVENTARIO - MiniPOS Portable")
        self.geometry("900x650")
        
        self.current_theme = 'darkly'
        self.style = Style(theme=self.current_theme)

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.db_path = os.path.join(base_dir, "data", "ventas.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.db_manager = DBManager(self.db_path)
        self.product_use_case = ProductCase(self.db_manager)

        self.create_widgets()
        self.load_products()
        
        # ✅ Atajo F2 para Agregar Producto
        self.bind('<F2>', lambda event: self.add_product_popup())

    def create_widgets(self):
        # --- MENÚ SUPERIOR DE OPCIONES ---
        menubar = tk.Menu(self)
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="🌓 Cambiar Tema", command=self.toggle_theme)
        options_menu.add_separator()
        options_menu.add_command(label="📤 Exportar Base de Datos", command=self.export_db)
        options_menu.add_command(label="📥 Importar Base de Datos", command=self.import_db)
        menubar.add_cascade(label="Opciones", menu=options_menu)
        self.config(menu=menubar)

        # --- BARRA DE BÚSQUEDA ---
        search_frame = ttk.Frame(self)
        search_frame.pack(padx=10, pady=10, fill="x")
        ttk.Label(search_frame, text="🔍 Buscar Producto:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_products)

        # --- TABLA DE INVENTARIO ---
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Barcode", "Price", "Stock"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Producto")
        self.tree.heading("Barcode", text="Código de Barras / QR")
        self.tree.heading("Price", text="Precio")
        self.tree.heading("Stock", text="Stock")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=250)
        self.tree.column("Barcode", width=150)
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Stock", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.edit_product_popup)

        # --- BOTONES INFERIORES ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)", command=self.add_product_popup).pack(side="left", padx=5)

    def toggle_theme(self):
        if self.current_theme == 'darkly':
            self.current_theme = 'flatly'
        else:
            self.current_theme = 'darkly'
        self.style.theme_use(self.current_theme)

    def filter_products(self, event=None):
        query = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in self.product_use_case.list_products():
            if query in str(product.name).lower() or query in str(product.barcode).lower():
                precio = f"${product.price:,.0f}".replace(",", ".")
                self.tree.insert("", "end", values=(product.product_id, product.name, product.barcode, precio, product.stock))

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in self.product_use_case.list_products():
            precio = f"${product.price:,.0f}".replace(",", ".")
            self.tree.insert("", "end", values=(product.product_id, product.name, product.barcode, precio, product.stock))

    def add_product_popup(self):
        popup = Toplevel(self)  # ✅ Usamos Toplevel de ttkbootstrap
        popup.title("Agregar Producto")
        popup.geometry("350x450")
        popup.transient(self)
        popup.grab_set()

        ttk.Label(popup, text="Nombre del Producto:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30)
        name_entry.pack(pady=5)

        ttk.Label(popup, text="Código de Barras / QR (Opcional):").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30)
        barcode_entry.pack(pady=5)

        ttk.Label(popup, text="Precio (ej. 15000):").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30)
        price_entry.pack(pady=5)

        ttk.Label(popup, text="Stock (Opcional, deje vacío para 0):").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30)
        stock_entry.pack(pady=5)

        def save():
            name = name_entry.get().strip()
            barcode = barcode_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "El nombre es obligatorio", parent=popup)
                return
            try:
                precio_limpio = price_entry.get().replace("$", "").replace(".", "").strip()
                price = float(precio_limpio) if precio_limpio else 0.0
                stock_str = stock_entry.get().strip()
                stock = int(stock_str) if stock_str else 0
            except ValueError:
                messagebox.showerror("Error", "Precio y Stock deben ser números", parent=popup)
                return
            self.product_use_case.add_product(name, barcode, price, stock)
            self.load_products()
            popup.destroy()

        ttk.Button(popup, text="Guardar", command=save).pack(pady=15)

    def edit_product_popup(self, event):
        selected = self.tree.selection()
        if not selected: return
        vals = self.tree.item(selected[0], 'values')
        product_id, name, barcode = vals[0], vals[1], vals[2]
        price = float(vals[3].replace("$", "").replace(".", ""))
        stock = int(vals[4])

        popup = Toplevel(self)
        popup.title("Editar Producto")
        popup.geometry("350x480")
        popup.transient(self); popup.grab_set()

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
                messagebox.showerror("Error", "Datos inválidos", parent=popup); return
            self.product_use_case.update_product(product_id, new_name, new_barcode, new_price, new_stock)
            self.load_products(); popup.destroy()

        ttk.Button(popup, text="Actualizar", command=update).pack(pady=10)
        ttk.Button(popup, text="🗑 Eliminar", command=lambda: [self.product_use_case.delete_product(product_id), self.load_products(), popup.destroy()], bootstyle="danger").pack(pady=5)

    def export_db(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db")])
        if archivo:
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, archivo)
            messagebox.showinfo("Éxito", "Base de datos exportada.")

    def import_db(self):
        archivo = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if archivo and messagebox.askyesno("Confirmar", "¿Reemplazar datos actuales?"):
            self.db_manager.close_connection()
            shutil.copy2(archivo, self.db_path)
            self.load_products()
            messagebox.showinfo("Éxito", "Base de datos importada.")
