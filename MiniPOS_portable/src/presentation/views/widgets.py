import tkinter as tk
import ttkbootstrap as ttk


def apply_titlebar_theme(window, is_dark):
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        v = ctypes.c_int(1 if is_dark else 0)
        for a in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, a, ctypes.byref(v), ctypes.sizeof(v))
    except Exception:
        pass


def center_window(win):
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x, y = (sw - w) // 2, (sh - h) // 2
    win.geometry(f"+{x}+{y}")


def show_popup_smooth(popup, is_dark):
    """Muestra un popup ya construido sin parpadeo en la barra de título."""
    popup.withdraw()
    popup.update_idletasks()
    apply_titlebar_theme(popup, is_dark)
    center_window(popup)
    popup.deiconify()


def get_menu_font():
    """Devuelve la fuente actual de los menús para que escalen con el tamaño."""
    try:
        import tkinter.font as tkfont
        f = tkfont.nametofont("TkMenuFont")
        return (f.cget("family"), f.cget("size"))
    except Exception:
        return ("Arial", 11)


class AutoCompleteEntry(ttk.Entry):
    """Entry con autocompletado en un Toplevel-Listbox que NO roba el foco."""

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

    # --- Manejo de teclas ---
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
        if self.popup is None:
            self.popup = tk.Toplevel(self)
            self.popup.wm_overrideredirect(True)
            try:
                self.popup.attributes('-topmost', True)
            except Exception:
                pass
            self.listbox = tk.Listbox(self.popup, activestyle='none',
                                      exportselection=False,
                                      font=("Arial", 11),
                                      borderwidth=1, relief="solid")
            self.listbox.pack(fill='both', expand=True)
            self.listbox.bind('<<ListboxSelect>>', self._on_select)
            self.listbox.bind('<Return>', self._on_select)
            self.listbox.bind('<Escape>', lambda e: (self._hide(), "break"))
            self.listbox.bind('<Double-Button-1>', self._on_select)
        self.listbox.delete(0, tk.END)
        for v in values:
            self.listbox.insert(tk.END, v)
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        item_h = 20
        h = min(len(values) * item_h + 4, 300)
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

    def refresh_values(self):
        """Llamar cuando cambie la lista de valores disponibles."""
        pass