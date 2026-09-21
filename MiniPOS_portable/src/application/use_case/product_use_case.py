from domain.models.product import Product
from infrastucture.db.db_manager import DBManager

class ProductCase:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    def add_product(self, name, barcode, price, stock, unit_type="unidad", unit="unidad") -> Product:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, barcode, price, stock, unit_type, unit) VALUES (?,?,?,?,?,?)",
            (name, barcode, price, stock, unit_type, unit)
        )
        conn.commit()
        pid = cursor.lastrowid
        return Product(pid, name, barcode, price, stock, unit_type, unit)

    def list_products(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        return [Product(r["product_id"], r["name"], r["barcode"], r["price"],
                        r["stock"], r["unit_type"], r["unit"]) for r in rows]

    def update_product(self, product_id, name, barcode, price, stock,
                       unit_type="unidad", unit="unidad"):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET name=?, barcode=?, price=?, stock=?, unit_type=?, unit=? WHERE product_id=?",
            (name, barcode, price, stock, unit_type, unit, product_id)
        )
        conn.commit()

    def delete_product(self, product_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()