import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


# ================================================================
# IDEA 1: TICKET EN PDF
# ================================================================
def generate_ticket_pdf(sale, items, payments=None, business_name="MI NEGOCIO",
                        business_info="", output_path=None, is_copy=False,
                        cashier_name="", business_phone="", business_address=""):
    """
    Genera un PDF con el ticket de venta.
    - sale: objeto Sale
    - items: lista de items (SaleItem o dicts)
    - payments: lista de dicts [{"method":..., "amount":...}] o None
    - Si output_path es None, se genera automáticamente.
    Devuelve la ruta del PDF generado.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
    except ImportError:
        raise Exception("Falta reportlab. Instala: pip install reportlab")

    if output_path is None:
        base = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'data', 'tickets'))
        os.makedirs(base, exist_ok=True)
        sale_num = getattr(sale, "display_number", sale.sale_id)
        output_path = os.path.join(
            base,
            f"ticket_{sale_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # ============ ENCABEZADO ============
    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, business_name)
    y -= 20

    c.setFont("Helvetica", 9)
    if business_info:
        c.drawCentredString(width / 2, y, business_info)
        y -= 12
    if business_address:
        c.drawCentredString(width / 2, y, business_address)
        y -= 12
    if business_phone:
        c.drawCentredString(width / 2, y, f"Tel: {business_phone}")
        y -= 12

    y -= 5
    c.setLineWidth(0.5)
    c.line(40, y, width - 40, y)
    y -= 15

    # ============ INFO DE LA VENTA ============
    c.setFont("Helvetica", 9)
    sale_num = getattr(sale, "display_number", sale.sale_id)
    c.drawString(40, y, f"Ticket #: {sale_num}")
    c.drawRightString(width - 40, y, f"Fecha: {sale.date}")
    y -= 14

    if getattr(sale, "customer_name", ""):
        c.drawString(40, y, f"Cliente: {sale.customer_name}")
        y -= 14
    if cashier_name:
        c.drawString(40, y, f"Cajero: {cashier_name}")
        y -= 14

    c.line(40, y, width - 40, y)
    y -= 15

    # ============ TABLA DE ITEMS ============
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Producto")
    c.drawString(300, y, "Cant.")
    c.drawString(360, y, "P. Unit.")
    c.drawRightString(width - 40, y, "Subtotal")
    y -= 12

    c.setFont("Helvetica", 9)
    for it in items:
        # Soporta objetos y dicts
        if hasattr(it, "product_name"):
            name = it.product_name
            qty = it.quantity
            price = it.unit_price
            sub = it.subtotal
        else:
            name = it.get("product_name", "")
            qty = it.get("quantity", 0)
            price = it.get("unit_price", 0)
            sub = it.get("subtotal", qty * price)

        # Envolver nombre si es largo
        nombre_corto = (name[:38] + "…") if len(name) > 40 else name
        c.drawString(40, y, nombre_corto)
        c.drawString(300, y, f"{qty:g}")
        c.drawString(360, y, f"${price:,.0f}")
        c.drawRightString(width - 40, y, f"${sub:,.0f}")
        y -= 12

        if y < 120:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)

    y -= 5
    c.line(40, y, width - 40, y)
    y -= 15

    # ============ TOTALES ============
    c.setFont("Helvetica", 10)
    subtotal = getattr(sale, "subtotal", sale.total)
    descuento = getattr(sale, "discount", 0.0)

    if descuento > 0:
        c.drawString(360, y, "Subtotal:")
        c.drawRightString(width - 40, y, f"${subtotal:,.0f}")
        y -= 14
        c.drawString(360, y, "Descuento:")
        c.drawRightString(width - 40, y, f"-${descuento:,.0f}")
        y -= 14

    c.setFont("Helvetica-Bold", 12)
    c.drawString(360, y, "TOTAL:")
    c.drawRightString(width - 40, y, f"${sale.total:,.0f}")
    y -= 20

    # ============ PAGOS ============
    c.setFont("Helvetica", 9)
    if payments and len(payments) > 1:
        c.drawString(40, y, "Forma de pago (mixto):")
        y -= 12
        for p in payments:
            c.drawString(60, y, f"  • {p.get('method','Otro')}:")
            c.drawRightString(width - 40, y, f"${p.get('amount',0):,.0f}")
            y -= 12
    else:
        metodo = sale.payment_method or "Efectivo"
        c.drawString(40, y, f"Forma de pago: {metodo}")
        y -= 12

    if getattr(sale, "is_credit", 0):
        pagado = getattr(sale, "amount_paid", 0.0) or 0.0
        debe = sale.total - pagado
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, f"FIADO - Abonado: ${pagado:,.0f}")
        y -= 12
        c.drawString(40, y, f"Saldo pendiente: ${debe:,.0f}")
        y -= 12

    # ============ PIE ============
    y -= 10
    c.line(40, y, width - 40, y)
    y -= 15
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, y, "¡Gracias por su compra!")
    y -= 12
    c.drawCentredString(width / 2, y, "MiniPOS")

    if is_copy:
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.red)
        c.drawCentredString(width / 2, height - 20, "*** COPIA ***")

    c.save()
    return output_path


# ================================================================
# IDEA 5: ETIQUETAS PDF (formato Avery carta, 30 por hoja)
# ================================================================
def generate_labels_pdf(products, output_path, copies=1):
    """
    Genera un PDF de etiquetas tamaño carta, 3 columnas x 10 filas = 30 por hoja.
    Formato Avery 5160 (2.625" x 1").
    Cada etiqueta: código de barras + nombre + precio redondeado.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
    except ImportError:
        raise Exception("Falta reportlab. Instala: pip install reportlab")

    try:
        from reportlab.graphics.barcode import code128
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics import renderPDF
        HAS_BARCODE = True
    except ImportError:
        HAS_BARCODE = False

    # Dimensiones Avery 5160 (carta, 30 etiquetas)
    LABEL_W = 2.625 * inch
    LABEL_H = 1.0 * inch
    MARGIN_LEFT = 0.1875 * inch
    MARGIN_TOP = 0.5 * inch
    COLS = 3
    ROWS = 10
    LABELS_PER_PAGE = COLS * ROWS

    c = canvas.Canvas(output_path, pagesize=letter)

    # Expandir según copias
    todas = []
    for p in products:
        for _ in range(copies):
            todas.append(p)

    total = len(todas)
    for idx, prod in enumerate(todas):
        pos = idx % LABELS_PER_PAGE
        if pos == 0 and idx > 0:
            c.showPage()

        col = pos % COLS
        row = pos // COLS

        x = MARGIN_LEFT + col * LABEL_W
        y_top = letter[1] - MARGIN_TOP - row * LABEL_H

        # Nombre (arriba)
        c.setFont("Helvetica-Bold", 7)
        nombre = (prod.name or "")[:30]
        c.drawString(x + 4, y_top - 10, nombre)

        # Precio redondeado (arriba derecha, grande)
        precio = prod.rounded_price if prod.rounded_price else prod.price
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(x + LABEL_W - 4, y_top - 12, f"${precio:,.0f}")

        # Código de barras (abajo)
        if HAS_BARCODE and prod.barcode:
            try:
                bc = code128.Code128(prod.barcode, barHeight=0.35 * inch,
                                     barWidth=0.008 * inch)
                bc.drawOn(c, x + (LABEL_W - bc.width) / 2, y_top - LABEL_H + 6)
            except Exception:
                c.setFont("Helvetica", 6)
                c.drawCentredString(x + LABEL_W / 2, y_top - LABEL_H + 15,
                                    prod.barcode)
        else:
            c.setFont("Helvetica", 7)
            c.drawCentredString(x + LABEL_W / 2, y_top - LABEL_H + 15,
                                prod.barcode or "")

    c.save()
    return output_path


# ================================================================
# IDEA 11: VENTANA DE GRÁFICOS
# ================================================================
class ChartsWindow(tk.Toplevel):
    def __init__(self, master, sale_case):
        super().__init__(master)
        self.sale_case = sale_case

        self.title("📊 Gráficos y estadísticas")
        self.geometry("1100x750")
        self.transient(master)

        # Intentar importar matplotlib
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            self.Figure = Figure
            self.FigureCanvasTkAgg = FigureCanvasTkAgg
            self.HAS_MPL = True
        except ImportError:
            self.HAS_MPL = False

        # ============ Barra superior ============
        top = tk.Frame(self, bg="#f0f0f0")
        top.pack(fill="x")

        tk.Label(top, text="Rango:", bg="#f0f0f0",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=6, pady=8)
        self.var_range = tk.StringVar(value="7 días")
        ttk.Combobox(top, textvariable=self.var_range, state="readonly",
                     values=["Hoy", "7 días", "30 días", "Mes actual", "Todo"],
                     width=12).pack(side="left")
        self.var_range.trace_add("write", lambda *a: self.reload())

        tk.Button(top, text="🔄 Refrescar", command=self.reload,
                  bg="#607D8B", fg="white", relief="flat", padx=10,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=8)

        tk.Button(top, text="📕 Exportar PDF", command=self.export_pdf,
                  bg="#f44336", fg="white", relief="flat", padx=10,
                  font=("Segoe UI", 9, "bold")).pack(side="right", padx=8, pady=6)

        # ============ Notebook con pestañas ============
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # Pestañas
        self.tab_profit = tk.Frame(self.notebook)
        self.tab_top = tk.Frame(self.notebook)
        self.tab_days = tk.Frame(self.notebook)
        self.tab_hours = tk.Frame(self.notebook)

        self.notebook.add(self.tab_profit, text="💰 Ganancias reales")
        self.notebook.add(self.tab_top, text="🏆 Top 10 productos")
        self.notebook.add(self.tab_days, text="📈 Ventas últimos días")
        self.notebook.add(self.tab_hours, text="🕐 Ventas por hora")

        if not self.HAS_MPL:
            tk.Label(self, text="⚠️ matplotlib no está instalado.\n"
                                "Ejecuta: pip install matplotlib",
                     fg="#c62828", font=("Segoe UI", 12, "bold")).pack(pady=20)

        self.reload()

    def _get_range_dates(self):
        from datetime import datetime, timedelta
        hoy = datetime.now().date()
        rango = self.var_range.get()
        if rango == "Hoy":
            return hoy.strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d")
        if rango == "7 días":
            return (hoy - timedelta(days=6)).strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d")
        if rango == "30 días":
            return (hoy - timedelta(days=29)).strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d")
        if rango == "Mes actual":
            return hoy.replace(day=1).strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d")
        return None, None

    def reload(self):
        if not self.HAS_MPL:
            return

        for tab in (self.tab_profit, self.tab_top, self.tab_days, self.tab_hours):
            for w in tab.winfo_children():
                w.destroy()

        start, end = self._get_range_dates()
        self._draw_profit(self.tab_profit, start, end)
        self._draw_top(self.tab_top, start, end)
        self._draw_days(self.tab_days)
        self._draw_hours(self.tab_hours, start, end)

    def _canvas(self, parent, fig):
        canvas = self.FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        return canvas

    def _draw_profit(self, parent, start, end):
        res = self.sale_case.get_profit_summary(start, end)
        fig = self.Figure(figsize=(10, 5), dpi=90)
        ax = fig.add_subplot(111)
        labels = ["Ventas", "Costos", "Devoluciones", "Ganancia neta"]
        values = [res["total_sales"], res["total_cost"],
                  res["total_returns"], res["net_profit"]]
        colors = ["#4CAF50", "#f44336", "#FF9800", "#2196F3"]
        bars = ax.bar(labels, values, color=colors)
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    f"${v:,.0f}", ha="center", va="bottom",
                    fontsize=9, fontweight="bold")
        ax.set_title("Ganancias reales del periodo", fontsize=12, fontweight="bold")
        ax.set_ylabel("$ Pesos")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        self._canvas(parent, fig)

    def _draw_top(self, parent, start, end):
        data = self.sale_case.get_top_products(10, start, end)
        fig = self.Figure(figsize=(10, 5), dpi=90)
        ax = fig.add_subplot(111)
        if not data:
            ax.text(0.5, 0.5, "Sin datos en el periodo",
                    ha="center", va="center", fontsize=14)
        else:
            names = [(d["product_name"][:20]) for d in reversed(data)]
            qtys = [d["quantity"] for d in reversed(data)]
            bars = ax.barh(names, qtys, color="#00BCD4")
            for b, d in zip(bars, reversed(data)):
                ax.text(b.get_width(), b.get_y() + b.get_height() / 2,
                        f" {d['quantity']:g} u / ${d['total']:,.0f}",
                        va="center", fontsize=8)
            ax.set_title("Top 10 productos más vendidos", fontsize=12, fontweight="bold")
            ax.set_xlabel("Cantidad")
            ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()
        self._canvas(parent, fig)

    def _draw_days(self, parent):
        data = self.sale_case.get_sales_last_days(30)
        fig = self.Figure(figsize=(10, 5), dpi=90)
        ax = fig.add_subplot(111)
        fechas = [d["date"][5:] for d in data]  # MM-DD
        totales = [d["total"] for d in data]
        ax.plot(fechas, totales, marker="o", color="#2196F3", linewidth=2)
        ax.fill_between(range(len(fechas)), totales, alpha=0.2, color="#2196F3")
        ax.set_title("Ventas de los últimos 30 días", fontsize=12, fontweight="bold")
        ax.set_ylabel("$ Pesos")
        ax.grid(alpha=0.3)
        if len(fechas) > 10:
            ax.set_xticks(range(0, len(fechas), max(1, len(fechas) // 10)))
            ax.set_xticklabels([fechas[i] for i in range(0, len(fechas),
                                 max(1, len(fechas) // 10))], rotation=45)
        fig.tight_layout()
        self._canvas(parent, fig)

    def _draw_hours(self, parent, start, end):
        data = self.sale_case.get_sales_by_hour(start, end)
        fig = self.Figure(figsize=(10, 5), dpi=90)
        ax = fig.add_subplot(111)
        horas = [f"{d['hour']:02d}h" for d in data]
        totales = [d["total"] for d in data]
        ax.bar(horas, totales, color="#FF9800")
        ax.set_title("Ventas por hora del día", fontsize=12, fontweight="bold")
        ax.set_ylabel("$ Pesos")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        self._canvas(parent, fig)

    # ============ EXPORTAR A PDF ============
    def export_pdf(self):
        if not self.HAS_MPL:
            messagebox.showerror("Exportar", "matplotlib no está instalado.")
            return

        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"graficos_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        if not ruta:
            return

        try:
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            messagebox.showerror("Exportar", "No se pudo importar PdfPages.")
            return

        start, end = self._get_range_dates()

        try:
            with PdfPages(ruta) as pdf:
                # Página 1: ganancias
                fig1 = self.Figure(figsize=(11, 7), dpi=100)
                ax1 = fig1.add_subplot(111)
                res = self.sale_case.get_profit_summary(start, end)
                labels = ["Ventas", "Costos", "Devoluciones", "Ganancia neta"]
                values = [res["total_sales"], res["total_cost"],
                          res["total_returns"], res["net_profit"]]
                colors = ["#4CAF50", "#f44336", "#FF9800", "#2196F3"]
                bars = ax1.bar(labels, values, color=colors)
                for b, v in zip(bars, values):
                    ax1.text(b.get_x() + b.get_width() / 2, b.get_height(),
                             f"${v:,.0f}", ha="center", va="bottom", fontsize=10)
                ax1.set_title("Ganancias reales", fontsize=14, fontweight="bold")
                ax1.grid(axis="y", alpha=0.3)
                fig1.tight_layout()
                pdf.savefig(fig1)

                # Página 2: top 10
                fig2 = self.Figure(figsize=(11, 7), dpi=100)
                ax2 = fig2.add_subplot(111)
                data = self.sale_case.get_top_products(10, start, end)
                if data:
                    names = [d["product_name"][:25] for d in reversed(data)]
                    qtys = [d["quantity"] for d in reversed(data)]
                    ax2.barh(names, qtys, color="#00BCD4")
                    ax2.set_title("Top 10 productos más vendidos",
                                  fontsize=14, fontweight="bold")
                else:
                    ax2.text(0.5, 0.5, "Sin datos", ha="center", va="center")
                fig2.tight_layout()
                pdf.savefig(fig2)

                # Página 3: últimos 30 días
                fig3 = self.Figure(figsize=(11, 7), dpi=100)
                ax3 = fig3.add_subplot(111)
                data = self.sale_case.get_sales_last_days(30)
                ax3.plot([d["date"][5:] for d in data],
                         [d["total"] for d in data],
                         marker="o", color="#2196F3")
                ax3.set_title("Ventas últimos 30 días",
                              fontsize=14, fontweight="bold")
                ax3.grid(alpha=0.3)
                fig3.tight_layout()
                pdf.savefig(fig3)

                # Página 4: por hora
                fig4 = self.Figure(figsize=(11, 7), dpi=100)
                ax4 = fig4.add_subplot(111)
                data = self.sale_case.get_sales_by_hour(start, end)
                ax4.bar([f"{d['hour']:02d}h" for d in data],
                        [d["total"] for d in data], color="#FF9800")
                ax4.set_title("Ventas por hora", fontsize=14, fontweight="bold")
                ax4.grid(axis="y", alpha=0.3)
                fig4.tight_layout()
                pdf.savefig(fig4)

            messagebox.showinfo("Exportar", f"PDF generado:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")
