class SaleItem:
    def __init__(self, item_id, sale_id, product_id, product_name, barcode,
                 quantity, unit_price, subtotal, returned_qty=0):
        self.item_id = item_id
        self.sale_id = sale_id
        self.product_id = product_id
        self.product_name = product_name
        self.barcode = barcode
        self.quantity = quantity
        self.unit_price = unit_price
        self.subtotal = subtotal
        self.returned_qty = returned_qty or 0

    @property
    def pending_qty(self):
        """Cantidad aún no devuelta."""
        return max(0.0, (self.quantity or 0) - (self.returned_qty or 0))

    def __repr__(self):
        return f"<SaleItem {self.product_name} x{self.quantity}>"


class Sale:
    def __init__(self, sale_id, date, total, payment_method, notes, items=None):
        self.sale_id = sale_id
        self.date = date
        self.total = total                          # total final (subtotal - discount)
        self.payment_method = payment_method
        self.notes = notes
        self.items = items if items else []
        self.customer_name = ""
        self.is_credit = 0
        self.is_paid = 1
        self.amount_paid = 0.0
        self.display_number = sale_id               # Número visual (#XX)
        self.subtotal = total                       # por defecto igual al total
        self.discount = 0.0
        self.is_returned = 0                        # Idea 10
        self.payments = []                          # Idea 3 (pago mixto)

    def pending(self):
        """Saldo pendiente (para fiados)."""
        return max(0.0, self.total - self.amount_paid)

    def __repr__(self):
        return f"<Sale #{self.sale_id} {self.date} ${self.total}>"