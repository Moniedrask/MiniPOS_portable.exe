"""
Widgets y utilidades compartidas para MiniPOS.
Incluye:
- Helpers de ventana (centrado, título oscuro, popups suaves)
- Diálogos personalizados (MD)
- Barra de menús oscura (DarkMenuBar)
- Autocompletado de entradas (AutoCompleteEntry)
- Tooltips (HoverTooltip, TreeviewTooltip, ListboxTooltip)
- Funciones de negocio (info del negocio, header)
- Helpers de scroll (make_scrolled_treeview, make_scrollable)
- NUEVAS: generate_ticket_pdf, generate_labels_pdf, ChartsWindow, ReturnsWindow
"""
import os
import sys
import tkinter as tk
import ttkbootstrap as ttk
from datetime import datetime


# =========================================================
# CONTROL DE POPUPS ABIERTOS
# =========================================================
_popup_depth = 0


def _inc_popup():
    global _popup_depth
    _popup_depth += 1


def _dec_popup():
    global _popup_depth
    _popup_depth = max(0, _popup_depth - 1)


def popup_is_open():
    """True si hay al menos un popup custom abierto."""
    return _popup_depth > 0


# =========================================================
# VENTANA: TÍTULO OSCURO / CENTRADO / POPUP SUAVE
# =========================================================
def force_dark_titlebar(win):
    """Fuerza la barra de título oscura en Windows 10/11."""
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        if not hwnd:
            hwnd = win.winfo_id()
        v = ctypes.c_int(1)
        for a in (20, 19):
            try:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, a, ctypes.byref(v), ctypes.sizeof(v))
            except Exception:
                pass
    except Exception:
        pass


def apply_titlebar_theme(window, is_dark=True):
    """Aplica el tema (oscuro/claro) a la barra de título."""
    force_dark_titlebar(window)


def auto_resize_popup(win, margin=10):
    """Ajusta el popup para que no salga de la pantalla."""
    try:
        win.update_idletasks()
        geo = win.geometry()
        try:
            size = geo.split("+")[0]
            if "x" in size:
                cw, ch = size.split("x")
                cw = int(cw); ch = int(ch)
            else:
                cw = win.winfo_width(); ch = win.winfo_height()
        except Exception:
            cw = win.winfo_width(); ch = win.winfo_height()
        sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
        max_w = sw - margin * 2
        max_h = sh - margin * 2 - 40
        w = min(cw, max_w); h = min(ch, max_h)
        if cw <= max_w and ch <= max_h:
            return
        x = (sw - w) // 2
        y = max(margin, (sh - h) // 2 - 20)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        pass


def center_window(win):
    """Centra la ventana en la pantalla."""
    try:
        win.update_idletasks()
        w = win.winfo_width(); h = win.winfo_height()
        if w <= 1 or h <= 1:
            w = win.winfo_reqwidth(); h = win.winfo_reqheight()
        sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
        max_w = sw - 20; max_h = sh - 80
        w = min(w, max_w); h = min(h, max_h)
        x = (sw - w) // 2
        y = max(0, (sh - h) // 2 - 20)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        pass


def show_popup_smooth(popup, is_dark=True):
    """Muestra un Toplevel con centrado, título oscuro y efecto suave."""
    _inc_popup()

    def on_destroy(e):
        if e.widget is popup:
            _dec_popup()

    try:
        popup.bind("<Destroy>", on_destroy, add="+")
    except Exception:
        pass

    try:
        popup.attributes('-alpha', 1.0)
    except Exception:
        pass

    auto_resize_popup(popup)

    try:
        popup.deiconify()
    except Exception:
        pass
    try:
        popup.update()
    except Exception:
        pass

    popup.after(80, lambda: auto_resize_popup(popup) if popup.winfo_exists() else None)
    popup.after(250, lambda: auto_resize_popup(popup) if popup.winfo_exists() else None)

    try:
        style = ttk.Style()
        popup.configure(bg=style.colors.bg)
    except Exception:
        pass

    force_dark_titlebar(popup)

    try:
        popup.lift()
        popup.attributes('-topmost', True)
        popup.focus_force()
    except Exception:
        pass

    def quitar_topmost():
        try:
            if popup.winfo_exists():
                popup.attributes('-topmost', False)
                popup.lift()
                popup.focus_force()
        except Exception:
            pass

    popup.after(300, quitar_topmost)
    popup.after(80, lambda: force_dark_titlebar(popup) if popup.winfo_exists() else None)
    popup.after(160, lambda: force_dark_titlebar(popup) if popup.winfo_exists() else None)


def get_menu_font():
    """Devuelve la fuente de los menús (familia, tamaño)."""
    try:
        import tkinter.font as tkfont
        f = tkfont.nametofont("TkMenuFont")
        return (f.cget("family"), f.cget("size"))
    except Exception:
        return ("Arial", 11)


# =========================================================
# INFORMACIÓN DEL NEGOCIO
# =========================================================
def get_business_info(db_manager):
    """Lee la info del negocio desde settings."""
    empty = {"type": "", "name": "", "owner": "", "place": "",
             "phone": "", "employees": "", "notes": ""}
    if db_manager is None:
        return dict(empty)
    try:
        return {
            "type": db_manager.get_setting("biz_type", "") or "",
            "name": db_manager.get_setting("biz_name", "") or "",
            "owner": db_manager.get_setting("biz_owner", "") or "",
            "place": db_manager.get_setting("biz_place", "") or "",
            "phone": db_manager.get_setting("biz_phone", "") or "",
            "employees": db_manager.get_setting("biz_employees", "") or "",
            "notes": db_manager.get_setting("biz_notes", "") or "",
        }
    except Exception:
        return dict(empty)


def save_business_info(db_manager, data):
    """Guarda la info del negocio en settings."""
    if db_manager is None:
        return
    for k in ("type", "name", "owner", "place", "phone", "employees", "notes"):
        try:
            db_manager.set_setting(f"biz_{k}", str(data.get(k, "") or ""))
        except Exception:
            pass


def get_business_display_text(db_manager):
    """Devuelve el texto 'tipo, nombre' formateado."""
    try:
        info = get_business_info(db_manager)
        tipo = (info.get("type") or "").strip()
        nombre = (info.get("name") or "").strip()
        if tipo and nombre:
            return f"{tipo}, {nombre}"
        if nombre:
            return nombre
        if tipo:
            return tipo
        return ""
    except Exception:
        return ""


def make_inline_business_header(parent, db_manager, bg=None):
    """
    Header compacto para la barra superior: 'tipo, nombre'
    tipo en gris, nombre en verde subrayado.
    Devuelve dict con widgets + refresh().
    """
    if bg is None:
        try:
            bg = ttk.Style().colors.bg
        except Exception:
            bg = "#1a1a1a"

    frame = tk.Frame(parent, bg=bg)
    tipo_lbl = tk.Label(frame, text="", font=("Arial", 11), bg=bg, fg="#888888")
    tipo_lbl.pack(side="left")
    coma_lbl = tk.Label(frame, text="", font=("Arial", 11), bg=bg, fg="#888888")
    coma_lbl.pack(side="left")
    nombre_lbl = tk.Label(frame, text="", font=("Arial", 11, "underline"),
                          bg=bg, fg="#7dd87d")
    nombre_lbl.pack(side="left")

    def refresh():
        info = get_business_info(db_manager)
        tipo = (info.get("type") or "").strip()
        nombre = (info.get("name") or "").strip()
        if tipo and nombre:
            tipo_lbl.configure(text=tipo)
            coma_lbl.configure(text=", ")
            nombre_lbl.configure(text=nombre)
        elif nombre:
            tipo_lbl.configure(text="")
            coma_lbl.configure(text="")
            nombre_lbl.configure(text=nombre)
        elif tipo:
            tipo_lbl.configure(text=tipo)
            coma_lbl.configure(text="")
            nombre_lbl.configure(text="")
        else:
            tipo_lbl.configure(text="")
            coma_lbl.configure(text="")
            nombre_lbl.configure(text="")

    refresh()
    return {"frame": frame, "refresh": refresh}


def make_business_header(parent, db_manager, on_click=None, bg=None):
    """Alias de compatibilidad."""
    return make_inline_business_header(parent, db_manager, bg=bg)


# =========================================================
# SCROLLBARS ROJO OSCURO
# =========================================================
def apply_dark_red_scrollbar_style():
    try:
        style = ttk.Style()
        style.configure("DarkRed.Vertical.TScrollbar",
                        background="#5c1a1a",
                        troughcolor="#1a0505",
                        bordercolor="#1a0505",
                        arrowcolor="#a8e6a8",
                        darkcolor="#5c1a1a",
                        lightcolor="#7a2020",
                        gripcount=0,
                        relief="flat")
        style.map("DarkRed.Vertical.TScrollbar",
                  background=[("active", "#8b2020"), ("pressed", "#6e1515")],
                  arrowcolor=[("active", "#ffffff")])
    except Exception:
        pass


def make_scrolled_treeview(parent, columns, headings, bootstyle="dark"):
    """
    Crea un Treeview con scrollbar rojo oscuro.
    headings: lista de (col_id, texto, ancho, anchor)
    Devuelve (frame, tree).
    """
    apply_dark_red_scrollbar_style()

    frame = ttk.Frame(parent, bootstyle=bootstyle)

    sb = ttk.Scrollbar(frame, orient="vertical",
                       style="DarkRed.Vertical.TScrollbar")
    sb.pack(side="right", fill="y")

    tree = ttk.Treeview(frame, columns=columns, show='headings',
                        yscrollcommand=sb.set)
    for c, t, w, a in headings:
        tree.heading(c, text=t)
        tree.column(c, width=w, anchor=a)
    tree.pack(side="left", fill="both", expand=True)
    sb.config(command=tree.yview)

    def _on_mousewheel(event):
        try:
            tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    tree.bind("<MouseWheel>", _on_mousewheel)
    return frame, tree


# =========================================================
# HELPER: ZONA SCROLLEABLE
# =========================================================
def make_scrollable(container, build_content, build_bottom=None, bg=None):
    """
    Convierte `container` en un área scrolleable.
    - build_content(parent) construye el contenido central
    - build_bottom(parent) construye el pie fijo (opcional)
    """
    apply_dark_red_scrollbar_style()
    if bg is None:
        try:
            bg = ttk.Style().colors.bg
        except Exception:
            bg = "#1a1a1a"

    result = {"canvas": None, "inner": None, "scrollbar": None, "bottom": None}

    if build_bottom is not None:
        bottom_frame = tk.Frame(container, bg=bg)
        bottom_frame.pack(side="bottom", fill="x", pady=4)
        try:
            build_bottom(bottom_frame)
        except Exception:
            pass
        result["bottom"] = bottom_frame

    scrollbar = ttk.Scrollbar(container, orient="vertical",
                              style="DarkRed.Vertical.TScrollbar")
    scrollbar.pack(side="right", fill="y")

    canvas = tk.Canvas(container, bg=bg, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg=bg)
    inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(event):
        try:
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass

    def _on_canvas_configure(event):
        try:
            canvas.itemconfigure(inner_id, width=event.width)
        except Exception:
            pass

    inner.bind("<Configure>", _on_inner_configure)
    canvas.bind("<Configure>", _on_canvas_configure)
    scrollbar.config(command=canvas.yview)

    def _on_mousewheel(event):
        try:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    canvas.bind("<MouseWheel>", _on_mousewheel)
    inner.bind("<MouseWheel>", _on_mousewheel)

    try:
        build_content(inner)
    except Exception:
        pass

    result["canvas"] = canvas
    result["inner"] = inner
    result["scrollbar"] = scrollbar

    # Ajustar scrollregion al inicio
    try:
        canvas.after(100, lambda: canvas.configure(scrollregion=canvas.bbox("all")))
    except Exception:
        pass

    return result


# =========================================================
# DIÁLOGOS PERSONALIZADOS (con bloqueo anti-doble ejecución)
# =========================================================
def _custom_dialog(parent, title, message, buttons, kind="info",
                   is_dark=True, default_button=0):
    if parent is None:
        return None
    try:
        root = parent.winfo_toplevel()
    except Exception:
        root = parent

    style = ttk.Style()
    bg = style.colors.bg
    fg = style.colors.fg

    pop = tk.Toplevel(root)
    pop.title(title)
    pop.transient(root)
    pop.withdraw()
    pop.configure(bg=bg)

    icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "question": "❓"}

    tk.Label(pop, text=f"{icons.get(kind, '')}  {title}",
             font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(20, 10), padx=20)
    tk.Label(pop, text=message, font=("Arial", 11),
             bg=bg, fg=fg, wraplength=460, justify="center").pack(padx=25, pady=10)

    result = {"idx": None}
    state = {"closing": False}

    bf = tk.Frame(pop, bg=bg)
    bf.pack(pady=(10, 20))

    btn_widgets = []

    def close_with(i):
        if state["closing"]:
            return
        state["closing"] = True
        result["idx"] = i
        try:
            pop.destroy()
        except Exception:
            pass

    def make_cb(i):
        def cb():
            close_with(i)
        return cb

    for i, b in enumerate(buttons):
        if i == 0:
            btn_style = "DarkGreen.TButton"
        elif b.lower() in ("no", "cancelar"):
            btn_style = "danger.TButton"
        else:
            btn_style = "secondary.TButton"
        try:
            btn = ttk.Button(bf, text=b, command=make_cb(i),
                             style=btn_style, width=12)
        except Exception:
            btn = ttk.Button(bf, text=b, command=make_cb(i), width=12)
        btn.pack(side="left", padx=8)
        btn_widgets.append(btn)

    pop.update_idletasks()
    w = max(420, pop.winfo_reqwidth())
    h = pop.winfo_reqheight()
    pop.geometry(f"{w}x{h}")

    def on_enter(e):
        if state["closing"]:
            return "break"
        try:
            btn_widgets[default_button].invoke()
        except Exception:
            pass
        return "break"

    def on_escape(e):
        if state["closing"]:
            return "break"
        try:
            pop.destroy()
        except Exception:
            pass
        return "break"

    pop.bind("<Return>", on_enter)
    pop.bind("<KP_Enter>", on_enter)
    pop.bind("<Escape>", on_escape)

    show_popup_smooth(pop)

    try:
        pop.grab_set()
        pop.focus_force()
    except Exception:
        pass

    def set_focus():
        try:
            if not state["closing"] and btn_widgets and pop.winfo_exists():
                btn_widgets[default_button].focus_set()
        except Exception:
            pass

    pop.after(50, set_focus)
    pop.after(250, set_focus)

    try:
        root.wait_window(pop)
    except Exception:
        pass

    try:
        if not popup_is_open() and parent and parent.winfo_exists():
            parent_tl = parent.winfo_toplevel()
            if parent_tl.winfo_exists():
                parent_tl.grab_set()
                parent_tl.lift()
                parent_tl.focus_force()
    except Exception:
        pass

    return result["idx"]


class MD:
    """Message Dialogs personalizados."""
    _is_dark = True

    @classmethod
    def set_dark(cls, is_dark):
        cls._is_dark = is_dark

    @classmethod
    def show_info(cls, message, title="Información", parent=None):
        _custom_dialog(parent, title, message, ["Bien"], "info", cls._is_dark)

    @classmethod
    def show_warning(cls, message, title="Advertencia", parent=None):
        _custom_dialog(parent, title, message, ["Bien"], "warning", cls._is_dark)

    @classmethod
    def show_error(cls, message, title="Error", parent=None):
        _custom_dialog(parent, title, message, ["Bien"], "error", cls._is_dark)

    @classmethod
    def yesno(cls, message, title="Confirmar", parent=None, default_yes=True):
        idx = _custom_dialog(parent, title, message, ["Sí", "No"],
                             "question", cls._is_dark,
                             default_button=0 if default_yes else 1)
        return "Yes" if idx == 0 else "No"


# =========================================================
# BARRA DE MENÚS OSCURA
# =========================================================
class DarkMenuBar(ttk.Frame):
    def __init__(self, parent, is_dark_func):
        super().__init__(parent, bootstyle="dark")
        self.is_dark_func = is_dark_func
        self.menus = []

    def add_menu(self, label, build_fn):
        mb = ttk.Menubutton(self, text=label, bootstyle="dark", padding=(6, 1))
        try:
            mb.configure(width=10)
        except Exception:
            pass
        style = ttk.Style()
        menu = tk.Menu(
            mb, tearoff=0,
            bg=style.colors.bg, fg=style.colors.fg,
            activebackground=style.colors.selectbg,
            activeforeground=style.colors.selectfg,
            bd=1, relief="solid",
            font=get_menu_font())
        build_fn(menu)
        mb.configure(menu=menu)
        mb.pack(side="left", padx=2, pady=1)
        self.menus.append((mb, menu))
        return mb


# =========================================================
# TOOLTIP
# =========================================================
class HoverTooltip:
    def __init__(self, widget, font_size=11, delay=350):
        self.widget = widget
        self.font_size = font_size
        self.delay = delay
        self.tip = None
        self.label = None
        self.marquee_timer = None
        self.show_timer = None
        self.current_key = None
        self._pending_x = 0
        self._pending_y = 0
        self._last_text = None
        try:
            import tkinter.font as tkfont
            self.font = tkfont.Font(family="Arial", size=font_size)
        except Exception:
            self.font = None
        widget.bind("<Motion>", self._on_motion, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button>", self._hide, add="+")

    def _identify(self, event):
        return None, None, False

    def _on_motion(self, event):
        key, text, truncated = self._identify(event)
        if key == self.current_key:
            return
        self._hide()
        self.current_key = key
        self._last_text = text
        if not truncated or not text:
            return
        self._pending_x = event.x_root
        self._pending_y = event.y_root
        self.show_timer = self.widget.after(self.delay, self._deferred_show)

    def _deferred_show(self):
        self.show_timer = None
        if not self._last_text:
            return
        self._show(self._pending_x, self._pending_y, self._last_text)

    def _show(self, x, y, text):
        style = ttk.Style()
        bg = style.colors.bg
        fg = style.colors.fg
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        try:
            self.tip.attributes("-topmost", True)
        except Exception:
            pass
        self.tip.configure(bg=bg)
        self.label = tk.Label(
            self.tip, text=text, bg=bg, fg=fg,
            font=("Arial", self.font_size),
            padx=8, pady=4,
            borderwidth=1, relief="solid",
            highlightthickness=0)
        self.label.pack()
        self.tip.update_idletasks()
        tw = self.tip.winfo_reqwidth()
        th = self.tip.winfo_reqheight()
        sw = self.tip.winfo_screenwidth()
        sh = self.tip.winfo_screenheight()
        px = min(x + 15, sw - tw - 10)
        py = min(y + 15, sh - th - 10)
        self.tip.geometry(f"+{max(px, 0)}+{max(py, 0)}")
        self._offset = 0
        if len(text) > 45:
            self._padded = text + "        "
            self._marquee()

    def _marquee(self):
        if not self.label or not self.tip:
            return
        full = self._padded
        offset = self._offset
        self.label.configure(text=full[offset:] + full[:offset])
        self._offset = (offset + 1) % len(full)
        self.marquee_timer = self.widget.after(160, self._marquee)

    def _hide(self, event=None):
        if self.show_timer:
            try:
                self.widget.after_cancel(self.show_timer)
            except Exception:
                pass
            self.show_timer = None
        if self.marquee_timer:
            try:
                self.widget.after_cancel(self.marquee_timer)
            except Exception:
                pass
            self.marquee_timer = None
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None
            self.label = None
        self.current_key = None
        self._last_text = None


class TreeviewTooltip(HoverTooltip):
    def _identify(self, event):
        row = self.widget.identify_row(event.y)
        col = self.widget.identify_column(event.x)
        key = (row, col)
        if not row or not col:
            return key, None, False
        try:
            col_idx = int(col.replace("#", "")) - 1
            vals = self.widget.item(row, "values")
            if col_idx >= len(vals):
                return key, None, False
            text = str(vals[col_idx])
            col_id = self.widget["columns"][col_idx]
            col_width = self.widget.column(col_id, "width")
        except Exception:
            return key, None, False
        if self.font:
            text_width = self.font.measure(text)
        else:
            text_width = len(text) * self.font_size * 0.65
        truncated = (text_width > col_width - 8) and len(text) > 6
        return key, text, truncated


class ListboxTooltip(HoverTooltip):
    def _identify(self, event):
        try:
            idx = self.widget.nearest(event.y)
            if idx < 0 or idx >= self.widget.size():
                return None, None, False
            text = self.widget.get(idx)
        except Exception:
            return None, None, False
        try:
            lb_width = self.widget.winfo_width()
        except Exception:
            lb_width = 200
        if self.font:
            text_width = self.font.measure(text)
        else:
            text_width = len(text) * self.font_size * 0.65
        truncated = (text_width > lb_width - 10) and len(text) > 6
        return idx, text, truncated


# =========================================================
# AUTOCOMPLETADO ENTRY
# =========================================================
class AutoCompleteEntry(ttk.Entry):
    def __init__(self, parent, values_getter, on_select, width=40, font=None, **kwargs):
        if font is None:
            font = ("Arial", 11)
        super().__init__(parent, width=width, font=font, **kwargs)
        self.values_getter = values_getter
        self.on_select_cb = on_select
        self.popup = None
        self.listbox = None
        self._listbox_tooltip = None
        self.bind('<KeyRelease>', self._on_key)
        self.bind('<Down>', self._on_down)
        self.bind('<Up>', self._on_up)
        self.bind('<Escape>', self._hide)
        self.bind('<FocusOut>', self._on_focus_out)
        self.bind('<Return>', self._on_return)

    def _on_key(self, event):
        if event.keysym in ('Down', 'Up', 'Return', 'Escape', 'Tab',
                            'Shift_L', 'Shift_R', 'Control_L', 'Control_R',
                            'Alt_L', 'Alt_R', 'Left', 'Right'):
            return
        self._update()

    def _update(self):
        text = self.get().lower().strip()
        if not text:
            self._hide()
            return
        try:
            vals = self.values_getter()
        except Exception:
            vals = []
        filtered = [v for v in vals if text in v.lower()][:500]
        if not filtered:
            self._hide()
            return
        self._show(filtered)

    def _show(self, values):
        style = ttk.Style()
        if self.popup is None:
            self.popup = tk.Toplevel(self)
            self.popup.wm_overrideredirect(True)
            try:
                self.popup.attributes('-topmost', True)
            except Exception:
                pass
            self.popup.configure(bg=style.colors.bg)

            container = tk.Frame(self.popup, bg=style.colors.bg)
            container.pack(fill='both', expand=True)

            sb = tk.Scrollbar(container, orient="vertical",
                              bg="#5c1a1a",
                              troughcolor="#1a0505",
                              activebackground="#8b2020",
                              borderwidth=0,
                              highlightthickness=0,
                              elementborderwidth=0)
            sb.pack(side="right", fill="y")

            self.listbox = tk.Listbox(
                container, activestyle='none', exportselection=False,
                bg=style.colors.bg, fg=style.colors.fg,
                selectbackground="#0a4d1f", selectforeground="#ffffff",
                font=("Arial", 11), borderwidth=0, relief="flat",
                highlightthickness=0, yscrollcommand=sb.set)
            self.listbox.pack(side="left", fill='both', expand=True)
            sb.config(command=self.listbox.yview)

            def _on_mousewheel(event):
                try:
                    self.listbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
                except Exception:
                    pass
            self.listbox.bind("<MouseWheel>", _on_mousewheel)

            self.listbox.bind('<<ListboxSelect>>', self._on_select)
            self.listbox.bind('<Return>', self._on_select)
            self.listbox.bind('<Escape>', lambda e: (self._hide(), "break"))
            self.listbox.bind('<Double-Button-1>', self._on_select)
            self._listbox_tooltip = ListboxTooltip(self.listbox, font_size=11)
        else:
            self.listbox.configure(bg=style.colors.bg, fg=style.colors.fg)

        self.listbox.delete(0, tk.END)
        for v in values:
            self.listbox.insert(tk.END, v)

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        item_h = 22
        h = min(len(values) * item_h + 6, 300)
        self.popup.geometry(f"{w}x{h}+{x}+{y}")
        self.popup.deiconify()
        self.popup.lift()

    def _hide(self, event=None):
        if self.popup is not None:
            self.popup.withdraw()

    def _on_select(self, event=None):
        try:
            sel = self.listbox.curselection()
            if sel:
                value = self.listbox.get(sel[0])
                self.delete(0, tk.END)
                self.insert(0, value)
                self.icursor(tk.END)
                self.on_select_cb(value)
                self._hide()
        except Exception:
            pass

    def _on_down(self, event=None):
        if self.popup is not None and self.popup.winfo_viewable() and self.listbox.size() > 0:
            self.listbox.focus_set()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            return "break"

    def _on_up(self, event=None):
        if self.popup is not None and self.popup.winfo_viewable() and self.listbox.size() > 0:
            self.listbox.focus_set()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(tk.END)
            self.listbox.activate(tk.END)
            return "break"

    def _on_return(self, event=None):
        text = self.get().strip()
        if text:
            self.on_select_cb(text)
        self._hide()

    def _on_focus_out(self, event=None):
        self.after(200, self._hide_if_unfocused)

    def _hide_if_unfocused(self):
        try:
            fw = self.focus_get()
            if fw != self.listbox:
                self._hide()
        except Exception:
            self._hide()


# =========================================================
# IDEA 1: TICKET EN PDF
# =========================================================
def generate_ticket_pdf(sale, items, payments=None, business_name="MI NEGOCIO",
                        business_info="", output_path=None, is_copy=False,
                        cashier_name="", business_phone="", business_address=""):
    """
    Genera un PDF con el ticket de venta.
    - sale: objeto Sale
    - items: lista de SaleItem o dicts
    - payments: lista de dicts [{"method":..., "amount":...}] o None
    """
    try:
        from reportlab.lib.pagesizes import letter
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

    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Producto")
    c.drawString(300, y, "Cant.")
    c.drawString(360, y, "P. Unit.")
    c.drawRightString(width - 40, y, "Subtotal")
    y -= 12

    c.setFont("Helvetica", 9)
    for it in items:
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


# =========================================================
# IDEA 5: ETIQUETAS PDF (Avery 5160, 30 por hoja)
# =========================================================
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
        HAS_BARCODE = True
    except ImportError:
        HAS_BARCODE = False

    LABEL_W = 2.625 * inch
    LABEL_H = 1.0 * inch
    MARGIN_LEFT = 0.1875 * inch
    MARGIN_TOP = 0.5 * inch
    COLS = 3
    ROWS = 10
    LABELS_PER_PAGE = COLS * ROWS

    c = canvas.Canvas(output_path, pagesize=letter)

    todas = []
    for p in products:
        for _ in range(copies):
            todas.append(p)

    for idx, prod in enumerate(todas):
        pos = idx % LABELS_PER_PAGE
        if pos == 0 and idx > 0:
            c.showPage()

        col = pos % COLS
        row = pos // COLS

        x = MARGIN_LEFT + col * LABEL_W
        y_top = letter[1] - MARGIN_TOP - row * LABEL_H

        c.setFont("Helvetica-Bold", 7)
        nombre = (prod.name or "")[:30]
        c.drawString(x + 4, y_top - 10, nombre)

        precio = getattr(prod, "rounded_price", 0) or prod.price
        if not precio:
            precio = prod.price
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(x + LABEL_W - 4, y_top - 12, f"${precio:,.0f}")

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


# =========================================================
# IDEA 11: VENTANA DE GRÁFICOS
# =========================================================
class ChartsWindow(tk.Toplevel):
    def __init__(self, master, sale_case):
        super().__init__(master)
        self.sale_case = sale_case

        self.title("📊 Gráficos y estadísticas")
        self.geometry("1100x750")
        self.transient(master)

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

        top = tk.Frame(self, bg="#f0f0f0")
        top.pack(fill="x")

        tk.Label(top, text="Rango:", bg="#f0f0f0",
                 font=("Arial", 9, "bold")).pack(side="left", padx=6, pady=8)
        self.var_range = tk.StringVar(value="7 días")
        ttk.Combobox(top, textvariable=self.var_range, state="readonly",
                     values=["Hoy", "7 días", "30 días", "Mes actual", "Todo"],
                     width=12).pack(side="left")
        self.var_range.trace_add("write", lambda *a: self.reload())

        ttk.Button(top, text="🔄 Refrescar", command=self.reload,
                   bootstyle="secondary").pack(side="left", padx=8)
        ttk.Button(top, text="📕 Exportar PDF", command=self.export_pdf,
                   bootstyle="danger").pack(side="right", padx=8, pady=6)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

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
                     fg="#c62828", font=("Arial", 12, "bold")).pack(pady=20)

        self.reload()
        show_popup_smooth(self)

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
        fechas = [d["date"][5:] for d in data]
        totales = [d["total"] for d in data]
        ax.plot(fechas, totales, marker="o", color="#2196F3", linewidth=2)
        ax.fill_between(range(len(fechas)), totales, alpha=0.2, color="#2196F3")
        ax.set_title("Ventas de los últimos 30 días", fontsize=12, fontweight="bold")
        ax.set_ylabel("$ Pesos")
        ax.grid(alpha=0.3)
        if len(fechas) > 10:
            step = max(1, len(fechas) // 10)
            ax.set_xticks(range(0, len(fechas), step))
            ax.set_xticklabels([fechas[i] for i in range(0, len(fechas), step)],
                               rotation=45)
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

    def export_pdf(self):
        if not self.HAS_MPL:
            MD.show_error("matplotlib no está instalado.", "Exportar", parent=self)
            return

        from tkinter import filedialog
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"graficos_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        if not ruta:
            return

        try:
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            MD.show_error("No se pudo importar PdfPages.", "Exportar", parent=self)
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

            MD.show_info(f"PDF generado:\n{ruta}", "Exportar", parent=self)
        except Exception as e:
            MD.show_error(f"No se pudo exportar:\n{e}", "Error", parent=self)


# =========================================================
# IDEA 10: VENTANA DE DEVOLUCIONES
# =========================================================
class ReturnsWindow(tk.Toplevel):
    def __init__(self, master, sale_case, on_done=None):
        super().__init__(master)
        self.sale_case = sale_case
        self.on_done = on_done

        self.title("↩️ Devoluciones / Notas crédito")
        self.geometry("1100x700")
        self.transient(master)

        top = tk.Frame(self, bg="#f0f0f0")
        top.pack(fill="x")

        tk.Label(top, text="🔍 Buscar venta (cliente / # / fecha):",
                 bg="#f0f0f0", font=("Arial", 10, "bold")).pack(side="left", padx=8, pady=8)
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *a: self.load())
        tk.Entry(top, textvariable=self.var_search, width=30,
                 font=("Arial", 11)).pack(side="left", padx=6)

        ttk.Button(top, text="🔄 Refrescar", command=self.load,
                   bootstyle="secondary").pack(side="right", padx=8)

        # Lista de ventas
        self.frame_tree, self.tree = make_scrolled_treeview(
            self,
            columns=("ID", "Fecha", "Cliente", "Método", "Total", "Estado"),
            headings=[
                ("ID", "#", 60, "center"),
                ("Fecha", "Fecha", 150, "center"),
                ("Cliente", "Cliente", 200, "center"),
                ("Método", "Método", 120, "center"),
                ("Total", "Total", 110, "center"),
                ("Estado", "Estado", 130, "center"),
            ],
            bootstyle="dark")
        self.frame_tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree.bind("<Double-1>", lambda e: self.open_return_dialog())

        bf = tk.Frame(self, bg="#f0f0f0")
        bf.pack(fill="x", pady=8)
        ttk.Button(bf, text="↩️ Registrar devolución",
                   command=self.open_return_dialog,
                   bootstyle="danger").pack(side="left", padx=8)
        ttk.Button(bf, text="Cerrar", command=self.destroy,
                   bootstyle="secondary").pack(side="right", padx=8)

        self.load()
        show_popup_smooth(self)

    def load(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        q = self.var_search.get().strip().lower()
        sales = self.sale_case.get_all_sales(limit=500)
        for s in sales:
            if q:
                texto = f"{s.display_number} {s.date} {s.customer_name}".lower()
                if q not in texto:
                    continue
            estado = "✅ OK"
            if s.is_returned:
                estado = "↩️ Devuelta"
            elif any(getattr(it, "returned_qty", 0) for it in s.items):
                estado = "↩️ Parcial"
            self.tree.insert("", "end", iid=str(s.sale_id), values=(
                f"#{s.display_number:02d}",
                s.date,
                s.customer_name or "-",
                s.payment_method,
                f"${s.total:,.0f}",
                estado))

    def open_return_dialog(self):
        sel = self.tree.selection()
        if not sel:
            MD.show_warning("Selecciona una venta primero.", "Sin selección", parent=self)
            return
        sale_id = int(sel[0])
        sale = self.sale_case.get_sale_by_id(sale_id)
        if not sale:
            return
        ReturnDialog(self, self.sale_case, sale, on_success=self._after_return)

    def _after_return(self):
        self.load()
        if self.on_done:
            self.on_done()


class ReturnDialog(tk.Toplevel):
    def __init__(self, master, sale_case, sale, on_success=None):
        super().__init__(master)
        self.sale_case = sale_case
        self.sale = sale
        self.on_success = on_success

        self.title(f"↩️ Devolución - Venta #{sale.display_number:02d}")
        self.geometry("700x600")
        self.transient(master)

        tk.Label(self, text=f"Venta #{sale.display_number:02d} - {sale.date}",
                 font=("Arial", 13, "bold")).pack(pady=8)
        tk.Label(self, text=f"Cliente: {sale.customer_name or '(sin nombre)'}",
                 font=("Arial", 10)).pack()

        tk.Label(self, text="Selecciona los productos a devolver:",
                 font=("Arial", 10, "bold")).pack(pady=(10, 4))

        self.frame_tree, self.tree = make_scrolled_treeview(
            self,
            columns=("Sel", "Producto", "Comprado", "Devuelto", "Pendiente", "P. Unit"),
            headings=[
                ("Sel", "✓", 40, "center"),
                ("Producto", "Producto", 250, "w"),
                ("Comprado", "Comprado", 90, "center"),
                ("Devuelto", "Ya devuelto", 90, "center"),
                ("Pendiente", "Pendiente", 90, "center"),
                ("P. Unit", "P. Unit.", 100, "center"),
            ],
            bootstyle="dark")
        self.frame_tree.pack(fill="both", expand=True, padx=10, pady=6)

        self._items_map = {}
        self._marked = set()
        for it in sale.items:
            pendiente = it.pending_qty if hasattr(it, "pending_qty") else it.quantity
            self._items_map[str(it.item_id)] = it
            self.tree.insert("", "end", iid=str(it.item_id), values=(
                "☐",
                it.product_name,
                f"{it.quantity:g}",
                f"{it.returned_qty:g}",
                f"{pendiente:g}",
                f"${it.unit_price:,.0f}"))
            if pendiente <= 0:
                self.tree.item(str(it.item_id), tags=("ok",))

        self.tree.bind("<Button-1>", self._on_click)

        # Cantidad
        tk.Label(self, text="Cantidades a devolver (uno por uno o 'todo'):",
                 font=("Arial", 10, "bold")).pack(pady=(8, 4))
        self.frame_qty = tk.Frame(self)
        self.frame_qty.pack(fill="x", padx=10)
        self.qty_vars = {}
        for it in sale.items:
            pendiente = it.pending_qty if hasattr(it, "pending_qty") else it.quantity
            if pendiente <= 0:
                continue
            f = tk.Frame(self.frame_qty)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=f"{it.product_name[:40]}", width=40, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.qty_vars[it.item_id] = v
            tk.Entry(f, textvariable=v, width=8, justify="center").pack(side="left", padx=6)
            tk.Label(f, text=f"/ {pendiente:g}").pack(side="left")

        # Motivo
        tk.Label(self, text="Motivo (opcional):", font=("Arial", 10)).pack(pady=(10, 2))
        self.var_reason = tk.StringVar()
        tk.Entry(self, textvariable=self.var_reason, width=60).pack(pady=4)

        bf = tk.Frame(self)
        bf.pack(pady=12)
        ttk.Button(bf, text="↩️ Registrar devolución",
                   command=self._do_return,
                   bootstyle="danger").pack(side="left", padx=8)
        ttk.Button(bf, text="Cancelar", command=self.destroy,
                   bootstyle="secondary").pack(side="left", padx=8)

        show_popup_smooth(self)

    def _on_click(self, event):
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row or col != "#1":
            return
        item = self._items_map.get(row)
        if not item:
            return
        pendiente = item.pending_qty if hasattr(item, "pending_qty") else item.quantity
        if pendiente <= 0:
            return
        if row in self._marked:
            self._marked.discard(row)
            self.tree.set(row, "Sel", "☐")
            if item.item_id in self.qty_vars:
                self.qty_vars[item.item_id].set("0")
        else:
            self._marked.add(row)
            self.tree.set(row, "Sel", "☑")
            if item.item_id in self.qty_vars:
                self.qty_vars[item.item_id].set(f"{pendiente:g}")

    def _do_return(self):
        items = []
        for item_id, var in self.qty_vars.items():
            try:
                qty = float(var.get() or 0)
            except ValueError:
                qty = 0
            if qty > 0:
                items.append({"item_id": item_id, "quantity": qty})

        if not items:
            MD.show_warning("No seleccionaste productos para devolver.",
                            "Sin devoluciones", parent=self)
            return

        ok, msg, total = self.sale_case.register_return(
            self.sale.sale_id, items,
            reason=self.var_reason.get().strip(),
            return_type="producto")
        if ok:
            MD.show_info(f"{msg}", "Devolución registrada", parent=self)
            self.destroy()
            if self.on_success:
                self.on_success()
        else:
            MD.show_error(msg, "Error", parent=self)