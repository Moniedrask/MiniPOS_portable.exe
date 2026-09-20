from domain.models.product import Product
from infrastucture.db.db_manager import DBManager

class ProductCase:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
    
    def add_product(self, name: str, barcode: str, price: float, stock: int) -> Product:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, barcode, price, stock) VALUES (?,?,?,?)",
            (name, barcode, price, stock)
        )
        conn.commit()
        product_id = cursor.lastrowid
        return Product(product_id, name, barcode, price, stock)
    
    def list_products(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        return [Product(row["product_id"], row["name"], row["barcode"], row["price"], row["stock"]) for row in rows]

    def update_product(self, product_id: int, name: str, barcode: str, price: float, stock: int):
        """Actualiza un producto existente en la base de datos"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET name = ?, barcode = ?, price = ?, stock = ? WHERE product_id = ?",
            (name, barcode, price, stock, product_id)
        )
        conn.commit()

    def delete_product(self, product_id: int):
        """Elimina un producto de la base de datos"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()
