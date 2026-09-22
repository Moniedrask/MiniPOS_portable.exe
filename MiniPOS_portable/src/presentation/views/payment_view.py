import tkinter as tk
import os
import subprocess
from tkinter import ttk as _tkttk  # noqa
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from presentation.views.widgets import (
    apply_titlebar_theme, center_window, show_popup_smooth,
    get_menu_font, AutoCompleteEntry, MD, TreeviewTooltip,
    popup_is_open, make_scrolled_treeview, get_business_display_text,
)


class PaymentView(ttk.Frame):
    def __init__(self, parent, product_use_case, sale_use_case, db_manager,
                 get_theme_func, on_business_click=None):
        super().__init__(parent, bootstyle="dark")
        self.product_use_case = product_use_case
        self.sale_use_case = sale_use_case
        self.db_manager = db_manager
        self.get_theme = get_theme_func
        self.on_business_click = on_business_click
        self.cart = []
        self.tooltip = None
        self._draft_loaded = False
        self.last_ticket_path = None
        self.create_widgets()
        self.refresh_cart()
        self.after(300, lambda: self.scan_entry.focus_set())
        self.after(800, self._check_cart_draft)
        self._keep_scanner_focused()

    def _is_dark(self):
        return True

    def _keep_scanner_focused(self):
        try:
            if not popup_is_open():
                fw = self.focus_get()
                if fw is not None and not isinstance(fw, (ttk.Entry, tk.Entry, ttk.Combobox)):
                    try:
                        if fw.winfo_toplevel() is self.winfo_toplevel():
                            self.scan_entry.focus_set()
                    except Exception:
                        pass
        except Exception:
            pass
        self.after(700, self._keep_scanner_focused)

    def _check_cart_draft(self):
        if self._draft_loaded:
            return
        try:
            if not self.winfo_ismapped():
                self.after(500, self._check_cart_draft)
                return
        except Exception:
            pass
        self._draft_loaded = True
        try:
            items, updated = self.sale_use_case.load_cart_draft()
        except Exception:
            return
        if not items:
            return
        try:
            total = sum(i["quantity"] * i["unit_price"] for i in items)
            n = len(items)
            fecha = updated or "(sin fecha)"
            r = MD.yesno(
                f"🛒 Se encontró un carrito sin cobrar:\n\n"
                f"Productos: {n}\n"
                f"Total: ${total:,.0f}\n"
                f"Guardado: {fecha}\n\n"
                f"¿Deseas recuperarlo?".replace(",", "."),
                "Recuperar carrito", parent=self)
            if r == "Yes":
                self.cart = items
                self.refresh_cart()
                self.scan_entry.focus_set()
            else:
                self.sale_use_case.clear_cart_draft()
                self.cart = []
                self.refresh_cart()
        except Exception:
            pass

    def _save_cart_draft(self):
        try:
            if self.cart:
                self.sale_use_case.save_cart_draft(self.cart)
            else:
                self.sale_use_case.clear_cart_draft()
        except Exception:
            pass

    def create_widgets(self):
        top = ttk.Frame(self, bootstyle="dark")
        top.pack(padx=10, pady=(10, 5), fill="x")

        ttk.Label(top, text="📷 Escanear:", font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(top, textvariable=self.scan_var, width=22, font=("Arial", 14))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.add_by_barcode)

        ttk.Label(top, text="🔍 Buscar:", font=("Arial", 11),
                  bootstyle="inverse-dark").pack(side="left", padx=(15, 5))

        self.search_var = tk.StringVar()
        self.search_entry = AutoCompleteEntry(
            top,
            values_getter=self._get_product_labels,
            on_select=self.add_by_search_value,
            width=25,
            font=("Arial", 11))
        self.search_entry.configure(textvariable=self.search_var)
        self.search_entry.pack(side="left", padx=5)

        ttk.Button(top, text="Agregar", command=self.add_by_search,
                   style="DarkGreen.TButton").pack(side="left", padx=5)

        cart_frame = ttk.Frame(self, bootstyle="dark")
        cart_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.tree_frame, self.tree = make_scrolled_treeview(
            cart_frame,
            columns=("ID", "Name", "Barcode", "Price", "Qty", "Subtotal"),
            headings=[
                ("ID", "ID", 50, "center"),
                ("Name", "Producto", 300, "w"),
                ("Barcode", "Código", 150, "w"),
                ("Price", "P. Unit.", 110, "e"),
                ("Qty", "Cantidad", 110, "center"),
                ("Subtotal", "Subtotal", 120, "e"),
            ],
            bootstyle="dark")
        self.tree_frame.pack(fill="both", expand=True)
        self.tree.bind("<Button-3>", self._cart_context_menu)
        self.tooltip = TreeviewTooltip(self.tree, font_size=11)

        bottom = ttk.Frame(self, bootstyle="dark")
        bottom.pack(fill="x", padx=10, pady=10)
        tf = ttk.Frame(bottom, bootstyle="dark")
        tf.pack(side="left")
        ttk.Label(tf, text="TOTAL A PAGAR:", font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(anchor="w")
        self.total_label = ttk.Label(tf, text="$0", font=("Arial", 36, "bold"),
                                     background="#0a4d1f", foreground="#a8e6a8",
                                     anchor="center", padding=10)
        self.total_label.pack(anchor="w")

        bf = ttk.Frame(bottom, bootstyle="dark")
        bf.pack(side="right")
        ttk.Button(bf, text="🖨 Último Ticket", command=self.open_last_ticket,
                   bootstyle="info").pack(side="left", padx=5, ipady=15)
        ttk.Button(bf, text="💰 COBRAR (F12)", command=self.pay,
                   style="DarkGreen.TButton").pack(side="left", padx=5, ipady=15, ipadx=15)
        ttk.Button(bf, text="❌ Cancelar", command=self.clear_cart,
                   bootstyle="danger").pack(side="left", padx=5, ipady=15)

        # Atajo F12 para cobrar
        self.winfo_toplevel().bind('<F12>', lambda e: self.pay(), add="+")

    def _get_product_labels(self):
        vals = []
        for p in self.product_use_case.list_active_products():
            txt = f"{p.name}  |  {p.barcode}" if p.barcode else p.name
            vals.append(txt)
        return vals

    def _find_by_barcode(self, codigo):
        for p in self.product_use_case.list_active_products():
            if str(p.barcode).strip() == codigo:
                return p
        return None

    def add_by_search_value(self, value):
        self.after(10, lambda: self._do_add_by_search(value))

    def _do_add_by_search(self, value):
        q = value.split("|")[0].strip() if "|" in value else value
        q_lower = q.lower()
        enc = None
        for p in self.product_use_case.list_active_products():
            if str(p.barcode).strip() == q or p.name.lower() == q_lower:
                enc = p
                break
        if not enc:
            for p in self.product_use_case.list_active_products():
                if q_lower in p.name.lower():
                    enc = p
                    break
        if not enc:
            MD.show_warning(f"⚠️ No se encontró '{q}'.", "No encontrado", parent=self)
            return
        self.search_var.set("")
        if enc.unit_type in ("peso", "volumen"):
            self.ask_amount(enc)
        else:
            self.add_to_cart(enc, 1)
        self.scan_entry.focus_set()

    def add_by_search(self, event=None):
        raw = self.search_var.get().strip()
        if not raw:
            return
        self._do_add_by_search(raw)

    def _cart_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.tree.focus(row)
        pid = int(self.tree.item(row, 'values')[0])
        name = self.tree.item(row, 'values')[1]
        style = ttk.Style()
        m = tk.Menu(self, tearoff=0,
                    bg=style.colors.bg, fg=style.colors.fg,
                    activebackground=style.colors.selectbg,
                    activeforeground=style.colors.selectfg,
                    bd=1, relief="solid",
                    font=get_menu_font())
        m.add_command(label="➖ Quitar 1", command=lambda: self._confirm_remove_one(pid, name))
        m.add_command(label="🗑️  Quitar producto completo",
                      command=lambda: self._confirm_remove_all(pid, name))
        m.add_separator()
        m.add_command(label="🧹 Vaciar carrito", command=self.clear_cart)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _confirm_remove_one(self, pid, name):
        if MD.yesno(f"¿Quitar 1 de '{name}' del carrito?", "Confirmar", parent=self) == "Yes":
            for i, it in enumerate(self.cart):
                if it["product_id"] == pid:
                    it["quantity"] -= 1
                    if it["quantity"] <= 0:
                        self.cart.pop(i)
                    else:
                        it["subtotal"] = it["quantity"] * it["unit_price"]
                    break
            self.refresh_cart()
            self._save_cart_draft()
            self.scan_entry.focus_set()

    def _confirm_remove_all(self, pid, name):
        if MD.yesno(f"¿Quitar TODO '{name}' del carrito?", "Confirmar", parent=self) == "Yes":
            self.cart = [i for i in self.cart if i["product_id"] != pid]
            self.refresh_cart()
            self._save_cart_draft()
            self.scan_entry.focus_set()

    def add_by_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        enc = self._find_by_barcode(codigo)
        if not enc:
            MD.show_warning(f"⚠️ '{codigo}' no registrado.", "No encontrado", parent=self)
            self.scan_var.set("")
            self.scan_entry.focus_set()
            return
        self.scan_var.set("")
        self.scan_entry.focus_set()
        if enc.unit_type in ("peso", "volumen"):
            self.ask_amount(enc)
        else:
            self.add_to_cart(enc, 1)

    def ask_amount(self, product):
        pop = Toplevel(self)
        pop.title(f"Cantidad - {product.name}")
        pop.geometry("400x320")
        pop.transient(self.winfo_toplevel())
        pop.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(pop, text=product.name, font=("Arial", 16, "bold"),
                 bg=bg, fg=fg).pack(pady=12)
        tk.Label(pop, text=f"Precio: ${product.price:,.0f}/{product.unit}".replace(",", "."),
                 font=("Arial", 12), bg=bg, fg=fg).pack(pady=5)
        tk.Label(pop, text=f"Ingrese la cantidad en {product.unit}:",
                 font=("Arial", 11), bg=bg, fg=fg).pack(pady=10)
        v = tk.StringVar(value="1")
        e = ttk.Entry(pop, textvariable=v, width=15, font=("Arial", 20), justify="center")
        e.pack(pady=5)
        e.select_range(0, tk.END)
        e.focus_set()

        def ok(ev=None):
            try:
                c = float(v.get().replace(",", "."))
                if c <= 0:
                    raise ValueError
            except ValueError:
                MD.show_error("Cantidad inválida", "Error", parent=pop)
                return "break"
            pop.destroy()
            self.add_to_cart(product, c)
            self.scan_entry.focus_set()
            return "break"

        bf = tk.Frame(pop, bg=bg)
        bf.pack(pady=15)
        ttk.Button(bf, text="Agregar", command=ok, style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar",
                   command=lambda: [pop.destroy(), self.scan_entry.focus_set()]).pack(side="left", padx=5)
        e.bind("<Return>", ok)
        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

    def add_to_cart(self, product, cantidad):
        precio = product.rounded_price if product.rounded_price else product.price
        for it in self.cart:
            if it["product_id"] == product.product_id:
                it["quantity"] += cantidad
                it["subtotal"] = it["quantity"] * it["unit_price"]
                self.refresh_cart()
                self._save_cart_draft()
                return
        self.cart.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "barcode": product.barcode,
            "unit": product.unit,
            "unit_price": precio,
            "quantity": cantidad,
            "subtotal": cantidad * precio,
        })
        self.refresh_cart()
        self._save_cart_draft()

    def refresh_cart(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for it in self.cart:
            qt = f"{it['quantity']:g} {it['unit']}" if it["unit"] != "unidad" else f"{int(it['quantity'])}"
            self.tree.insert("", "end", values=(
                it["product_id"], it["product_name"], it["barcode"],
                f"${it['unit_price']:,.0f}".replace(",", "."), qt,
                f"${it['subtotal']:,.0f}".replace(",", ".")))
        tot = sum(i["subtotal"] for i in self.cart)
        self.total_label.configure(text=f"${tot:,.0f}".replace(",", "."))

    def clear_cart(self):
        if not self.cart:
            return
        if MD.yesno("¿Vaciar el carrito?", "Confirmar", parent=self) == "Yes":
            self.cart = []
            self.refresh_cart()
            self.sale_use_case.clear_cart_draft()
            self.scan_entry.focus_set()

    def open_last_ticket(self):
        if not self.last_ticket_path or not os.path.exists(self.last_ticket_path):
            MD.show_info("Aún no se ha generado ningún ticket en esta sesión.",
                         "Sin tickets", parent=self)
            return
        try:
            os.startfile(self.last_ticket_path)
        except Exception:
            try:
                subprocess.Popen(['explorer', '/select,', self.last_ticket_path])
            except Exception as e:
                MD.show_error(f"No se pudo abrir el ticket:\n{e}\n\nRuta: {self.last_ticket_path}",
                              "Error", parent=self)

    def pay(self):
        try:
            self._pay_internal()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                MD.show_error(f"Error al abrir el pago:\n{e}", "Error", parent=self)
            except Exception:
                pass

    def _pay_internal(self):
        if not self.cart:
            MD.show_warning("El carrito está vacío.", "Nada que cobrar", parent=self)
            return
        subtotal = sum(i["subtotal"] for i in self.cart)

        pop = Toplevel(self)
        pop.title("Confirmar Pago")
        pop.geometry("680x860")
        pop.transient(self.winfo_toplevel())
        pop.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        container = tk.Frame(pop, bg=bg)
        container.pack(fill="both", expand=True)

        refs = {}
        state = {"updating": False}

        def build_content(parent):
            # Encabezado negocio
            texto_negocio = get_business_display_text(self.db_manager)
            if texto_negocio:
                tk.Label(parent, text=texto_negocio,
                         font=("Arial", 11, "bold"),
                         bg=bg, fg="#7dd87d").pack(pady=(10, 2))

            tk.Label(parent, text="💰 CONFIRMAR PAGO",
                     font=("Arial", 15, "bold"), bg=bg, fg=fg).pack(pady=(2, 6))

            # Subtotal / Descuento / Total
            sub_frame = tk.Frame(parent, bg=bg)
            sub_frame.pack(pady=2)
            tk.Label(sub_frame, text="Subtotal:",
                     font=("Arial", 11), bg=bg, fg=fg).pack(side="left", padx=(0, 5))
            tk.Label(sub_frame, text=f"${subtotal:,.0f}".replace(",", "."),
                     font=("Arial", 12, "bold"), bg=bg, fg=fg).pack(side="left")

            # Descuento
            desc_frame = tk.Frame(parent, bg=bg)
            desc_frame.pack(pady=(2, 4))
            tk.Label(desc_frame, text="Descuento:",
                     font=("Arial", 10), bg=bg, fg=fg).pack(side="left", padx=(0, 5))
            desc_tipo_var = tk.StringVar(value="monto")
            ttk.Radiobutton(desc_frame, text="$", variable=desc_tipo_var,
                            value="monto", bootstyle="info").pack(side="left", padx=2)
            ttk.Radiobutton(desc_frame, text="%", variable=desc_tipo_var,
                            value="porcentaje", bootstyle="info").pack(side="left", padx=2)
            desc_var = tk.StringVar(value="0")
            ttk.Entry(desc_frame, textvariable=desc_var, width=10,
                      font=("Arial", 11), justify="center").pack(side="left", padx=5)

            # Total (verde)
            total_frame = tk.Frame(parent, bg="#0a4d1f", padx=20, pady=8)
            total_frame.pack(pady=(4, 8))
            tk.Label(total_frame, text="TOTAL A PAGAR",
                     font=("Arial", 9, "bold"),
                     bg="#0a4d1f", fg="#a8e6a8").pack()
            total_lbl = tk.Label(total_frame, text=f"${subtotal:,.0f}".replace(",", "."),
                                 font=("Arial", 24, "bold"),
                                 bg="#0a4d1f", fg="#a8e6a8")
            total_lbl.pack()

            # Nombre cliente
            tk.Label(parent, text="Nombre del cliente:",
                     font=("Arial", 10), bg=bg, fg=fg).pack(pady=(2, 2))
            nombre_var = tk.StringVar()
            ttk.Entry(parent, textvariable=nombre_var, width=40,
                      font=("Arial", 11)).pack(pady=3, padx=20)

            # Deuda previa label
            deuda_lbl = tk.Label(parent, text="", font=("Arial", 10, "bold"),
                                 bg=bg, fg="#ffd166", wraplength=600, justify="center")
            deuda_lbl.pack(pady=4, padx=10)

            # === MÉTODOS DE PAGO ===
            tk.Label(parent, text="Métodos de pago (deja en blanco los que no uses):",
                     font=("Arial", 10, "bold"), bg=bg, fg=fg).pack(pady=(8, 3))

            metodos_frame = tk.Frame(parent, bg=bg)
            metodos_frame.pack(pady=2)

            # Efectivo
            tk.Label(metodos_frame, text="💵 Efectivo:",
                     font=("Arial", 10), bg=bg, fg=fg).grid(row=0, column=0, padx=5, pady=2, sticky="e")
            ef_var = tk.StringVar(value="")
            ttk.Entry(metodos_frame, textvariable=ef_var, width=12,
                      font=("Arial", 11), justify="center").grid(row=0, column=1, padx=5, pady=2)

            # Transferencia
            tk.Label(metodos_frame, text="🏦 Transferencia:",
                     font=("Arial", 10), bg=bg, fg=fg).grid(row=1, column=0, padx=5, pady=2, sticky="e")
            tr_var = tk.StringVar(value="")
            ttk.Entry(metodos_frame, textvariable=tr_var, width=12,
                      font=("Arial", 11), justify="center").grid(row=1, column=1, padx=5, pady=2)

            # Tarjeta
            tk.Label(metodos_frame, text="💳 Tarjeta:",
                     font=("Arial", 10), bg=bg, fg=fg).grid(row=2, column=0, padx=5, pady=2, sticky="e")
            ta_var = tk.StringVar(value="")
            ttk.Entry(metodos_frame, textvariable=ta_var, width=12,
                      font=("Arial", 11), justify="center").grid(row=2, column=1, padx=5, pady=2)

            # Resumen
            resumen_lbl = tk.Label(parent, text="", font=("Arial", 10),
                                   bg=bg, fg="#a8e6a8", justify="center")
            resumen_lbl.pack(pady=4, padx=10)

            # Fiado
            fiado_var = tk.BooleanVar(value=False)
            fiado_check = ttk.Checkbutton(parent,
                                          text="📝 Marcar el resto como FIADO",
                                          variable=fiado_var,
                                          bootstyle="warning-round-toggle")
            fiado_check.pack(pady=4)

            # Abono (solo si debe)
            abono_var = tk.BooleanVar(value=False)
            abono_monto_var = tk.StringVar(value="")
            abono_frame = tk.Frame(parent, bg=bg)

            # Notas
            tk.Label(parent, text="Notas (opcional):",
                     font=("Arial", 10), bg=bg, fg=fg).pack(pady=(6, 2))
            notas_var = tk.StringVar()
            ttk.Entry(parent, textvariable=notas_var, width=40).pack(pady=3, padx=20)

            refs.update({
                "subtotal": subtotal,
                "total_lbl": total_lbl,
                "desc_var": desc_var,
                "desc_tipo_var": desc_tipo_var,
                "nombre_var": nombre_var,
                "deuda_lbl": deuda_lbl,
                "ef_var": ef_var,
                "tr_var": tr_var,
                "ta_var": ta_var,
                "resumen_lbl": resumen_lbl,
                "fiado_var": fiado_var,
                "abono_var": abono_var,
                "abono_monto_var": abono_monto_var,
                "abono_frame": abono_frame,
                "notas_var": notas_var,
            })

        def build_bottom(parent):
            def confirmar():
                nombre = refs["nombre_var"].get().strip()
                desc_aplicado = calcular_descuento()
                total_actual = max(0.0, subtotal - desc_aplicado)

                # Leer montos
                try:
                    ef = float(refs["ef_var"].get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                except ValueError:
                    ef = 0.0
                try:
                    tr = float(refs["tr_var"].get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                except ValueError:
                    tr = 0.0
                try:
                    ta = float(refs["ta_var"].get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                except ValueError:
                    ta = 0.0

                pagos = []
                if ef > 0:
                    pagos.append({"method": "Efectivo", "amount": ef})
                if tr > 0:
                    pagos.append({"method": "Transferencia", "amount": tr})
                if ta > 0:
                    pagos.append({"method": "Tarjeta", "amount": ta})

                total_pagado = ef + tr + ta
                es_fiado = refs["fiado_var"].get()

                # Validar
                if not pagos and not es_fiado:
                    MD.show_warning("Debes ingresar al menos un método de pago o marcar FIADO.",
                                    "Faltan datos", parent=pop)
                    return

                if total_pagado > total_actual + 0.01:
                    MD.show_warning(
                        f"El total ingresado (${total_pagado:,.0f}) es mayor al total a pagar (${total_actual:,.0f}).".replace(",", "."),
                        "Monto excedido", parent=pop)
                    return

                if es_fiado and not nombre:
                    MD.show_error("Para FIADO debes ingresar el nombre del cliente.",
                                  "Falta nombre", parent=pop)
                    return

                if abs(total_pagado - total_actual) > 0.01 and not es_fiado:
                    falta = total_actual - total_pagado
                    if not MD.yesno(
                            f"El total ingresado es ${total_pagado:,.0f} y falta ${falta:,.0f}.\n"
                            f"¿Deseas marcar la diferencia como FIADO?".replace(",", "."),
                            "Diferencia detectada", parent=pop) == "Yes":
                        return
                    es_fiado = True
                    if not nombre:
                        MD.show_error("Para FIADO debes ingresar el nombre del cliente.",
                                      "Falta nombre", parent=pop)
                        return

                # Abono a deuda (si marcado)
                monto_abono = 0.0
                if refs["abono_var"].get() and nombre:
                    try:
                        monto_abono = float(
                            refs["abono_monto_var"].get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                    except ValueError:
                        monto_abono = 0.0

                # Método principal (el de mayor monto o el primero)
                if pagos:
                    metodo_principal = max(pagos, key=lambda x: x["amount"])["method"]
                else:
                    metodo_principal = "Fiado"

                try:
                    sale_id, total_final, display_num = self.sale_use_case.create_sale(
                        self.cart,
                        payments=pagos if pagos else None,
                        payment_method=metodo_principal,
                        notes=refs["notas_var"].get().strip(),
                        customer_name=nombre,
                        is_credit=es_fiado,
                        discount=desc_aplicado,
                        register_customer_payment_amount=monto_abono)

                    # Generar ticket
                    base_dir = os.path.join(os.path.dirname(self.db_manager.db_path), "tickets")
                    ticket_path = self.sale_use_case.generate_ticket_pdf(sale_id, base_dir=base_dir)
                    if ticket_path:
                        self.last_ticket_path = ticket_path

                    # Mensaje final
                    msg = f"✅ Venta #{display_num:02d} registrada.\n\n"
                    msg += f"Subtotal: ${subtotal:,.0f}\n".replace(",", ".")
                    if desc_aplicado > 0:
                        msg += f"Descuento: -${desc_aplicado:,.0f}\n".replace(",", ".")
                    msg += f"TOTAL: ${total_final:,.0f}\n".replace(",", ".")
                    for p in pagos:
                        msg += f"  • {p['method']}: ${p['amount']:,.0f}\n".replace(",", ".")
                    if es_fiado:
                        msg += f"\n📌 FIADO a: {nombre}\n"
                        if nombre:
                            deuda = self.sale_use_case.get_pending_by_customer(nombre)
                            msg += f"💰 Nueva deuda: ${deuda:,.0f}\n".replace(",", ".")
                    if monto_abono > 0:
                        aplicado, saldo = self.sale_use_case.apply_payment_to_customer(
                            nombre, monto_abono, method=metodo_principal)
                        msg += f"\n💵 Abono aplicado: ${aplicado:,.0f}\n".replace(",", ".")
                        if saldo <= 0.01:
                            msg += "✅ Deuda SALDADA por completo.\n"
                        else:
                            msg += f"📌 Saldo pendiente: ${saldo:,.0f}\n".replace(",", ".")
                    if ticket_path:
                        msg += f"\n🖨 Ticket guardado en:\n{ticket_path}"

                    self.cart = []
                    self.refresh_cart()
                    self.sale_use_case.clear_cart_draft()
                    pop.destroy()
                    MD.show_info(msg, "Venta Exitosa", parent=self)
                    self.scan_entry.focus_set()

                    # Ofrecer abrir el ticket
                    if ticket_path:
                        r = MD.yesno("¿Deseas abrir el ticket ahora?",
                                     "Abrir ticket", parent=self)
                        if r == "Yes":
                            self.open_last_ticket()
                except Exception as e:
                    MD.show_error(f"Error: {e}", "Error", parent=pop)

            ttk.Button(parent, text="✅ Confirmar Pago", command=confirmar,
                       style="DarkGreen.TButton").pack(side="left", padx=8, ipady=8, ipadx=15)
            ttk.Button(parent, text="Cancelar",
                       command=pop.destroy).pack(side="left", padx=8, ipady=8)

        # ====== Lógica de recálculo ======
        def calcular_descuento():
            try:
                v = float(refs["desc_var"].get().replace(",", ".") or 0)
            except ValueError:
                v = 0.0
            if v < 0:
                v = 0.0
            if refs["desc_tipo_var"].get() == "porcentaje":
                if v > 100:
                    v = 100.0
                return subtotal * (v / 100.0)
            else:
                if v > subtotal:
                    v = subtotal
                return v

        def actualizar_total(*args):
            try:
                desc = calcular_descuento()
                total_actual = max(0.0, subtotal - desc)
                refs["total_lbl"].configure(text=f"${total_actual:,.0f}".replace(",", "."))
                actualizar_resumen()
            except Exception:
                pass

        def actualizar_resumen(*args):
            try:
                desc = calcular_descuento()
                total_actual = max(0.0, subtotal - desc)
                ef = float(refs["ef_var"].get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                tr = float(refs["tr_var"].get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                ta = float(refs["ta_var"].get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                total_ing = ef + tr + ta
                falta = total_actual - total_ing
                if falta <= 0.01:
                    txt = f"✅ Ingresado: ${total_ing:,.0f}".replace(",", ".")
                else:
                    txt = f"💵 Ingresado: ${total_ing:,.0f}   |   Falta: ${falta:,.0f}".replace(",", ".")
                refs["resumen_lbl"].configure(text=txt)
            except ValueError:
                refs["resumen_lbl"].configure(text="")

        def on_nombre_change(*args):
            nombre = refs["nombre_var"].get().strip()
            # Limpiar frame de abono
            for w in refs["abono_frame"].winfo_children():
                w.destroy()
            refs["abono_var"].set(False)
            refs["abono_monto_var"].set("")

            if not nombre:
                refs["deuda_lbl"].configure(text="")
                refs["abono_frame"].pack_forget()
                return
            try:
                deuda = self.sale_use_case.get_pending_by_customer(nombre)
            except Exception:
                deuda = 0
            if deuda > 0:
                refs["deuda_lbl"].configure(
                    text=f"⚠️ {nombre} ya debe ${deuda:,.0f} de fiados anteriores.".replace(",", "."),
                    fg="#ffd166")
                # Mostrar checkbox de abono
                ttk.Checkbutton(refs["abono_frame"], text="💵 Abonar",
                                variable=refs["abono_var"],
                                bootstyle="success-round-toggle").pack(side="left", padx=5)
                tk.Label(refs["abono_frame"], text="Monto:", bg=bg, fg=fg,
                         font=("Arial", 10)).pack(side="left", padx=5)
                ttk.Entry(refs["abono_frame"], textvariable=refs["abono_monto_var"],
                          width=12, font=("Arial", 11), justify="center").pack(side="left", padx=5)
                refs["abono_frame"].pack(pady=4)
            else:
                refs["deuda_lbl"].configure(
                    text=f"ℹ️ {nombre} no tiene deudas previas.", fg="#a8e6a8")
                refs["abono_frame"].pack_forget()

        # Traces
        refs["desc_var"].trace_add("write", actualizar_total)
        refs["desc_tipo_var"].trace_add("write", actualizar_total)
        refs["ef_var"].trace_add("write", actualizar_resumen)
        refs["tr_var"].trace_add("write", actualizar_resumen)
        refs["ta_var"].trace_add("write", actualizar_resumen)
        refs["nombre_var"].trace_add("write", on_nombre_change)

        make_scrollable(container, build_content, build_bottom, bg=bg)
        actualizar_total()

        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass