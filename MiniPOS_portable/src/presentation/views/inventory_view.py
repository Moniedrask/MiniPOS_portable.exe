# Al final del __init__ de InventoryView, después de self.after(300, ...):
        self._keep_scanner_focused()

    def _keep_scanner_focused(self):
        try:
            fw = self.focus_get()
            if fw is not None and not isinstance(fw, (ttk.Entry, tk.Entry, ttk.Combobox)):
                self.scan_entry.focus_set()
        except Exception:
            pass
        self.after(700, self._keep_scanner_focused)