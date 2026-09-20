class Product:
    def __init__(self, product_id: int, name: str, barcode: str, price: float, stock: int):
        self.product_id = product_id
        self.name = name
        self.barcode = barcode
        self.price = price
        self.stock = stock

    def __repr__(self):
        return f"<Product {self.product_id}: {self.name} ({self.barcode}) (${self.price}) Stock: {self.stock}>"
