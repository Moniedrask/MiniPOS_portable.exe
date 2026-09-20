import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from ttkbootstrap.dialogs import Messagebox
from datetime import datetime


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


class PaymentView(Toplevel):
    def __init__(self, parent, product_use_case, sale_use_case, current_theme='darkly'):
        super().__init__(parent)
        self.parent = parent
        self.product_use_case = product_use_case
        self.sale_use_case = sale_use_case
        self.current_theme = current_theme
        self.cart = []  # lista de dicts

        self.title("PAGOS - Punto de Venta")
        self.geometry("1000x700")
        self.transient(parent)
        self.configure(bg=parent.style.colors.bg)

        self.create_widgets()
        self.refresh_cart()
        self.after(200, lambda: apply_titlebar_theme(self, current_theme == 'darkly'))
        self.after(300, lambda: self.scan_entry.focus_set())

    def create_widgets(self):
        # --- BARRA DE ESCANEO ---
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=10, fill="x")
        ttk.Label(scan_frame, text="📷 Escanear producto:", font=("Arial", 12, "bold"),
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var, width=40, font=("Arial", 13))
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
        self.tree.heading("Qty", text="Cant.")
        self.tree.heading("Subtotal", text="Subtotal")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=280)
        self.tree.column("Barcode", width=140)
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Qty", width=60, anchor="center")
        self.tree.column("Subtotal", width=110, anchor="e")
        self.tree.pack(fill="both", expand=True)

        # --- TOTAL Y BOTONES ---
        bottom = ttk.Frame(self, bootstyle="dark")
        bottom.pack(fill="x", padx=10, pady=10)

        # Total a la izquierda
        total_frame = ttk.Frame(bottom, bootstyle="dark")
        total_frame.pack(side="left")
        ttk.Label(total_frame, text="TOTAL A PAGAR:", font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(anchor="w")
        self.total_label = ttk.Label(total_frame, text="$0", font=("Arial", 28, "bold"),
                                     bootstyle="inverse-success")
        self.total_label.pack(anchor="w")

        # Botones a la derecha
        btns = ttk.Frame(bottom, bootstyle="dark")
        btns.pack(side="right")
        ttk.Button(btns, text="➖ Restar cantidad", command=self.decrease_qty).grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        ttk.Button(btns, text="🗑 Quitar producto", command=self.remove_item).grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        ttk.Button(btns, text="🧹 Vaciar carrito", command=self.clear_cart).grid(row=0, column=2, padx=5, pady=3, sticky="ew")
        ttk.Button(btns, text="💰 COBRAR", command=self.pay, bootstyle="success").grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky="ew", ipady=8)
        ttk.Button(btns, text="❌ Cancelar venta", command=self.destroy, bootstyle="danger").grid(row=1, column=2, padx=5, pady=10, sticky="ew", ipady=8)

    # ================= LÓGICA DEL CARRITO =================
    def add_by_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        # Buscar producto
        encontrado = None
        for p in self.product_use_case.list_products():
            if str(p.barcode).strip() == codigo:
                encontrado = p
                break

        if not encontrado:
            Messagebox.show_warning(f"⚠️ El código '{codigo}' no está registrado en el inventario.",
                                    "Producto no encontrado", parent=self)
            self.scan_var.set("")
            self.scan_entry.focus_set()
            return

        # Si ya está en el carrito, aumentar cantidad
        for item in self.cart:
            if item["product_id"] == encontrado.product_id:
                item["quantity"] += 1
                item["subtotal"] = item["quantity"] * item["unit_price"]
                break
        else:
            self.cart.append({
                "product_id": encontrado.product_id,
                "product_name": encontrado.name,
                "barcode": encontrado.barcode,
                "unit_price": encontrado.price,
                "quantity": 1,
                "subtotal": encontrado.price,
            })

        self.scan_var.set("")
        self.refresh_cart()
        self.scan_entry.focus_set()

    def refresh_cart(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in self.cart:
            self.tree.insert("", "end", values=(
                item["product_id"],
                item["product_name"],
                item["barcode"],
                f"${item['unit_price']:,.0f}".replace(",", "."),
                item["quantity"],
                f"${item['subtotal']:,.0f}".replace(",", ".")
            ))
        total = sum(i["subtotal"] for i in self.cart)
        self.total_label.configure(text=f"${total:,.0f}".replace(",", "."))

    def decrease_qty(self):
        selected = self.tree.selection()
        if not selected:
            return
        vals = self.tree.item(selected[0], 'values')
        product_id = int(vals[0])
        for i, item in enumerate(self.cart):
            if item["product_id"] == product_id:
                item["quantity"] -= 1
                if item["quantity"] <= 0:
                    self.cart.pop(i)
                else:
                    item["subtotal"] = item["quantity"] * item["unit_price"]
                break
        self.refresh_cart()
        self.scan_entry.focus_set()

    def remove_item(self):
        selected = self.tree.selection()
        if not selected:
            return
        vals = self.tree.item(selected[0], 'values')
        product_id = int(vals[0])
        self.cart = [i for i in self.cart if i["product_id"] != product_id]
        self.refresh_cart()
        self.scan_entry.focus_set()

    def clear_cart(self):
        if not self.cart:
            return
        if Messagebox.yesno("¿Vaciar todo el carrito?", "Confirmar", parent=self) == "Yes":
            self.cart = []
            self.refresh_cart()
            self.scan_entry.focus_set()

    # ================= COBRAR =================
    def pay(self):
        if not self.cart:
            Messagebox.show_warning("El carrito está vacío.", "Nada que cobrar", parent=self)
            return

        total = sum(i["subtotal"] for i in self.cart)

        popup = Toplevel(self)
        popup.title("Confirmar Pago")
        popup.geometry("400x380")
        popup.transient(self)
        popup.grab_set()

        ttk.Label(popup, text="💰 CONFIRMAR PAGO", font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(popup, text=f"Total a pagar:  ${total:,.0f}".replace(",", "."),
                  font=("Arial", 16, "bold"), bootstyle="success").pack(pady=10)

        ttk.Label(popup, text="Método de pago:").pack(pady=5)
        metodo_var = tk.StringVar(value="Efectivo")
        metodos_frame = ttk.Frame(popup)
        metodos_frame.pack(pady=5)
        for m in ("Efectivo", "Transferencia", "Tarjeta", "Otro"):
            ttk.Radiobutton(metodos_frame, text=m, variable=metodo_var, value=m).pack(anchor="w")

        ttk.Label(popup, text="Notas (opcional):").pack(pady=5)
        notas_entry = ttk.Entry(popup, width=40)
        notas_entry.pack(pady=5)

        def confirmar():
            try:
                sale_id, total_final = self.sale_use_case.create_sale(
                    self.cart, payment_method=metodo_var.get(), notes=notas_entry.get().strip()
                )
                popup.destroy()
                Messagebox.show_info(
                    f"✅ Venta #{sale_id} registrada.\nTotal: ${total_final:,.0f}".replace(",", "."),
                    "Venta Exitosa", parent=self
                )
                # Refrescar inventario en la ventana principal
                if hasattr(self.parent, 'load_products'):
                    self.parent.load_products()
                self.cart = []
                self.refresh_cart()
                self.scan_entry.focus_set()
            except Exception as e:
                Messagebox.show_error(f"Error al registrar venta: {e}", "Error", parent=popup)

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="✅ Confirmar Pago", command=confirmar, bootstyle="success").pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Cancelar", command=popup.destroy).pack(side="left", padx=10)

        popup.after(200, lambda: apply_titlebar_theme(popup, self.current_theme == 'darkly'))