from datetime import datetime
from domain.models.sale import Sale, SaleItem


class SaleCase:
    def __init__(self, db_manager):
        self.db = db_manager

    def create_sale(self, items, payment_method="Efectivo", notes=""):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        total = sum(i["quantity"] * i["unit_price"] for i in items)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO sales (date, total, payment_method, notes) VALUES (?,?,?,?)",
            (now, total, payment_method, notes))
        sale_id = cursor.lastrowid

        for item in items:
            subtotal = item["quantity"] * item["unit_price"]
            cursor.execute(
                "INSERT INTO sale_items (sale_id, product_id, product_name, barcode, "
                "quantity, unit, unit_price, subtotal) VALUES (?,?,?,?,?,?,?,?)",
                (sale_id, item["product_id"], item["product_name"], item.get("barcode", ""),
                 item["quantity"], item.get("unit", "unidad"),
                 item["unit_price"], subtotal))
            if item["product_id"]:
                cursor.execute(
                    "UPDATE products SET stock = stock - ? WHERE product_id = ?",
                    (item["quantity"], item["product_id"]))

        conn.commit()
        return sale_id, total

    def get_sales_by_day(self, date_str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales WHERE date LIKE ? ORDER BY date", (f"{date_str}%",))
        sales = []
        for s in cursor.fetchall():
            cursor.execute("SELECT * FROM sale_items WHERE sale_id = ?", (s["sale_id"],))
            items = [SaleItem(r["item_id"], r["sale_id"], r["product_id"], r["product_name"],
                              r["barcode"], r["quantity"], r["unit_price"], r["subtotal"])
                     for r in cursor.fetchall()]
            sales.append(Sale(s["sale_id"], s["date"], s["total"],
                              s["payment_method"], s["notes"], items))
        return sales

    def get_sales_by_month(self, year_month):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales WHERE date LIKE ? ORDER BY date", (f"{year_month}%",))
        sales = []
        for s in cursor.fetchall():
            cursor.execute("SELECT * FROM sale_items WHERE sale_id = ?", (s["sale_id"],))
            items = [SaleItem(r["item_id"], r["sale_id"], r["product_id"], r["product_name"],
                              r["barcode"], r["quantity"], r["unit_price"], r["subtotal"])
                     for r in cursor.fetchall()]
            sales.append(Sale(s["sale_id"], s["date"], s["total"],
                              s["payment_method"], s["notes"], items))
        return sales