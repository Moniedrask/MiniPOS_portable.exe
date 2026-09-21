```markdown
# 🛒 MiniPOS Portable

**Punto de Venta e Inventario ligero, portable y 100% offline para pequeños comercios.**

Sin instalación, sin servidores, sin internet. Solo descarga el `.exe`, ponlo en una carpeta o USB y ejecútalo.

---

## ✨ Características

### 🛒 Módulo de PAGOS
- Carrito de compras con total en tiempo real.
- Escaneo automático con lector USB y búsqueda con autocompletado.
- Métodos de pago: **Efectivo, Transferencia, Tarjeta, Otro y Fiado**.
- Descuento automático de stock al confirmar la venta.
- **Abonos a deudas anteriores** con cálculo en tiempo real.

### 📦 Módulo de INVENTARIO
- Agregar, editar, eliminar y ver detalle de productos.
- **Unidades de medida:** por unidad, peso (kg/gr/mg) o volumen (Lt/ml).
- Ordenamiento por cualquier columna (clic en encabezados).
- Fechas automáticas de creación y actualización.
- Tooltip con marquesina en nombres largos.

### 💳 Fiados
- Agrupación automática por cliente.
- Registro de **abonos parciales** y marcado como pagado.
- Detección de deudas previas al fiar un nuevo producto.
- Vista de detalle con todos los productos fiados.

### 📊 Resumen de Ventas
- Tarjetas de resumen: **Hoy, Mes, Total y Fiados pendientes**.
- Agrupado por cliente con Total / Pagado / Pendiente.
- Filtros rápidos: Todas, Hoy, Este mes.
- Selección múltiple con checkboxes y acciones en lote.

### 🎨 Interfaz
- Modo **Oscuro / Claro** con botones personalizados.
- **Tamaño de fuente** ajustable (8 a 20).
- **Contraseña de inicio** configurable.
- **Auto-inicio** con Windows.
- Pantalla completa con `F11`.
- Todos los popups centrados y con modo oscuro forzado.

### 💾 Datos y Respaldos
- **100% Portable:** la base de datos se guarda junto al `.exe`.
- Exportar / Importar base de datos completa.
- **Auto-guardado** del carrito y formularios a medio llenar.
- Reporte del día (TXT) y del mes (Excel).

### 🔄 Contador de Ventas
- Reinicio del número visual de venta (`#01`) sin borrar el historial.
- Reportes actualizados con la numeración nueva.

---

## ⌨️ Atajos de teclado

| Tecla | Acción |
|---|---|
| `F2` | Agregar producto (en Inventario) |
| `F11` | Pantalla completa |
| `Ctrl + 1` | Ir a PAGOS |
| `Ctrl + 2` | Ir a INVENTARIO |
| `Ctrl + F12` | Eliminar la venta/fiado más reciente del cliente |
| `Shift + F12` | Eliminar todos los marcados |
| `Enter` | Confirmar diálogo |
| `Escape` | Cancelar diálogo |

---

## 📥 Instalación

1. Ve a la sección **[Releases](../../releases)** y descarga el archivo **`miniPOS_portable-v2.0.exe`**.
2. Crea una carpeta en tu PC o USB (ej. `C:\MiniPOS` o `D:\PuntoDeVenta`).
3. Mueve el `.exe` a esa carpeta.
4. Doble clic para ejecutar. La primera vez se creará la carpeta `data` con tu base de datos.
5. ¡Listo! Empieza a agregar productos y pásalos con tu lector de códigos de barras.

> **⚠️ Nota sobre Windows Defender:** Como el ejecutable no cuenta con firma digital de pago, Windows puede mostrar una advertencia azul la primera vez. Es un **falso positivo** normal en programas creados con PyInstaller. Solo haz clic en **"Más información"** → **"Ejecutar de todas formas"**.

---

## 🛠️ Stack Tecnológico

- **Lenguaje:** Python 3.11
- **Interfaz Gráfica:** Tkinter + ttkbootstrap
- **Base de Datos:** SQLite 3 (local, sin servidores externos)
- **Empaquetado:** PyInstaller (`--onefile`, portable para Windows)
- **Compilación automática:** GitHub Actions

---

## 📁 Estructura del proyecto

```

MiniPOS_portable/
├── main.py
├── data/
│   └── ventas.db            # Se crea automáticamente
├── domain/
│   └── models/
│       ├── product.py
│       └── sale.py
├── infrastucture/
│   └── db/
│       └── db_manager.py
├── application/
│   └── use_case/
│       ├── product_use_case.py
│       └── sale_use_case.py
└── src/
└── presentation/
└── views/
├── widgets.py
├── main_view.py
├── inventory_view.py
└── payment_view.py

```

---

## 🔧 Compilación manual

Si quieres compilar tu propio `.exe` desde el código fuente:

### Requisitos
- Python 3.11 o superior
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/MiniPOS_portable.git
cd MiniPOS_portable

# 2. Instalar dependencias
pip install ttkbootstrap openpyxl pyinstaller pystray Pillow

# 3. Compilar
cd MiniPOS_portable
pyinstaller --noconsole --onefile --paths=src --name="miniPOS_portable-v2.0" main.py
```

El ejecutable quedará en MiniPOS_portable/dist/miniPOS_portable-v2.0.exe.

---

🤝 Contribuciones

Las contribuciones son bienvenidas. Si encuentras un bug o tienes una sugerencia:

1. Abre un Issue describiendo el problema o la mejora.
2. Si quieres aportar código, haz un Fork y envía un Pull Request.

---

📄 Licencia

Este proyecto está distribuido bajo la licencia MIT.

---

📞 Soporte

Si tienes problemas o preguntas, abre un Issue en este repositorio.

---

¡Gracias por usar MiniPOS Portable! 🎉

```

---

Solo recuerda reemplazar `TU_USUARIO` por tu nombre de usuario de GitHub en la sección de compilación manual.
