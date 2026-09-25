"""
Ventana unificada de Ajustes con pestañas:
- Apariencia: tema, tamaño de fuente
- Seguridad: contraseña de inicio
- Inicio: autostart (Windows + Linux)
- Ventas: reset contador, auto-reset diario
- Negocio: datos del negocio
- Ticket: tamaño, copias, datos a mostrar
- Vencimiento: días de alerta, descuento de oferta
- Cajero: nombre del cajero
- Backup: carpeta, respaldo automático
- Auto-Export: exportar automáticamente a carpeta/USB
"""
import os
import sys
import shutil
import platform
import tkinter as tk
import ttkbootstrap as ttk
from tkinter import filedialog
from datetime import datetime

from presentation.views.widgets import (
    MD, show_popup_smooth, get_business_info, save_business_info
)


class SettingsView(tk.Toplevel):
    def __init__(self, master, db_manager, product_use_case, sale_use_case,
                 on_theme_change=None, on_font_change=None, on_business_change=None,
                 on_change_password=None, on_autostart_change=None,
                 on_apply_theme=None):
        super().__init__(master)
        self.db = db_manager
        self.product_case = product_use_case
        self.sale_case = sale_use_case
        self.on_theme_change = on_theme_change
        self.on_font_change = on_font_change
        self.on_business_change = on_business_change
        self.on_change_password = on_change_password
        self.on_autostart_change = on_autostart_change
        self.on_apply_theme = on_apply_theme

        self.title("⚙️ Ajustes - MiniPOS")
        self.geometry("820x700")
        self.minsize(700, 580)
        self.transient(master)

        try:
            bg = ttk.Style().colors.bg
            fg = ttk.Style().colors.fg
        except Exception:
            bg = "#1a1a1a"
            fg = "#ffffff"
        self.configure(bg=bg)

        tk.Label(self, text="⚙️ AJUSTES", font=("Arial", 18, "bold"),
                 bg=bg, fg=fg).pack(pady=(15, 6))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=8)

        self._build_tab_apariencia()
        self._build_tab_seguridad()
        self._build_tab_inicio()
        self._build_tab_ventas()
        self._build_tab_negocio()
        self._build_tab_ticket()
        self._build_tab_vencimiento()
        self._build_tab_cajero()
        self._build_tab_backup()
        self._build_tab_auto_export()

        bf = tk.Frame(self, bg=bg)
        bf.pack(side="bottom", fill="x", pady=10)
        ttk.Button(bf, text="Cerrar", command=self.destroy,
                   bootstyle="secondary").pack(side="right", padx=12)

        show_popup_smooth(self)
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    # ============================================================
    # APARIENCIA
    # ============================================================
    def _build_tab_apariencia(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="🎨 Apariencia")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="Tema de la aplicación:",
                 font=("Arial", 11, "bold"), bg=bg, fg=fg).pack(
                     pady=(20, 4), anchor="w", padx=20)
        self.var_theme = tk.StringVar(
            value=self.db.get_setting("theme", "darkly") or "darkly")
        tf = tk.Frame(tab, bg=bg)
        tf.pack(anchor="w", padx=20)
        for val, txt in [("darkly", "🌙 Oscuro"), ("flatly", "☀️ Claro")]:
            ttk.Radiobutton(tf, text=txt, variable=self.var_theme,
                            value=val, bootstyle="info").pack(side="left", padx=6)

        tk.Label(tab, text="Tamaño de fuente:",
                 font=("Arial", 11, "bold"), bg=bg, fg=fg).pack(
                     pady=(20, 4), anchor="w", padx=20)
        self.var_font_size = tk.StringVar(
            value=self.db.get_setting("font_size", "11") or "11")
        ff = tk.Frame(tab, bg=bg)
        ff.pack(anchor="w", padx=20)
        ttk.Combobox(ff, textvariable=self.var_font_size, state="readonly",
                     values=["9", "10", "11", "12", "13", "14", "16", "18"],
                     width=8).pack(side="left")
        tk.Label(ff, text="(9 a 18 pt)", bg=bg, fg=fg,
                 font=("Arial", 9, "italic")).pack(side="left", padx=8)

        def aplicar():
            theme = self.var_theme.get()
            size = self.var_font_size.get()
            self.db.set_setting("theme", theme)
            self.db.set_setting("font_size", size)
            if self.on_theme_change:
                try:
                    self.on_theme_change(theme)
                except Exception:
                    pass
            if self.on_font_change:
                try:
                    self.on_font_change(int(size))
                except Exception:
                    pass
            MD.show_info("✅ Apariencia actualizada.", "Listo", parent=self)

        ttk.Button(tab, text="💾 Aplicar", command=aplicar,
                   bootstyle="success").pack(pady=20, padx=20, anchor="w")

    # ============================================================
    # SEGURIDAD
    # ============================================================
    def _build_tab_seguridad(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="🔐 Seguridad")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="🔐 Contraseña de inicio",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 4))
        tk.Label(tab, text="Se pide al iniciar la aplicación.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))

        pwd = self.db.get_setting("startup_password", "") or ""
        estado = "✅ CONFIGURADA" if pwd else "❌ NO configurada"
        tk.Label(tab, text=f"Estado actual: {estado}",
                 font=("Arial", 11, "bold"), bg=bg, fg=fg).pack(pady=6)

        def abrir_cambio():
            if self.on_change_password:
                try:
                    self.on_change_password()
                except Exception:
                    pass
            else:
                MD.show_info("Función no disponible.", "Info", parent=self)

        ttk.Button(tab, text="🔑 Cambiar contraseña de inicio",
                   command=abrir_cambio,
                   bootstyle="success").pack(pady=8)

        if pwd:
            def quitar():
                if MD.yesno("¿Quitar la contraseña de inicio?", "Confirmar",
                            parent=self) == "Yes":
                    self.db.set_setting("startup_password", "")
                    MD.show_info("Contraseña eliminada.", "Listo", parent=self)
            ttk.Button(tab, text="❌ Quitar contraseña",
                       command=quitar, bootstyle="danger").pack(pady=8)

        tk.Label(tab, text=" ", bg=bg, fg=fg).pack()
        tk.Label(tab, text="🔒 Contraseña de administrador",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 4))
        tk.Label(tab,
                 text="Se pide para acciones sensibles (borrar ventas,\n"
                      "reiniciar contador, ajustes críticos).",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8",
                 justify="center").pack(pady=(0, 6))
        tk.Label(tab, text="Contraseña actual: 1234 (fija por ahora)",
                 font=("Arial", 10), bg=bg, fg=fg).pack(pady=6)

    # ============================================================
    # INICIO (autostart)
    # ============================================================
    def _build_tab_inicio(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="🚀 Inicio")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="🚀 Ejecución al iniciar el sistema",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 4))
        tk.Label(tab,
                 text="Inicia MiniPOS automáticamente al arrancar el sistema operativo.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))

        habilitado = self._is_autostart_enabled()
        self.var_autostart = tk.BooleanVar(value=habilitado)
        ttk.Checkbutton(tab, text="🚀 Ejecutar con el Sistema Operativo (SO)",
                        variable=self.var_autostart,
                        bootstyle="success-round-toggle",
                        command=self._toggle_autostart).pack(pady=6)

        sistema = platform.system()
        tk.Label(tab, text=f"Sistema detectado: {sistema}",
                 font=("Arial", 10), bg=bg, fg=fg).pack(pady=4)

    def _is_autostart_enabled(self):
        sistema = platform.system()
        if sistema == "Windows":
            try:
                startup = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows',
                                       'Start Menu', 'Programs', 'Startup')
                return os.path.exists(os.path.join(startup, 'MiniPOS_Portable.bat'))
            except Exception:
                return False
        elif sistema == "Linux":
            try:
                autostart = os.path.expanduser("~/.config/autostart/MiniPOS.desktop")
                return os.path.exists(autostart)
            except Exception:
                return False
        return False

    def _toggle_autostart(self):
        activar = self.var_autostart.get()
        sistema = platform.system()
        try:
            if sistema == "Windows":
                startup = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows',
                                       'Start Menu', 'Programs', 'Startup')
                os.makedirs(startup, exist_ok=True)
                bat = os.path.join(startup, 'MiniPOS_Portable.bat')
                if activar:
                    with open(bat, 'w', encoding='utf-8') as f:
                        f.write(f'@echo off\nstart "" "{sys.executable}"\n')
                else:
                    if os.path.exists(bat):
                        os.remove(bat)
            elif sistema == "Linux":
                autostart_dir = os.path.expanduser("~/.config/autostart")
                os.makedirs(autostart_dir, exist_ok=True)
                desktop = os.path.join(autostart_dir, "MiniPOS.desktop")
                if activar:
                    if getattr(sys, 'frozen', False):
                        exe = sys.executable
                    else:
                        exe = f"python3 {os.path.abspath(sys.argv[0])}"
                    contenido = (
                        "[Desktop Entry]\n"
                        "Type=Application\n"
                        "Name=MiniPOS Portable\n"
                        "Comment=Punto de Venta\n"
                        f"Exec={exe}\n"
                        "Terminal=false\n"
                        "X-GNOME-Autostart-enabled=true\n"
                    )
                    with open(desktop, 'w', encoding='utf-8') as f:
                        f.write(contenido)
                    os.chmod(desktop, 0o755)
                else:
                    if os.path.exists(desktop):
                        os.remove(desktop)
            else:
                MD.show_warning(f"Auto-inicio no soportado en {sistema}.",
                                "No soportado", parent=self)
                return

            if activar:
                MD.show_info(f"✅ Auto-inicio ACTIVADO en {sistema}.",
                             "Auto-inicio", parent=self)
            else:
                MD.show_info(f"❌ Auto-inicio DESACTIVADO en {sistema}.",
                             "Auto-inicio", parent=self)

            if self.on_autostart_change:
                try:
                    self.on_autostart_change()
                except Exception:
                    pass
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)
            self.var_autostart.set(not activar)

    # ============================================================
    # VENTAS
    # ============================================================
    def _build_tab_ventas(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="🔢 Ventas")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="🕛 Auto-reset diario del contador de ventas",
                 font=("Arial", 12, "bold"), bg=bg, fg=fg).pack(
                     pady=(20, 4), anchor="w", padx=20)
        tk.Label(tab,
                 text="Al cambiar el día, el número de venta vuelve a #01 automáticamente.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(
                     anchor="w", padx=20)

        self.var_auto_reset = tk.BooleanVar(
            value=self.sale_case.is_auto_reset_enabled())
        ttk.Checkbutton(tab, text="✅ Activar auto-reset diario",
                        variable=self.var_auto_reset,
                        bootstyle="success-round-toggle",
                        command=self._toggle_auto_reset).pack(
                            pady=8, padx=20, anchor="w")

        tk.Label(tab, text="🔄 Reinicio manual del contador",
                 font=("Arial", 12, "bold"), bg=bg, fg=fg).pack(
                     pady=(20, 4), anchor="w", padx=20)
        tk.Label(tab,
                 text="Reinicia el número de venta a #01 sin borrar ventas ni fiados.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(
                     anchor="w", padx=20)

        def reset_manual():
            if MD.yesno(
                    "🔄 ¿Reiniciar el contador de ventas?\n\n"
                    "Las ventas y fiados NO se borran.\n"
                    "Solo el número que aparece como 'Venta #XX'.",
                    "Confirmar", parent=self, default_yes=True) != "Yes":
                return
            try:
                self.sale_case.reset_sale_number_counter()
                self.sale_case.set_last_reset_date(datetime.now().strftime("%Y-%m-%d"))
                MD.show_info("✅ Contador reiniciado. La próxima venta será #01.",
                             "Listo", parent=self)
            except Exception as e:
                MD.show_error(f"Error: {e}", "Error", parent=self)

        ttk.Button(tab, text="🔄 Reiniciar contador ahora",
                   command=reset_manual,
                   bootstyle="warning").pack(pady=8, padx=20, anchor="w")

    def _toggle_auto_reset(self):
        val = self.var_auto_reset.get()
        self.sale_case.enable_auto_reset(val)
        if val:
            MD.show_info("✅ Auto-reset ACTIVADO.", "Ventas", parent=self)
        else:
            MD.show_info("❌ Auto-reset DESACTIVADO.", "Ventas", parent=self)

    # ============================================================
    # NEGOCIO
    # ============================================================
    def _build_tab_negocio(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="🏪 Negocio")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        info = get_business_info(self.db)

        tk.Label(tab, text="🏪 DATOS DEL NEGOCIO",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(15, 4))
        tk.Label(tab,
                 text="Aparecen en la barra de título, en la barra superior y en los tickets.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))

        container = tk.Frame(tab, bg=bg)
        container.pack(fill="both", expand=True, padx=20)

        self._biz_refs = {}
        campos = [
            ("type", "Tipo de negocio (tienda, víveres...):"),
            ("name", "Nombre del negocio:"),
            ("owner", "Dueño:"),
            ("place", "Lugar / Dirección:"),
            ("phone", "Teléfono:"),
            ("employees", "Empleados (separados por coma):"),
        ]
        for key, label in campos:
            tk.Label(container, text=label, font=("Arial", 10),
                     bg=bg, fg=fg, anchor="w").pack(fill="x", pady=(8, 2))
            e = ttk.Entry(container, width=60, font=("Arial", 11))
            e.pack(fill="x", pady=2)
            if info.get(key):
                e.insert(0, info.get(key))
            self._biz_refs[key] = e

        tk.Label(container, text="Notas adicionales:",
                 font=("Arial", 10), bg=bg, fg=fg, anchor="w").pack(
                     fill="x", pady=(8, 2))
        notas = tk.Text(container, width=60, height=3, font=("Arial", 10),
                        bg=bg, fg=fg, insertbackground=fg,
                        relief="solid", borderwidth=1, wrap="word")
        notas.pack(fill="x", pady=2)
        if info.get("notes"):
            notas.insert("1.0", info.get("notes"))
        self._biz_refs["notes"] = notas

        def guardar():
            data = {}
            for k in ("type", "name", "owner", "place", "phone", "employees"):
                try:
                    data[k] = self._biz_refs[k].get()
                except Exception:
                    data[k] = ""
            try:
                data["notes"] = self._biz_refs["notes"].get("1.0", tk.END).strip()
            except Exception:
                data["notes"] = ""
            try:
                save_business_info(self.db, data)
                MD.show_info("✅ Datos del negocio guardados.", "Listo", parent=self)
                if self.on_business_change:
                    try:
                        self.on_business_change()
                    except Exception:
                        pass
            except Exception as e:
                MD.show_error(f"Error: {e}", "Error", parent=self)

        ttk.Button(container, text="💾 Guardar datos",
                   command=guardar,
                   bootstyle="success").pack(pady=12, anchor="e")

    # ============================================================
    # TICKET
    # ============================================================
    def _build_tab_ticket(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="🖨️ Ticket")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="🖨️ Configuración del ticket PDF",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 8))

        tk.Label(tab, text="Tamaño de página:",
                 font=("Arial", 11), bg=bg, fg=fg).pack(
                     anchor="w", padx=20, pady=(10, 4))
        self.var_ticket_size = tk.StringVar(
            value=self.db.get_setting("ticket_size", "letter") or "letter")
        tf = tk.Frame(tab, bg=bg)
        tf.pack(anchor="w", padx=20)
        for val, txt in [("letter", "📄 Carta"), ("80mm", "🎫 80mm (rollo)"),
                         ("58mm", "🎫 58mm (rollo chico)")]:
            ttk.Radiobutton(tf, text=txt, variable=self.var_ticket_size,
                            value=val, bootstyle="info").pack(side="left", padx=6)

        tk.Label(tab, text="Copias automáticas (al cobrar):",
                 font=("Arial", 11), bg=bg, fg=fg).pack(
                     anchor="w", padx=20, pady=(15, 4))
        self.var_ticket_copies = tk.StringVar(
            value=self.db.get_setting("ticket_copies", "0") or "0")
        ttk.Combobox(tab, textvariable=self.var_ticket_copies, state="readonly",
                     values=["0", "1", "2", "3"], width=8).pack(anchor="w", padx=20)

        tk.Label(tab, text="Mensaje al pie del ticket:",
                 font=("Arial", 11), bg=bg, fg=fg).pack(
                     anchor="w", padx=20, pady=(15, 4))
        self.var_ticket_footer = tk.StringVar(
            value=self.db.get_setting("ticket_footer",
                                       "¡Gracias por su compra!") or "")
        ttk.Entry(tab, textvariable=self.var_ticket_footer, width=60).pack(
            anchor="w", padx=20)

        def guardar():
            self.db.set_setting("ticket_size", self.var_ticket_size.get())
            self.db.set_setting("ticket_copies", self.var_ticket_copies.get())
            self.db.set_setting("ticket_footer", self.var_ticket_footer.get())
            MD.show_info("✅ Ticket actualizado.", "Listo", parent=self)

        ttk.Button(tab, text="💾 Guardar", command=guardar,
                   bootstyle="success").pack(pady=20, padx=20, anchor="w")

    # ============================================================
    # VENCIMIENTO
    # ============================================================
    def _build_tab_vencimiento(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="📅 Vencimiento")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="📅 Alertas de vencimiento de productos",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 4))
        tk.Label(tab, text="Avisos antes de que un producto venza.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))

        cfg = self.product_case.get_expiry_settings()

        def row_field(label, var_name, value, hint=""):
            f = tk.Frame(tab, bg=bg)
            f.pack(fill="x", padx=20, pady=6)
            tk.Label(f, text=label, font=("Arial", 10, "bold"),
                     bg=bg, fg=fg, width=28, anchor="w").pack(side="left")
            v = tk.StringVar(value=str(value))
            setattr(self, var_name, v)
            ttk.Entry(f, textvariable=v, width=10, justify="center").pack(
                side="left", padx=6)
            if hint:
                tk.Label(f, text=hint, font=("Arial", 9, "italic"),
                         bg=bg, fg="#888888").pack(side="left", padx=6)

        row_field("🟠 Alerta temprana (días):", "_var_warn1",
                  cfg["warn_days_1"], "Aviso amarillo")
        row_field("🟡 Alerta cercana (días):", "_var_warn2",
                  cfg["warn_days_2"], "Aviso naranja")
        row_field("💡 Zona de oferta (días):", "_var_offer",
                  cfg["offer_days"], "Sugerir oferta")
        row_field("🏷️ Descuento de oferta (%):", "_var_discount",
                  cfg["offer_discount"], "")

        def guardar():
            try:
                w1 = int(float(self._var_warn1.get() or 15))
                w2 = int(float(self._var_warn2.get() or 7))
                od = int(float(self._var_offer.get() or 2))
                disc = float(self._var_discount.get() or 20)
            except ValueError:
                MD.show_error("Valores inválidos.", "Error", parent=self)
                return
            if not (w1 >= w2 >= od):
                MD.show_error(
                    "Los días deben cumplir: temprana ≥ cercana ≥ oferta\n"
                    "Ejemplo: 15 ≥ 7 ≥ 2",
                    "Orden inválido", parent=self)
                return
            try:
                self.product_case.set_expiry_settings(w1, w2, od, disc)
                MD.show_info(
                    f"✅ Alertas configuradas:\n"
                    f"🟠 Temprana: {w1} días\n"
                    f"🟡 Cercana: {w2} días\n"
                    f"💡 Oferta: {od} días\n"
                    f"🏷️ Descuento: {disc}%",
                    "Listo", parent=self)
            except Exception as e:
                MD.show_error(f"Error: {e}", "Error", parent=self)

        ttk.Button(tab, text="💾 Guardar configuración",
                   command=guardar,
                   bootstyle="success").pack(pady=20, padx=20, anchor="w")

    # ============================================================
    # CAJERO
    # ============================================================
    def _build_tab_cajero(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="👤 Cajero")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="👤 Cajero actual",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 4))
        tk.Label(tab, text="Aparece en los tickets que se imprimen.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))

        self.var_cashier = tk.StringVar(
            value=self.db.get_setting("cashier_name", "") or "")
        ttk.Entry(tab, textvariable=self.var_cashier, width=40,
                  font=("Arial", 12)).pack(pady=8)

        def guardar():
            self.db.set_setting("cashier_name", self.var_cashier.get().strip())
            MD.show_info(f"✅ Cajero: {self.var_cashier.get() or '(vacío)'}",
                         "Listo", parent=self)

        ttk.Button(tab, text="💾 Guardar", command=guardar,
                   bootstyle="success").pack(pady=12)

    # ============================================================
    # BACKUP
    # ============================================================
    def _build_tab_backup(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="💾 Backup")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="💾 Respaldo automático",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 4))
        tk.Label(tab,
                 text="Copia de seguridad de la base de datos cada día.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8").pack(pady=(0, 10))

        self.var_auto_backup = tk.BooleanVar(
            value=(self.db.get_setting("auto_backup_enabled", "1") == "1"))
        ttk.Checkbutton(tab, text="✅ Activar respaldo automático diario",
                        variable=self.var_auto_backup,
                        bootstyle="success-round-toggle",
                        command=self._toggle_auto_backup).pack(pady=8)

        tk.Label(tab, text="Carpeta de respaldos:",
                 font=("Arial", 10), bg=bg, fg=fg).pack(
                     anchor="w", padx=20, pady=(15, 4))

        self.var_backup_folder = tk.StringVar(
            value=self.db.get_setting("backup_folder", "") or "")
        f = tk.Frame(tab, bg=bg)
        f.pack(fill="x", padx=20, pady=4)
        ttk.Entry(f, textvariable=self.var_backup_folder, width=55,
                  font=("Arial", 10)).pack(side="left", fill="x", expand=True)

        def elegir():
            folder = filedialog.askdirectory(parent=self)
            if folder:
                self.var_backup_folder.set(folder)

        ttk.Button(f, text="📁", command=elegir,
                   bootstyle="info", width=3).pack(side="left", padx=4)

        def guardar():
            self.db.set_setting("auto_backup_enabled",
                                "1" if self.var_auto_backup.get() else "0")
            self.db.set_setting("backup_folder",
                                self.var_backup_folder.get().strip())
            MD.show_info("✅ Configuración de respaldo guardada.",
                         "Listo", parent=self)

        ttk.Button(tab, text="💾 Guardar", command=guardar,
                   bootstyle="success").pack(pady=12, padx=20, anchor="w")

    def _toggle_auto_backup(self):
        val = self.var_auto_backup.get()
        self.db.set_setting("auto_backup_enabled", "1" if val else "0")
        if val:
            MD.show_info("✅ Respaldo automático ACTIVADO.", "Backup", parent=self)
        else:
            MD.show_info("❌ Respaldo automático DESACTIVADO.", "Backup", parent=self)

    # ============================================================
    # AUTO-EXPORT (NUEVO)
    # ============================================================
    def _build_tab_auto_export(self):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="📤 Auto-Export")

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(tab, text="📤 Exportación automática",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 4))
        tk.Label(tab,
                 text="Copia la base de datos a una carpeta o USB\n"
                      "automáticamente según la frecuencia elegida.",
                 font=("Arial", 9, "italic"), bg=bg, fg="#a8e6a8",
                 justify="center").pack(pady=(0, 10))

        self.var_auto_export = tk.BooleanVar(
            value=(self.db.get_setting("auto_export_enabled", "0") == "1"))
        ttk.Checkbutton(tab, text="✅ Activar exportación automática",
                        variable=self.var_auto_export,
                        bootstyle="success-round-toggle",
                        command=self._toggle_auto_export).pack(pady=8)

        tk.Label(tab, text="Carpeta o USB de destino:",
                 font=("Arial", 10), bg=bg, fg=fg).pack(
                     anchor="w", padx=20, pady=(15, 4))

        self.var_export_folder = tk.StringVar(
            value=self.db.get_setting("auto_export_folder", "") or "")
        f = tk.Frame(tab, bg=bg)
        f.pack(fill="x", padx=20, pady=4)
        ttk.Entry(f, textvariable=self.var_export_folder, width=55,
                  font=("Arial", 10)).pack(side="left", fill="x", expand=True)

        def elegir():
            folder = filedialog.askdirectory(parent=self)
            if folder:
                self.var_export_folder.set(folder)

        ttk.Button(f, text="📁", command=elegir,
                   bootstyle="info", width=3).pack(side="left", padx=4)

        tk.Label(tab, text="Frecuencia:",
                 font=("Arial", 10), bg=bg, fg=fg).pack(
                     anchor="w", padx=20, pady=(15, 4))

        self.var_export_freq = tk.StringVar(
            value=self.db.get_setting("auto_export_frequency", "each_sale")
            or "each_sale")
        freq_frame = tk.Frame(tab, bg=bg)
        freq_frame.pack(anchor="w", padx=20)
        opciones_freq = [
            ("each_sale", "🛒 En cada venta"),
            ("on_close", "🚪 Al cerrar la aplicación"),
            ("hourly", "⏰ Cada hora"),
            ("daily", "📅 Una vez al día"),
        ]
        for val, txt in opciones_freq:
            ttk.Radiobutton(freq_frame, text=txt, variable=self.var_export_freq,
                            value=val, bootstyle="info").pack(anchor="w", pady=2)

        info = tk.Frame(tab, bg="#1e3a5c", padx=10, pady=8)
        info.pack(fill="x", padx=20, pady=(15, 4))
        tk.Label(info,
                 text="ℹ️ Se copia el archivo ventas.db completo a la carpeta\n"
                      "elegida con el nombre ventas_YYYY-MM-DD_HH-MM-SS.db.\n"
                      "Se mantienen los últimos 30 archivos automáticamente.",
                 font=("Arial", 9), bg="#1e3a5c", fg="#c8e6c9",
                 justify="left").pack(anchor="w")

        def guardar():
            self.db.set_setting("auto_export_enabled",
                                "1" if self.var_auto_export.get() else "0")
            self.db.set_setting("auto_export_folder",
                                self.var_export_folder.get().strip())
            self.db.set_setting("auto_export_frequency",
                                self.var_export_freq.get())
            MD.show_info("✅ Configuración de exportación guardada.",
                         "Listo", parent=self)

        ttk.Button(tab, text="💾 Guardar", command=guardar,
                   bootstyle="success").pack(pady=15, padx=20, anchor="w")

        def probar_ahora():
            folder = self.var_export_folder.get().strip()
            if not folder:
                MD.show_error("Selecciona una carpeta primero.", "Error",
                              parent=self)
                return
            if not os.path.isdir(folder):
                MD.show_error(f"La carpeta no existe:\n{folder}", "Error",
                              parent=self)
                return
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                destino = os.path.join(folder, f"ventas_{timestamp}.db")
                db_path = getattr(self.db, "db_path", None)
                if not db_path or not os.path.exists(db_path):
                    MD.show_error("No se encontró la base de datos.", "Error",
                                  parent=self)
                    return
                self.db.close_connection()
                shutil.copy2(db_path, destino)
                self.db.get_connection()
                MD.show_info(f"✅ Copia creada:\n{destino}",
                             "Exportación exitosa", parent=self)
            except Exception as e:
                MD.show_error(f"Error al exportar:\n{e}", "Error", parent=self)

        ttk.Button(tab, text="🧪 Probar exportación ahora",
                   command=probar_ahora,
                   bootstyle="info").pack(pady=5, padx=20, anchor="w")

    def _toggle_auto_export(self):
        val = self.var_auto_export.get()
        self.db.set_setting("auto_export_enabled", "1" if val else "0")
        if val:
            MD.show_info("✅ Exportación automática ACTIVADA.", "Auto-Export",
                         parent=self)
        else:
            MD.show_info("❌ Exportación automática DESACTIVADA.", "Auto-Export",
                         parent=self)