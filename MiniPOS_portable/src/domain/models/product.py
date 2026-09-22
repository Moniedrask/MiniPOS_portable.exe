class Product:
    def __init__(self, product_id, name, barcode, price, stock,
                 unit_type="unidad", unit="unidad",
                 created_at="", updated_at="", group_name="",
                 cost=0.0, margin_percent=20.0):
        self.product_id = product_id
        self.name = name
        self.barcode = barcode
        self.price = price
        self.stock = stock
        self.unit_type = unit_type
        self.unit = unit
        self.created_at = created_at
        self.updated_at = updated_at
        self.group_name = group_name
        self.cost = cost
        self.margin_percent = margin_percent

    def __repr__(self):
        return f"<Product {self.product_id}: {self.name} ${self.price} (costo ${self.cost}, {self.margin_percent}%)>"