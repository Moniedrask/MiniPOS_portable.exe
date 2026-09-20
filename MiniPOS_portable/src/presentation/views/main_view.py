# src/presentation/views/main_view.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ttkbootstrap import Style
import os
import shutil
import sys  # ✅ NUEVO: Necesario para detectar si es .exe o código fuente
from application.use_case.product_use_case import ProductCase
from infrastucture.db.db_manager import DBManager

class MainView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MiniPOS Portable")
        self.geometry("850x600")
        
        # Variable para controlar el tema actual
        self.current_theme = 'darkly'
        self.style = Style(theme=self.current_theme)

        # ✅ SOLUCIÓN: Detectar si estamos ejecutando el .exe o el código fuente
        if getattr(sys, 'frozen', False):
            # Si es el .exe compilado, guardar la base de datos junto al ejecutable
            base_dir = os.path.dirname(sys.executable)
        else:
            # Si es código fuente, guardar en la raíz del proyecto
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            
        self.db_path = os.path.join(base_dir, "data", "ventas.db")
        
        # Crear la carpeta data si no existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.db_manager = DBManager(self.db_path)
        self.product_use_case = ProductCase(self.db_manager)

        self.create_widgets()
        self.load_products()

    def create_widgets(self):
        # --- BARRA DE BÚSQUEDA ---
        search_frame = ttk.Frame(self)
        search_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(search_frame, text="🔍 Buscar Producto (Nombre o Código):").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_products) # Filtrar mientras escribe

        # --- FRAME PRINCIPAL PARA LA TABLA ---
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=5, fill="both", expand=True)

        lbl_instruccion = ttk.Label(self, text="💡 Haz doble clic sobre un producto para editarlo", font=("Arial", 9, "italic"))
        lbl_instruccion.pack(pady=2)

        # Agregamos la columna "Barcode" a la tabla
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Barcode", "Price", "Stock"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Producto")
        self.tree.heading("Barcode", text="Código de Barras / QR")
        self.tree.heading("Price", text="Precio")
        self.tree.heading("Stock", text="Stock")
        
        # Ajustar el ancho de las columnas
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=200)
        self.tree.column("Barcode", width=150)
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Stock", width=80, anchor="center")
        
        self.tree.pack(fill="both", expand=True)

        # Vincular doble clic a la función de edición
        self.tree.bind("<Double-1>", self.edit_product_popup)

        # --- FRAME PARA BOTONES INFERIORES ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        add_button = ttk.Button(btn_frame, text="➕ Agregar Producto", command=self.add_product_popup)
        add_button.pack(side="left", padx=5)

        theme_button = ttk.Button(btn_frame, text="🌓 Cambiar Tema", command=self.toggle_theme)
        theme_button.pack(side="left", padx=5)

        export_button = ttk.Button(btn_frame, text="📤 Exportar Base de Datos", command=self.export_db)
        export_button.pack(side="left", padx=5)

        import_button = ttk.Button(btn_frame, text="📥 Importar Base de Datos", command=self.import_db)
        import_button.pack(side="left", padx=5)

    def toggle_theme(self):
        """Cambia entre modo oscuro y claro"""
        if self.current_theme == 'darkly':
            self.current_theme = 'flatly'
        else:
            self.current_theme = 'darkly'
        self.style.theme_use(self.current_theme)

    def filter_products(self, event=None):
        """Filtra los productos en la tabla según lo que se escriba en la búsqueda"""
        query = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        products = self.product_use_case.list_products()
        for product in products:
            # Buscar coincidencia en Nombre o Código de Barras
            if query in str(product.name).lower() or query in str(product.barcode).lower():
                precio_formateado = f"${product.price:,.0f}".replace(",", ".")
                self.tree.insert("", "end", values=(product.product_id, product.name, product.barcode, precio_formateado, product.stock))

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        products = self.product_use_case.list_products()
        for product in products:
            precio_formateado = f"${product.price:,.0f}".replace(",", ".")
            # Insertar los valores incluyendo el código de barras
            self.tree.insert("", "end", values=(product.product_id, product.name, product.barcode, precio_formateado, product.stock))

    def add_product_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Agregar Producto")
        popup.geometry("350x400")
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
                messagebox.showerror("Error", "Precio debe ser un número válido y Stock un número entero", parent=popup)
                return

            self.product_use_case.add_product(name, barcode, price, stock)
            self.load_products()
            popup.destroy()

        save_btn = ttk.Button(popup, text="Guardar", command=save)
        save_btn.pack(pady=15)

    def edit_product_popup(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        item_values = self.tree.item(selected_item[0], 'values')
        product_id = item_values[0]
        name = item_values[1]
        barcode = item_values[2]
        
        price_str = item_values[3].replace("$", "").replace(".", "").strip()
        price = float(price_str) if price_str else 0.0
        stock = int(item_values[4])

        popup = tk.Toplevel(self)
        popup.title("Editar Producto")
        popup.geometry("350x420")
        popup.transient(self)
        popup.grab_set()

        ttk.Label(popup, text="ID (No editable):").pack(pady=5)
        id_label = ttk.Label(popup, text=str(product_id), font=("Arial", 10, "bold"))
        id_label.pack(pady=2)

        ttk.Label(popup, text="Nombre del Producto:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30)
        name_entry.insert(0, name)
        name_entry.pack(pady=5)

        ttk.Label(popup, text="Código de Barras / QR:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30)
        barcode_entry.insert(0, barcode)
        barcode_entry.pack(pady=5)

        ttk.Label(popup, text="Precio:").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30)
        price_entry.insert(0, str(int(price)))
        price_entry.pack(pady=5)

        ttk.Label(popup, text="Stock:").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30)
        stock_entry.insert(0, str(stock))
        stock_entry.pack(pady=5)

        def update():
            new_name = name_entry.get().strip()
            new_barcode = barcode_entry.get().strip()
            if not new_name:
                messagebox.showerror("Error", "El nombre es obligatorio", parent=popup)
                return
            
            try:
                precio_limpio = price_entry.get().replace("$", "").replace(".", "").strip()
                new_price = float(precio_limpio) if precio_limpio else 0.0
                
                stock_str = stock_entry.get().strip()
                new_stock = int(stock_str) if stock_str else 0
                
            except ValueError:
                messagebox.showerror("Error", "Precio debe ser un número y Stock un entero", parent=popup)
                return

            self.product_use_case.update_product(product_id, new_name, new_barcode, new_price, new_stock)
            self.load_products()
            popup.destroy()

        update_btn = ttk.Button(popup, text="Actualizar", command=update)
        update_btn.pack(pady=15)

        def delete():
            if messagebox.askyesno("Confirmar", "¿Estás seguro de eliminar este producto?", parent=popup):
                self.product_use_case.delete_product(product_id)
                self.load_products()
                popup.destroy()

        delete_btn = ttk.Button(popup, text="🗑 Eliminar Producto", command=delete, bootstyle="danger")
        delete_btn.pack(pady=5)

    # --- FUNCIONES DE EXPORTAR E IMPORTAR ---
    def export_db(self):
        """Copia la base de datos actual a un lugar seguro elegido por el usuario"""
        archivo_destino = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("Base de Datos SQLite", "*.db"), ("Todos los archivos", "*.*")],
            title="Guardar copia de seguridad de la Base de Datos"
        )
        if archivo_destino:
            try:
                # Cerrar conexiones antes de copiar para evitar bloqueos
                self.db_manager.close_connection() 
                shutil.copy2(self.db_path, archivo_destino)
                messagebox.showinfo("Éxito", "La base de datos ha sido exportada correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def import_db(self):
        """Reemplaza la base de datos actual con una copia de seguridad"""
        archivo_origen = filedialog.askopenfilename(
            filetypes=[("Base de Datos SQLite", "*.db"), ("Todos los archivos", "*.*")],
            title="Seleccionar copia de seguridad de la Base de Datos"
        )
        if archivo_origen:
            confirmacion = messagebox.askyesno("Confirmar", "¿Seguro que deseas importar esta base de datos? Se reemplazarán todos los datos actuales.", parent=self)
            if confirmacion:
                try:
                    self.db_manager.close_connection()
                    shutil.copy2(archivo_origen, self.db_path)
                    self.load_products()
                    messagebox.showinfo("Éxito", "Base de datos importada correctamente.")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo importar: {e}")
