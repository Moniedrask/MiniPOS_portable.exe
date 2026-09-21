class SaleItem:
    def __init__(self, item_id, sale_id, product_id, product_name, barcode,
                 quantity, unit_price, subtotal):
        self.item_id = item_id
        self.sale_id = sale_id
        self.product_id = product_id
        self.product_name = product_name
        self.barcode = barcode
        self.quantity = quantity
        self.unit_price = unit_price
        self.subtotal = subtotal


class Sale:
    def __init__(self, sale_id, date, total, payment_method, notes, items=None):
        self.sale_id = sale_id
        self.date = date
        self.total = total
        self.payment_method = payment_method
        self.notes = notes
        self.items = items if items else []
        self.customer_name = ""
        self.is_credit = 0
        self.is_paid = 1
        self.amount_paid = 0.0
        # ✅ Número visual que se muestra al usuario (puede diferir del sale_id)
        self.display_number = sale_id

    def pending(self):
        return max(0.0, self.total - self.amount_paid)

    def __repr__(self):
        return f"<Sale #{self.sale_id} {self.date} ${self.total}>"