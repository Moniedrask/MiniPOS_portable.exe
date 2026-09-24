class Product:
    def __init__(self, product_id, name, barcode, price, stock,
                 unit_type="unidad", unit="unidad",
                 created_at="", updated_at="",
                 # === Fase 0 (ideas 25, 26, 27, 28, 4, 16) ===
                 group_name="", cost=0.0, margin_percent=20.0,
                 rounded_price=0.0, round_enabled=0, round_to=100,
                 package_cost=0.0, package_units=0, is_package=0,
                 paused=0, expiry_date=""):
        self.product_id = product_id
        self.name = name
        self.barcode = barcode
        self.price = price
        self.stock = stock
        self.unit_type = unit_type  # "unidad" | "peso" | "volumen"
        self.unit = unit            # "unidad" | "kg" | "gr" | "mg" | "Lt" | "ml"
        self.created_at = created_at
        self.updated_at = updated_at

        # Campos nuevos (con defaults para no romper código viejo)
        self.group_name = group_name
        self.cost = cost
        self.margin_percent = margin_percent
        self.rounded_price = rounded_price if rounded_price else price
        self.round_enabled = round_enabled
        self.round_to = round_to
        self.package_cost = package_cost
        self.package_units = package_units
        self.is_package = is_package
        self.paused = paused
        self.expiry_date = expiry_date

    @property
    def effective_price(self):
        """Precio que se cobra realmente (redondeado si aplica)."""
        if self.round_enabled and self.rounded_price:
            return self.rounded_price
        return self.price

    def __repr__(self):
        return f"<Product {self.product_id}: {self.name} ({self.unit}) ${self.price}>"