import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from ttkbootstrap.dialogs import Messagebox


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


class PaymentView(ttk.Frame):
    """Módulo de PAGOS (POS) como Frame embebido en la ventana principal."""

    def __init__(self, parent, product_use_case, sale_use_case, get_theme_func):
        super().__init__(parent, bootstyle="dark")
        self.product_use_case = product_use_case
        self.sale_use_case = sale_use_case
        self.get_theme = get_theme_func
        self.cart = []

        self.create_widgets()
        self.refresh_cart()
        self.after(300, lambda: self.scan_entry.focus_set())

    def create_widgets(self):
        # --- BARRA DE ESCANEO ---
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(15, 5), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear producto:",
                  font=("Arial", 14, "bold"), bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var, width=40, font=("Arial", 14))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.add_by_barcode)
        ttk.Button(scan_frame, text="🔍 Agregar", command=lambda: self.add_by_barcode(None)).pack(side="left", padx=5)

        # --- TABLA DEL CARRITO ---
        cart_frame = ttk.Frame(self, bootstyle="dark")
        cart_frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree = ttk.Treeview(cart_frame,
                                 columns=("ID", "Name", "Barcode", "Price", "Qty", "Subtotal"),
                                 show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Producto")
        self.tree.heading("Barcode", text="Código")
        self.tree.heading("Price", text="P. Unit.")
        self.tree.heading("Qty", text="Cantidad")
        self.tree.heading("Subtotal", text="Subtotal")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=300)
        self.tree.column("Barcode", width=150)
        self.tree.column("Price", width=110, anchor="e")
        self.tree.column("Qty", width=100, anchor="center")
        self.tree.column("Subtotal", width=120, anchor="e")
        self.tree.pack(fill="both", expand=True)

        # --- TOTAL Y BOTONES ---
        bottom = ttk.Frame(self, bootstyle="dark")
        bottom.pack(fill="x", padx=10, pady=10)

        total_frame = ttk.Frame(bottom, bootstyle="dark")
        total_frame.pack(side="left")
        ttk.Label(total_frame, text="TOTAL A PAGAR:", font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(anchor="w")
        self.total_label = ttk.Label(total_frame, text="$0", font=("Arial", 32, "bold"),
                                     bootstyle="inverse-success")
        self.total_label.pack(anchor="w")

        btns = ttk.Frame(bottom, bootstyle="dark")
        btns.pack(side="right")
        ttk.Button(btns, text="➖ Restar", command=self.decrease_qty).grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        ttk.Button(btns, text="🗑 Quitar", command=self.remove_item).grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        ttk.Button(btns, text="🧹 Vaciar", command=self.clear_cart).grid(row=0, column=2, padx=5, pady=3, sticky="ew")
        ttk.Button(btns, text="💰 COBRAR", command=self.pay, bootstyle="success").grid(
            row=1, column=0, columnspan=2, padx=5, pady=10, sticky="ew", ipady=12)
        ttk.Button(btns, text="❌ Cancelar", command=self.clear_cart, bootstyle="danger").grid(
            row=1, column=2, padx=5, pady=10, sticky="ew", ipady=12)

    def add_by_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        encontrado = None
        for p in self.product_use_case.list_products():
            if str(p.barcode).strip() == codigo:
                encontrado = p
                break

        if not encontrado:
            Messagebox.show_warning(f"⚠️ El código '{codigo}' no está registrado.",
                                    "Producto no encontrado", parent=self)
            self.scan_var.set(""); self.scan_entry.focus_set(); return

        # Si es por peso/volumen, preguntar cantidad
        if encontrado.unit_type in ("peso", "volumen"):
            self.ask_amount(encontrado)
        else:
            self.add_to_cart(encontrado, 1)
        self.scan_var.set(""); self.scan_entry.focus_set()

    def ask_amount(self, product):
        """Popup para ingresar peso/volumen del producto."""
        self.parent_popup = Toplevel(self)
        self.parent_popup.title(f"Cantidad - {product.name}")
        self.parent_popup.geometry("350x280")
        self.parent_popup.transient(self.winfo_toplevel())
        self.parent_popup.grab_set()

        theme = self.get_theme()
        ttk.Label(self.parent_popup, text=f"{product.name}",
                  font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(self.parent_popup, text=f"Precio: ${product.price:,.0f}/{product.unit}".replace(",", "."),
                  font=("Arial", 11)).pack(pady=5)
        ttk.Label(self.parent_popup, text=f"Ingrese la cantidad en {product.unit}:",
                  font=("Arial", 11)).pack(pady=10)

        entry_var = tk.StringVar(value="1")
        entry = ttk.Entry(self.parent_popup, textvariable=entry_var, width=15,
                          font=("Arial", 18), justify="center")
        entry.pack(pady=5)
        entry.select_range(0, tk.END)
        entry.focus_set()

        def aceptar():
            try:
                cant = float(entry_var.get().replace(",", "."))
                if cant <= 0:
                    raise ValueError
            except ValueError:
                Messagebox.show_error(f"Cantidad inválida", "Error", parent=self.parent_popup)
                return
            self.parent_popup.destroy()
            self.add_to_cart(product, cant)

        def cancelar():
            self.parent_popup.destroy()
            self.scan_entry.focus_set()

        btn_frame = ttk.Frame(self.parent_popup)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="Agregar", command=aceptar, bootstyle="success").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=cancelar).pack(side="left", padx=5)
        entry.bind("<Return>", lambda e: aceptar())
        self.parent_popup.after(200, lambda: apply_titlebar_theme(self.parent_popup, theme == 'darkly'))

    def add_to_cart(self, product, cantidad):
        """Agrega un producto al carrito (o suma cantidad si ya existe)."""
        for item in self.cart:
            if item["product_id"] == product.product_id:
                item["quantity"] += cantidad
                item["subtotal"] = item["quantity"] * item["unit_price"]
                self.refresh_cart()
                return
        self.cart.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "barcode": product.barcode,
            "unit": product.unit,
            "unit_price": product.price,
            "quantity": cantidad,
            "subtotal": cantidad * product.price,
        })
        self.refresh_cart()

    def refresh_cart(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in self.cart:
            qty_txt = f"{item['quantity']:g} {item['unit']}" if item["unit"] != "unidad" else f"{int(item['quantity'])}"
            self.tree.insert("", "end", values=(
                item["product_id"], item["product_name"], item["barcode"],
                f"${item['unit_price']:,.0f}".replace(",", "."),
                qty_txt,
                f"${item['subtotal']:,.0f}".replace(",", ".")))
        total = sum(i["subtotal"] for i in self.cart)
        self.total_label.configure(text=f"${total:,.0f}".replace(",", "."))

    def decrease_qty(self):
        sel = self.tree.selection()
        if not sel: return
        pid = int(self.tree.item(sel[0], 'values')[0])
        for i, item in enumerate(self.cart):
            if item["product_id"] == pid:
                # Para peso/volumen pedir cuánto restar (por simplicidad: restar de a 1)
                item["quantity"] -= 1 if item["unit"] == "unidad" else 0.1
                if item["quantity"] <= 0:
                    self.cart.pop(i)
                else:
                    item["subtotal"] = item["quantity"] * item["unit_price"]
                break
        self.refresh_cart(); self.scan_entry.focus_set()

    def remove_item(self):
        sel = self.tree.selection()
        if not sel: return
        pid = int(self.tree.item(sel[0], 'values')[0])
        self.cart = [i for i in self.cart if i["product_id"] != pid]
        self.refresh_cart(); self.scan_entry.focus_set()

    def clear_cart(self):
        if not self.cart: return
        if Messagebox.yesno("¿Vaciar el carrito?", "Confirmar", parent=self) == "Yes":
            self.cart = []; self.refresh_cart(); self.scan_entry.focus_set()

    def pay(self):
        if not self.cart:
            Messagebox.show_warning("El carrito está vacío.", "Nada que cobrar", parent=self); return
        total = sum(i["subtotal"] for i in self.cart)

        popup = Toplevel(self)
        popup.title("Confirmar Pago")
        popup.geometry("400x400")
        popup.transient(self.winfo_toplevel()); popup.grab_set()

        ttk.Label(popup, text="💰 CONFIRMAR PAGO", font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(popup, text=f"Total a pagar:  ${total:,.0f}".replace(",", "."),
                  font=("Arial", 18, "bold"), bootstyle="success").pack(pady=10)

        ttk.Label(popup, text="Método de pago:").pack(pady=5)
        metodo_var = tk.StringVar(value="Efectivo")
        mf = ttk.Frame(popup); mf.pack(pady=5)
        for m in ("Efectivo", "Transferencia", "Tarjeta", "Otro"):
            ttk.Radiobutton(mf, text=m, variable=metodo_var, value=m).pack(anchor="w")

        ttk.Label(popup, text="Notas (opcional):").pack(pady=5)
        notas_entry = ttk.Entry(popup, width=40); notas_entry.pack(pady=5)

        def confirmar():
            try:
                sale_id, total_final = self.sale_use_case.create_sale(
                    self.cart, payment_method=metodo_var.get(), notes=notas_entry.get().strip())
                popup.destroy()
                Messagebox.show_info(
                    f"✅ Venta #{sale_id} registrada.\nTotal: ${total_final:,.0f}".replace(",", "."),
                    "Venta Exitosa", parent=self)
                self.cart = []; self.refresh_cart()
                self.scan_entry.focus_set()
            except Exception as e:
                Messagebox.show_error(f"Error: {e}", "Error", parent=popup)

        bf = ttk.Frame(popup); bf.pack(pady=20)
        ttk.Button(bf, text="✅ Confirmar", command=confirmar, bootstyle="success").pack(side="left", padx=10)
        ttk.Button(bf, text="Cancelar", command=popup.destroy).pack(side="left", padx=10)
        popup.after(200, lambda: apply_titlebar_theme(popup, self.get_theme() == 'darkly'))