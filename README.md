# 🛒 MiniPOS Portable

**Punto de Venta e Inventario ligero, portable y 100% offline para pequeños comercios.**

Sin instalación, sin servidores, sin internet. Solo descarga el ejecutable, ponlo en una carpeta (o USB) y ejecútalo. Todos los datos quedan guardados junto al programa.

---

## ✨ Características

### 🛒 Módulo de PAGOS
- Carrito con total en tiempo real
- Escaneo con lector de código de barras USB + autocompletado
- **Pago mixto**: divide el pago en varios métodos (hasta 3)
- Métodos: Efectivo, Transferencia, Tarjeta, Otro y **Fiado**
- Descuento automático de stock al cobrar
- **Abonos** a deudas anteriores con cálculo en vivo
- **Panel de ventas recientes** (reimprimir / devolver)
- **Ticket PDF** generado automáticamente (opcional)

### 📦 Módulo de INVENTARIO
- Agregar, editar, eliminar, pausar y ver detalle de productos
- **Modo Paquete / Caja**: costos por paquete, unidades y stock total calculado
- **Redondeo de precio** por producto (10, 50, 100, 500, 1000)
- **Sugerencia inteligente** de paquete al escribir un nombre ya comprado antes
- **Vencimiento**: alertas configurables (15/7/2 días), oferta automática
- **Unidades**: unidad, peso (kg/gr/mg), volumen (Lt/ml)
- **Etiquetas PDF** (Avery 5160, 30 por hoja con código de barras)
- **Historial de precios** con exportación a TXT / Excel / PDF
- Ordenamiento por columnas, filtros por grupo y estado
- Auto-guardado de formularios

### 💳 Fiados
- Agrupación automática por cliente
- Registro de abonos parciales y marcado como pagado
- Detección de deudas previas al fiar
- Checkboxes para selección múltiple
- Hotkeys: `Ctrl+F12` (eliminar venta reciente), `Shift+F12` (eliminar marcados)

### ↩️ Devoluciones
- Total o parcial por producto
- Restaura stock automáticamente
- Notas de crédito
- Aviso "producto devuelto X veces"
- Descuenta del cierre de caja

### 💰 Base de Caja
- Apertura con monto inicial
- Cuadre con efectivo contado vs. esperado
- Retiros, gastos e ingresos manuales
- Cierre de caja del día con reporte completo

### 📊 Gráficos y Estadísticas
- Top 10 productos más vendidos
- Ventas últimos 30 días (línea)
- Ventas por hora del día
- **Ganancias reales** (venta - costo - devoluciones)
- Exportación a PDF

### 🎨 Interfaz
- Modo **Oscuro / Claro**
- **Tamaño de fuente** ajustable (9 a 18)
- **Ventana de Ajustes** unificada con pestañas:
  - Apariencia · Seguridad · Inicio · Ventas · Negocio
  - Ticket · Vencimiento · Cajero · Backup
  - **Auto-Export**
- **Contraseña de inicio** + **contraseña de admin** para acciones sensibles
- **Ejecutar con el Sistema Operativo (SO)** — Windows y Linux
- Pantalla completa con `F11`
- Popups centrados con modo oscuro forzado

### 💾 Datos y Respaldos
- **100% Portable**: la base de datos se guarda junto al ejecutable
- Exportar / Importar base de datos completa
- **Auto-guardado** del carrito y formularios a medio llenar
- **Respaldo automático diario** (configurable)
- **Exportación automática** de la base de datos a carpeta o USB:
  - En cada venta
  - Al cerrar la aplicación
  - Cada hora
  - Una vez al día
  - Mantiene los últimos 30 archivos automáticamente
- Reporte del día (TXT) y del mes (Excel)

---

## 📥 Descarga

Ve a la sección **[Releases](../../releases)** y descarga el archivo para tu sistema operativo:

| Sistema | Archivo | Compatible con |
|---|---|---|
| 🪟 Windows moderno | `miniPOS_portable-v2.5.exe` | Windows 10, 11 |
| 🪟 Windows 7 SP1 | `miniPOS_portable-v2.5-win7.exe` | Windows 7 SP1, 8, 8.1, 10, 11 |
| 🐧 Linux | `miniPOS_portable-v2.5-x86_64.AppImage` | Ubuntu 20.04+, Debian 11+, Fedora 35+, Linux Mint 20+, etc. |

### 🪟 Instalación en Windows (10 / 11)

1. Descarga `miniPOS_portable-v2.5.exe`.
2. Crea una carpeta en tu PC o USB (ej. `C:\MiniPOS` o `D:\PuntoDeVenta`).
3. Mueve el `.exe` a esa carpeta.
4. Doble clic para ejecutar. La primera vez se creará la carpeta `data` con tu base de datos.

### 🪟 Instalación en Windows 7 SP1

1. Descarga `miniPOS_portable-v2.5-win7.exe` desde Releases.
2. Ponlo en una carpeta o USB (ej. `C:\MiniPOS`).
3. Doble clic para ejecutar.

> **⚠️ Importante**: la versión estándar (`miniPOS_portable-v2.5.exe`) **NO funciona en Windows 7**.
> Debes descargar específicamente el archivo `-win7.exe`.

> **⚠️ Nota sobre Windows Defender:** Como el ejecutable no cuenta con firma digital de pago, Windows puede mostrar una advertencia azul la primera vez. Es un **falso positivo** normal en programas creados con PyInstaller. Solo haz clic en **"Más información"** → **"Ejecutar de todas formas"**.

### 🐧 Instalación en Linux (AppImage)

1. Descarga el archivo `miniPOS_portable-v2.5-x86_64.AppImage`.
2. Dale permisos de ejecución:
   ```bash
   chmod +x miniPOS_portable-v2.5-x86_64.AppImage
   ```
3. Ejecútalo:
   ```bash
   ./miniPOS_portable-v2.5-x86_64.AppImage
   ```

**Ventajas del AppImage:**
- ✅ **No requiere instalación**
- ✅ **No modifica el sistema**
- ✅ **Funciona en cualquier distro moderna**
- ✅ **Un solo archivo portable**
- ✅ **Icono integrado** (aparece en el dock/barra de tareas)

> **Tip opcional**: Instala [AppImageLauncher](https://github.com/TheAssassin/AppImageLauncher) para integrar el AppImage al menú de aplicaciones del sistema con su icono.

---

## ⌨️ Atajos de teclado

| Tecla | Acción |
|---|---|
| `F2` | Agregar producto (en Inventario) |
| `F3` | Ir al buscador (en Pagos) |
| `F11` | Pantalla completa |
| `F12` | Cobrar |
| `Ctrl + 1` | Ir a PAGOS |
| `Ctrl + 2` | Ir a INVENTARIO |
| `Ctrl + F12` | Eliminar venta/fiado más reciente del cliente |
| `Shift + F12` | Eliminar todos los marcados |
| `Enter` | Confirmar diálogo |
| `Escape` | Cancelar diálogo |

---

## 🛠️ Stack Tecnológico

- **Lenguaje:**
  - Python 3.11 (Windows 10/11 + Linux)
  - Python 3.8 (Windows 7 SP1)
- **Interfaz:** Tkinter + ttkbootstrap
- **Base de Datos:** SQLite 3 (local, sin servidores externos)
- **Empaquetado:** PyInstaller + AppImage
- **Compilación:** GitHub Actions

**Dependencias:**
- `ttkbootstrap` — temas modernos para Tkinter
- `reportlab` — generación de PDFs (tickets, etiquetas, reportes)
- `matplotlib` — gráficos
- `openpyxl` — Excel
- `Pillow` + `pystray` — bandeja del sistema
- `pyinstaller` — compilación

**Nota**: Las versiones de las librerías se ajustan según el Python usado:
- `requirements.txt` → Python 3.11 (versiones modernas)
- `requirements-win7.txt` → Python 3.8 (versiones compatibles con Windows 7)

---

## 📁 Estructura del proyecto

```
MiniPOS_portable.exe/
├── .github/
│   └── workflows/
│       └── build.yml                    # Compilación automática
├── MiniPOS_portable/                    # Código fuente
│   ├── main.py                          # Punto de entrada
│   ├── miniPOS_portable.png             # Icono (Linux)
│   ├── miniPOS_portable.ico             # Icono (Windows)
│   ├── data/
│   │   └── ventas.db                    # Base de datos (se crea automáticamente)
│   └── src/
│       ├── domain/
│       │   └── models/
│       │       ├── product.py
│       │       └── sale.py
│       ├── infrastucture/
│       │   └── db/
│       │       └── db_manager.py
│       ├── application/
│       │   └── use_case/
│       │       ├── product_use_case.py
│       │       └── sale_use_case.py
│       └── presentation/
│           └── views/
│               ├── widgets.py
│               ├── password_utils.py
│               ├── main_view.py
│               ├── inventory_view.py
│               ├── payment_view.py
│               └── settings_view.py
├── requirements.txt                     # Deps para Python 3.11
├── requirements-win7.txt                # Deps para Python 3.8 (Win7)
├── README.md
└── .gitignore
```

---

## 🔧 Compilación manual

Si quieres compilar tú mismo el ejecutable desde el código fuente:

### Requisitos
- Python 3.11 (o 3.8 para Windows 7 SP1)
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Moniedrask/MiniPOS_portable.exe.git
cd MiniPOS_portable.exe/MiniPOS_portable

# 2. Instalar dependencias (elige una)
pip install -r ../requirements.txt          # Para Python 3.11
pip install -r ../requirements-win7.txt     # Para Python 3.8 (Win7)

# 3. Compilar (Windows moderno)
pyinstaller --noconsole --onefile --paths=src --icon="miniPOS_portable.ico" --name="miniPOS_portable-v2.5" main.py

# 3. Compilar (Windows 7 SP1)
pyinstaller --noconsole --onefile --paths=src --icon="miniPOS_portable.ico" --name="miniPOS_portable-v2.5-win7" main.py

# 3. Compilar (Linux)
pyinstaller --onefile --paths=src --name="miniPOS_portable-v2.5" main.py
```

El ejecutable quedará en `dist/`.

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Si encuentras un bug o tienes una sugerencia:

- Abre un **Issue** describiendo el problema o la mejora.
- Si quieres aportar código, haz un **Fork** y envía un **Pull Request**.

---

## 📄 Licencia

Este proyecto está distribuido bajo la licencia **MIT**.

---

## 📞 Soporte

Si tienes problemas o preguntas, abre un **Issue** en este repositorio.

---

## 📌 Notas adicionales

- **Windows 7 SP1**: Los usuarios de Windows 7 SP1 deben descargar específicamente el archivo `-win7.exe`. Las versiones modernas (`.exe` normal) **no funcionan en Windows 7**.
- **Linux**: El AppImage funciona en la mayoría de distribuciones modernas (Ubuntu 20.04+, Debian 11+, Fedora 35+, Linux Mint 20+, etc.). Para sistemas muy antiguos (Ubuntu 18.04 o anteriores), puede requerir dependencias extra.
- **Base de datos**: si actualizas desde una versión antigua, la app migra automáticamente la base de datos existente agregando las columnas y tablas nuevas que falten, sin perder datos.
- **macOS**: No está soportado por el momento.

---

¡Gracias por usar MiniPOS Portable! 🎉
