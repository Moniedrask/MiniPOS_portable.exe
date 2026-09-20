# src/presentation/views/main_view.py
import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap import Style
import os
from application.use_case.product_use_case import ProductCase
from infrastucture.db.db_manager import DBManager

class MainView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MiniPOS Portable")
        self.geometry("750x550")
        
        # Variable para controlar el tema actual
        self.current_theme = 'darkly'
        self.style = Style(theme=self.current_theme)

        # Obtener ruta absoluta de la base de datos
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.normpath(os.path.join(base_dir, "..", "..", "..", "data", "ventas.db"))

        # Crear carpeta data si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db_manager = DBManager(db_path)
        self.product_use_case = ProductCase(self.db_manager)

        self.create_widgets()
        self.load_products()

    def create_widgets(self):
        # Frame principal para la tabla
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Instrucción para el usuario
        lbl_instruccion = ttk.Label(self, text="💡 Haz doble clic sobre un producto para editarlo", font=("Arial", 9, "italic"))
        lbl_instruccion.pack(pady=2)

        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Price", "Stock"), show='headings')
        self.tree.heading("ID", text="ID / QR")
        self.tree.heading("Name", text="Producto")
        self.tree.heading("Price", text="Precio")
        self.tree.heading("Stock", text="Stock")
        self.tree.pack(fill="both", expand=True)

        # Vincular doble clic a la función de edición
        self.tree.bind("<Double-1>", self.edit_product_popup)

        # Frame para botones inferiores
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        add_button = ttk.Button(btn_frame, text="➕ Agregar Producto", command=self.add_product_popup)
        add_button.pack(side="left", padx=5)

        theme_button = ttk.Button(btn_frame, text="🌓 Cambiar Tema", command=self.toggle_theme)
        theme_button.pack(side="left", padx=5)

    def toggle_theme(self):
        """Cambia entre modo oscuro y claro"""
        if self.current_theme == 'darkly':
            self.current_theme = 'flatly' # Modo claro
        else:
            self.current_theme = 'darkly' # Modo oscuro
        self.style.theme_use(self.current_theme)

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        products = self.product_use_case.list_products()
        for product in products:
            # Formato Colombia: $10.000 (sin decimales y con puntos de miles)
            precio_formateado = f"${product.price:,.0f}".replace(",", ".")
            self.tree.insert("", "end", values=(product.product_id, product.name, precio_formateado, product.stock))

    def add_product_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Agregar Producto")
        popup.geometry("320x320")
        popup.transient(self) # Mantener la ventana al frente
        popup.grab_set() # Bloquear la ventana principal mientras se edita

        ttk.Label(popup, text="Nombre / Código QR:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30)
        name_entry.pack(pady=5)

        ttk.Label(popup, text="Precio (ej. 15000):").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30)
        price_entry.pack(pady=5)

        ttk.Label(popup, text="Stock (Opcional, deje vacío para 0):").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30)
        stock_entry.pack(pady=5)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "El nombre es obligatorio", parent=popup)
                return
            
            try:
                # Limpiar el precio por si el usuario escribe puntos o $
                precio_limpio = price_entry.get().replace("$", "").replace(".", "").strip()
                price = float(precio_limpio) if precio_limpio else 0.0
                
                # Stock opcional: si está vacío, se guarda como 0
                stock_str = stock_entry.get().strip()
                stock = int(stock_str) if stock_str else 0
                
            except ValueError:
                messagebox.showerror("Error", "Precio debe ser un número válido y Stock un número entero", parent=popup)
                return

            self.product_use_case.add_product(name, price, stock)
            self.load_products()
            popup.destroy()

        save_btn = ttk.Button(popup, text="Guardar", command=save)
        save_btn.pack(pady=15)

    def edit_product_popup(self, event):
        """Abre una ventana para editar el producto seleccionado con doble clic"""
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        # Obtener los valores de la fila seleccionada
        item_values = self.tree.item(selected_item[0], 'values')
        product_id = item_values[0]
        name = item_values[1]
        
        # Limpiar el precio formateado ("$10.000" -> 10000)
        price_str = item_values[2].replace("$", "").replace(".", "").strip()
        price = float(price_str) if price_str else 0.0
        stock = int(item_values[3])

        # Crear ventana de edición
        popup = tk.Toplevel(self)
        popup.title("Editar Producto")
        popup.geometry("320x350")
        popup.transient(self)
        popup.grab_set()

        # Rellenar campos con los datos actuales
        ttk.Label(popup, text="ID / Código QR (No editable):").pack(pady=5)
        id_label = ttk.Label(popup, text=str(product_id), font=("Arial", 10, "bold"))
        id_label.pack(pady=2)

        ttk.Label(popup, text="Nombre / Código QR:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30)
        name_entry.insert(0, name)
        name_entry.pack(pady=5)

        ttk.Label(popup, text="Precio:").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30)
        price_entry.insert(0, str(int(price))) # Mostrar sin decimales
        price_entry.pack(pady=5)

        ttk.Label(popup, text="Stock:").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30)
        stock_entry.insert(0, str(stock))
        stock_entry.pack(pady=5)

        def update():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showerror("Error", "El nombre es obligatorio", parent=popup)
                return
            
            try:
                # Limpiar precio y stock
                precio_limpio = price_entry.get().replace("$", "").replace(".", "").strip()
                new_price = float(precio_limpio) if precio_limpio else 0.0
                
                stock_str = stock_entry.get().strip()
                new_stock = int(stock_str) if stock_str else 0
                
            except ValueError:
                messagebox.showerror("Error", "Precio debe ser un número y Stock un entero", parent=popup)
                return

            # ⚠️ IMPORTANTE: Esta función debe existir en tu ProductCase
            self.product_use_case.update_product(product_id, new_name, new_price, new_stock)
            self.load_products()
            popup.destroy()

        update_btn = ttk.Button(popup, text="Actualizar", command=update)
        update_btn.pack(pady=15)

        # Botón para eliminar (opcional, por si acaso)
        def delete():
            if messagebox.askyesno("Confirmar", "¿Estás seguro de eliminar este producto?", parent=popup):
                # ⚠️ IMPORTANTE: Esta función debe existir en tu ProductCase
                self.product_use_case.delete_product(product_id)
                self.load_products()
                popup.destroy()

        delete_btn = ttk.Button(popup, text="🗑 Eliminar Producto", command=delete, bootstyle="danger")
        delete_btn.pack(pady=5)

            # Validar Stock (Opcional)
            stock_str = stock_entry.get().strip()
            if stock_str:
                try:
                    stock = int(stock_str)
                except ValueError:
                    tk.messagebox.showerror("Error", "El stock debe ser un número entero válido o dejarse en blanco")
                    return
            else:
                stock = 0  # Si se deja en blanco, se guardará como 0

            self.product_use_case.add_product(name, price, stock)
            self.load_products()
            popup.destroy()

        save_btn = ttk.Button(popup, text="Guardar", command=save)
        save_btn.pack(pady=10)
