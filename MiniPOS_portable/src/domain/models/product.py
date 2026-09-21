class Product:
    def __init__(self, product_id: int, name: str, barcode: str, price: float,
                 stock: float, unit_type: str = "unidad", unit: str = "unidad"):
        self.product_id = product_id
        self.name = name
        self.barcode = barcode
        self.price = price
        self.stock = stock
        self.unit_type = unit_type  # "unidad" | "peso" | "volumen"
        self.unit = unit            # "unidad" | "kg" | "gr" | "mg" | "Lt" | "ml"

    def __repr__(self):
        return f"<Product {self.product_id}: {self.name} ({self.unit}) ${self.price}>"