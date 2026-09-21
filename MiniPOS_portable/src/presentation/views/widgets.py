import tkinter as tk
import ttkbootstrap as ttk


# =========================================================
# CONTADOR GLOBAL DE POPUPS
# =========================================================
_popup_depth = 0


def _inc_popup():
    global _popup_depth
    _popup_depth += 1


def _dec_popup():
    global _popup_depth
    _popup_depth = max(0, _popup_depth - 1)


def popup_is_open():
    return _popup_depth > 0


# =========================================================
# BARRA DE TÍTULO OSCURA
# =========================================================
def force_dark_titlebar(win):
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
    force_dark_titlebar(window)


def center_window(win):
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    if w <= 1 or h <= 1:
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


def show_popup_smooth(popup, is_dark=True):
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

    popup.update_idletasks()
    center_window(popup)

    try:
        popup.deiconify()
    except Exception:
        pass
    try:
        popup.update()
    except Exception:
        pass

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
    try:
        import tkinter.font as tkfont
        f = tkfont.nametofont("TkMenuFont")
        return (f.cget("family"), f.cget("size"))
    except Exception:
        return ("Arial", 11)


# =========================================================
# TREEVIEW CON SCROLLBAR
# =========================================================
def make_scrolled_treeview(parent, columns, headings, bootstyle="dark"):
    """
    Crea un Treeview con scrollbar vertical y soporte de rueda del ratón.
    Devuelve (frame, treeview).
    """
    frame = ttk.Frame(parent, bootstyle=bootstyle)

    sb = ttk.Scrollbar(frame, orient="vertical")
    sb.pack(side="right", fill="y")

    tree = ttk.Treeview(frame, columns=columns, show='headings',
                        yscrollcommand=sb.set)
    for c, t, w, a in headings:
        tree.heading(c, text=t)
        tree.column(c, width=w, anchor=a)
    tree.pack(side="left", fill="both", expand=True)
    sb.config(command=tree.yview)

    # Rueda del ratón
    def _on_mousewheel(event):
        try:
            tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    tree.bind("<MouseWheel>", _on_mousewheel)

    return frame, tree


# =========================================================
# DIÁLOGOS PERSONALIZADOS
# =========================================================
def _custom_dialog(parent, title, message, buttons, kind="info", is_dark=True):
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
    bf = tk.Frame(pop, bg=bg)
    bf.pack(pady=(10, 20))

    def make_cb(i):
        def cb():
            result["idx"] = i
            pop.destroy()
        return cb

    for i, b in enumerate(buttons):
        if i == 0:
            btn_style = "DarkGreen.TButton"
        elif b.lower() in ("no", "cancelar"):
            btn_style = "danger.TButton"
        else:
            btn_style = "secondary.TButton"
        ttk.Button(bf, text=b, command=make_cb(i),
                   style=btn_style, width=12).pack(side="left", padx=8)

    pop.update_idletasks()
    w = max(420, pop.winfo_reqwidth())
    h = pop.winfo_reqheight()
    pop.geometry(f"{w}x{h}")

    show_popup_smooth(pop)

    try:
        pop.grab_set()
        pop.focus_force()
    except Exception:
        pass

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
    def yesno(cls, message, title="Confirmar", parent=None):
        idx = _custom_dialog(parent, title, message, ["Sí", "No"],
                             "question", cls._is_dark)
        return "Yes" if idx == 0 else "No"


# =========================================================
# BARRA DE MENÚS OSCURA Y COMPACTA
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
# TOOLTIP CON MARQUESINA
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
# AUTOCOMPLETADO ENTRY CON LISTBOX OSCURO + SCROLLBAR
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
        # ✅ Permitir hasta 500 sugerencias (antes 15), la scrollbar maneja el resto
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

            # Contenedor interno con scrollbar
            container = tk.Frame(self.popup, bg=style.colors.bg)
            container.pack(fill='both', expand=True)

            sb = tk.Scrollbar(container, orient="vertical")
            sb.pack(side="right", fill="y")

            self.listbox = tk.Listbox(
                container,
                activestyle='none',
                exportselection=False,
                bg=style.colors.bg,
                fg=style.colors.fg,
                selectbackground="#0a4d1f",
                selectforeground="#ffffff",
                font=("Arial", 11),
                borderwidth=0,
                relief="flat",
                highlightthickness=0,
                yscrollcommand=sb.set)
            self.listbox.pack(side="left", fill='both', expand=True)
            sb.config(command=self.listbox.yview)

            # ✅ Rueda del ratón en el listbox
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
        # ✅ Altura limitada a 300px (aprox 13 ítems); el resto se ve con scroll
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