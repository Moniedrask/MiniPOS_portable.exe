import tkinter as tk
import ttkbootstrap as ttk


def apply_titlebar_theme(window, is_dark):
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        v = ctypes.c_int(1 if is_dark else 0)
        for a in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, a, ctypes.byref(v), ctypes.sizeof(v))
    except Exception:
        pass


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


def show_popup_smooth(popup, is_dark):
    """Muestra un popup sin parpadeo y con fondo correcto."""
    try:
        style = ttk.Style()
        popup.configure(bg=style.colors.bg)
    except Exception:
        pass
    popup.update_idletasks()
    center_window(popup)
    apply_titlebar_theme(popup, is_dark)
    popup.deiconify()
    popup.lift()
    try:
        popup.focus_force()
    except Exception:
        pass


def get_menu_font():
    try:
        import tkinter.font as tkfont
        f = tkfont.nametofont("TkMenuFont")
        return (f.cget("family"), f.cget("size"))
    except Exception:
        return ("Arial", 11)


# =========================================================
# DIÁLOGOS PERSONALIZADOS (con fondo oscuro correcto)
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
    try:
        pop.grab_set()
    except Exception:
        pass

    icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "question": "❓"}

    header = tk.Label(pop, text=f"{icons.get(kind, '')}  {title}",
                      font=("Arial", 13, "bold"),
                      bg=bg, fg=fg)
    header.pack(pady=(20, 10), padx=20)

    msg_lbl = tk.Label(pop, text=message, font=("Arial", 11),
                       bg=bg, fg=fg,
                       wraplength=460, justify="center")
    msg_lbl.pack(padx=25, pady=10)

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
    show_popup_smooth(pop, is_dark)

    try:
        root.wait_window(pop)
    except Exception:
        pass
    return result["idx"]


class MD:
    """Messagebox con botones en español, fondo oscuro."""

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
        # ✅ Botón compacto (padding reducido y fuente pequeña)
        mb = ttk.Menubutton(self, text=label, bootstyle="dark",
                            padding=(6, 1))
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
# AUTOCOMPLETADO ENTRY CON LISTBOX OSCURO
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
        filtered = [v for v in vals if text in v.lower()][:15]
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
            self.listbox = tk.Listbox(
                self.popup,
                activestyle='none',
                exportselection=False,
                bg=style.colors.bg,
                fg=style.colors.fg,
                selectbackground="#0a4d1f",
                selectforeground="#ffffff",
                font=("Arial", 11),
                borderwidth=0,
                relief="flat",
                highlightthickness=0)
            self.listbox.pack(fill='both', expand=True)
            self.listbox.bind('<<ListboxSelect>>', self._on_select)
            self.listbox.bind('<Return>', self._on_select)
            self.listbox.bind('<Escape>', lambda e: (self._hide(), "break"))
            self.listbox.bind('<Double-Button-1>', self._on_select)
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