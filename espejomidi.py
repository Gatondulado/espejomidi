import tkinter as tk
from tkinter import ttk
import mido
import threading
import ctypes
import sys
import io
import json
import os

# ─── Tooltip ──────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text   = text
        self.tw     = None
        widget.bind("<Enter>", self.mostrar)
        widget.bind("<Leave>", self.ocultar)

    def mostrar(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tw, text=self.text,
                       bg="#1e1e30", fg="#a78bfa",
                       font=("Courier New", 8),
                       relief="flat", padx=8, pady=4,
                       wraplength=220, justify="left")
        lbl.pack()

    def ocultar(self, event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

def tip(widget, texto):
    Tooltip(widget, texto)


# ─── DPI awareness ────────────────────────────────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# ─── Ocultar consola ──────────────────────────────────────────────────────────
try:
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    ctypes.windll.user32.ShowWindow(hwnd, 0)
except:
    pass

log_buffer = []
consola_win = None
log_text_ref = [None]

class LogCapture(io.StringIO):
    def write(self, txt):
        if txt.strip():
            log_buffer.append(txt.strip())
            if len(log_buffer) > 200:
                log_buffer.pop(0)
            try:
                if consola_win and consola_win.winfo_exists() and log_text_ref[0]:
                    log_text_ref[0].config(state="normal")
                    log_text_ref[0].insert("end", txt.strip() + "\n")
                    log_text_ref[0].see("end")
                    log_text_ref[0].config(state="disabled")
            except:
                pass
        return super().write(txt)

sys.stdout = LogCapture()
sys.stderr = LogCapture()

# ─── Config ───────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])), "espejo_config.json")

def cargar_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {"tema": "dark", "paneles": []}

def guardar_config():
    data = {"tema": tema_actual.get(), "paneles": []}
    for _, ctrl, refs, cb_e, cb_s, corr_v, oct_v in paneles:
        fijar = False
        try:
            fijar = fijar_do_var.get()
        except:
            pass
        data["paneles"].append({
            "entrada":    cb_e.get(),
            "salida":     cb_s.get(),
            "correccion": corr_v.get(),
            "octava":     oct_v.get(),
            "fijar_do":   fijar,
        })
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except:
        pass

# ─── Controlador MIDI ─────────────────────────────────────────────────────────
class ControladorMIDI:
    def __init__(self):
        self.activo = False
        self.hilo   = None
        self.parar  = threading.Event()

    def iniciar(self, entrada, salida, correccion, octava):
        self.detener()
        self.entrada      = entrada
        self.salida       = salida
        self.correccion   = correccion
        self.octava       = octava
        self.parar.clear()
        self.activo = True
        self.hilo = threading.Thread(target=self._correr, daemon=True)
        self.hilo.start()

    def detener(self):
        self.activo = False
        self.parar.set()
        if self.hilo and self.hilo.is_alive():
            self.hilo.join(timeout=1)

    def _correr(self):
        try:
            with mido.open_input(self.entrada) as inport, \
                 mido.open_output(self.salida) as outport:
                while not self.parar.is_set():
                    for msg in inport.iter_pending():
                        if msg.type in ('note_on', 'note_off'):
                            nota = 127 - msg.note - self.correccion + (self.octava * 12)
                            nota = max(0, min(127, nota))
                            outport.send(msg.copy(note=nota))
                        else:
                            outport.send(msg)
                    self.parar.wait(timeout=0.001)
        except Exception as e:
            print(f"Error: {e}")

# ─── Temas ────────────────────────────────────────────────────────────────────
TEMAS = {
    "dark": {
        "BG": "#0d0d14", "PANEL": "#14141e", "BORDER": "#2a2a40",
        "ACCENT": "#7c5cbf", "ACCENT2": "#a78bfa",
        "TEXT": "#e8e8f0", "SUBTEXT": "#7878a0",
        "GREEN": "#22c55e", "RED": "#ef4444",
        "ENTRY_BG": "#1e1e30", "BTN_TEMA": "☀  LIGHT", "SEP": "#2a2a40",
    },
    "light": {
        "BG": "#dcdce8", "PANEL": "#f0f0f5", "BORDER": "#c0c0d0",
        "ACCENT": "#7c5cbf", "ACCENT2": "#5b21b6",
        "TEXT": "#18182a", "SUBTEXT": "#50507a",
        "GREEN": "#16a34a", "RED": "#dc2626",
        "ENTRY_BG": "#e0e0ec", "BTN_TEMA": "🌙  DARK", "SEP": "#c0c0d0",
    }
}

# ─── Root ─────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("ESPEJO MIDI")
root.resizable(True, True)

cfg = cargar_config()
tema_actual = tk.StringVar(value=cfg.get("tema", "dark"))
all_widgets = []
paneles = []  # (frame, ctrl, refs, cb_e, cb_s, corr_var, oct_var)

def c(key):
    return TEMAS[tema_actual.get()][key]

def reg(w, tipo, opts=None):
    all_widgets.append((w, tipo, opts or {}))
    return w

def obtener_puertos():
    try:
        return mido.get_input_names(), mido.get_output_names()
    except Exception as e:
        print(f"Error detectando puertos: {e}")
        try:
            import rtmidi
            mi = rtmidi.MidiIn()
            mo = rtmidi.MidiOut()
            return mi.get_ports(), mo.get_ports()
        except:
            return [], []

# ─── Tema ─────────────────────────────────────────────────────────────────────
def aplicar_tema_widget(w, tipo, opts):
    col = TEMAS[tema_actual.get()]
    bg  = col.get(opts.get("bg", "BG"), col["BG"])
    fg  = col.get(opts.get("fg", "TEXT"), col["TEXT"])
    try:
        if   tipo == "frame":      w.configure(bg=bg)
        elif tipo == "panel":      w.configure(bg=bg, highlightbackground=col["BORDER"])
        elif tipo == "label":      w.configure(bg=bg, fg=fg)
        elif tipo == "accent_bar": w.configure(bg=col["ACCENT"])
        elif tipo == "sep":        w.configure(bg=col["SEP"])
        elif tipo == "entry_lbl":  w.configure(bg=col["ENTRY_BG"], fg=fg)
        elif tipo == "canvas":     w.configure(bg=bg)
        elif tipo == "btn":
            w.configure(bg=bg, fg=fg,
                        activebackground=col["ACCENT"],
                        activeforeground="#ffffff")
        elif tipo == "btn_accent":
            w.configure(bg=col["ACCENT"], fg="#ffffff",
                        activebackground=col["ACCENT2"],
                        activeforeground="#ffffff")
        elif tipo == "btn_danger":
            w.configure(bg=col["BORDER"], fg=col["SUBTEXT"],
                        activebackground=col["RED"],
                        activeforeground="#ffffff")
        elif tipo == "btn_tema":
            w.configure(bg=col["ACCENT"], fg="#ffffff",
                        text=col["BTN_TEMA"],
                        activebackground=col["ACCENT2"],
                        activeforeground="#ffffff")
    except:
        pass

def aplicar_tema():
    col = TEMAS[tema_actual.get()]
    root.configure(bg=col["BG"])
    main_canvas.configure(bg=col["BG"])
    scroll_frame.configure(bg=col["BG"])
    style = ttk.Style()
    style.configure("TCombobox",
        fieldbackground=col["ENTRY_BG"], background=col["ENTRY_BG"],
        foreground=col["TEXT"], selectbackground=col["ACCENT"],
        selectforeground="#ffffff", bordercolor=col["BORDER"],
        arrowcolor=col["ACCENT2"])
    style.map("TCombobox",
        fieldbackground=[("readonly", col["ENTRY_BG"]),
                         ("disabled", col["PANEL"])],
        foreground=[("readonly", col["TEXT"]),
                    ("disabled", col["SUBTEXT"])])
    for w, tipo, opts in all_widgets:
        aplicar_tema_widget(w, tipo, opts)
    for _, ctrl, refs, _, _, _, _ in paneles:
        _actualizar_btns(ctrl, refs)
    guardar_config()

def toggle_tema():
    tema_actual.set("light" if tema_actual.get() == "dark" else "dark")
    aplicar_tema()

def _actualizar_btns(ctrl, refs):
    col = TEMAS[tema_actual.get()]
    btn_on, btn_off, estado_lbl, estado_var, cb_e, cb_s = refs
    if ctrl.activo:
        estado_var.set("● ACTIVO")
        estado_lbl.config(fg=col["GREEN"])
        btn_on.config(state="disabled", bg=col["BORDER"],
                      fg=col["SUBTEXT"], activebackground=col["BORDER"])
        btn_off.config(state="normal", bg=col["RED"],
                       fg="#ffffff", activebackground="#c01010")
        cb_e.config(state="disabled")
        cb_s.config(state="disabled")
    else:
        estado_var.set("INACTIVO")
        estado_lbl.config(fg=col["RED"])
        btn_on.config(state="normal", bg=col["ACCENT"],
                      fg="#ffffff", activebackground=col["ACCENT2"])
        btn_off.config(state="disabled", bg=col["BORDER"],
                       fg=col["SUBTEXT"], activebackground=col["BORDER"])
        cb_e.config(state="readonly")
        cb_s.config(state="readonly")

# ─── Consola ──────────────────────────────────────────────────────────────────
def toggle_consola():
    global consola_win
    if consola_win and consola_win.winfo_exists():
        consola_win.destroy()
        return
    consola_win = tk.Toplevel(root)
    consola_win.title("Consola")
    consola_win.configure(bg="#0a0a0f")
    consola_win.geometry("620x280")
    lt = tk.Text(consola_win, bg="#0a0a0f", fg="#22c55e",
                 font=("Courier New", 9), relief="flat", wrap="word")
    lt.pack(fill="both", expand=True, padx=10, pady=(10,4))
    log_text_ref[0] = lt
    for line in log_buffer:
        lt.insert("end", line + "\n")
    lt.see("end")
    tk.Button(consola_win, text="LIMPIAR", bg="#1a1a2e", fg="#64748b",
              relief="flat", font=("Courier New", 8), padx=8, pady=4,
              command=lambda: [log_buffer.clear(),
                               lt.config(state="normal"),
                               lt.delete("1.0","end"),
                               lt.config(state="disabled")],
              cursor="hand2").pack(pady=(0,8))

# ─── Scroll ───────────────────────────────────────────────────────────────────
def actualizar_scroll():
    root.update_idletasks()
    sh = root.winfo_screenheight()
    sw = root.winfo_screenwidth()
    content_h = scroll_frame.winfo_reqheight()
    max_h = sh - 80
    new_h = min(content_h, max_h)
    new_w = min(640, sw - 60)
    x = (sw - new_w) // 2
    y = (sh - new_h) // 2
    root.geometry(f"{new_w}x{new_h}+{x}+{y}")
    if content_h > max_h:
        scrollbar.pack(side="right", fill="y")
        main_canvas.configure(yscrollcommand=scrollbar.set)
    else:
        scrollbar.pack_forget()
        main_canvas.configure(yscrollcommand="")
        main_canvas.yview_moveto(0)

# ─── Panel ────────────────────────────────────────────────────────────────────
def crear_panel(parent, config=None):
    ctrl = ControladorMIDI()

    panel = tk.Frame(parent, bd=0, highlightthickness=1)
    reg(panel, "panel", {"bg":"PANEL"})
    panel.pack(fill="x", padx=16, pady=(0, 10))

    reg(tk.Frame(panel, height=2), "accent_bar").pack(fill="x")

    hdr = reg(tk.Frame(panel), "frame", {"bg":"PANEL"})
    hdr.pack(fill="x", padx=16, pady=(12, 0))

    num_lbl = reg(tk.Label(hdr, text=f"CONTROLADOR {len(paneles)+1}",
                  font=("Courier New", 10, "bold")),
                  "label", {"bg":"PANEL","fg":"ACCENT2"})
    num_lbl.pack(side="left")

    estado_var = tk.StringVar(value="INACTIVO")
    estado_lbl = reg(tk.Label(hdr, textvariable=estado_var,
                     font=("Courier New", 9, "bold")),
                     "label", {"bg":"PANEL","fg":"RED"})
    estado_lbl.pack(side="right")

    body = reg(tk.Frame(panel), "frame", {"bg":"PANEL"})
    body.pack(fill="x", padx=16, pady=(8, 0))

    entradas, salidas = obtener_puertos()

    def sublbl(txt):
        reg(tk.Label(body, text=txt, font=("Courier New", 8)),
            "label", {"bg":"PANEL","fg":"SUBTEXT"}).pack(anchor="w", pady=(6,1))

    def combo(vals, saved=None):
        cb = ttk.Combobox(body, values=vals, state="readonly",
                          font=("Courier New", 9))
        cb.pack(fill="x")
        if saved and saved in vals:
            cb.set(saved)
        elif vals:
            cb.current(0)
        return cb

    sublbl("ENTRADA MIDI")
    cb_entrada = combo(entradas, config.get("entrada") if config else None)
    sublbl("SALIDA MIDI")
    cb_salida  = combo(salidas,  config.get("salida")  if config else None)

    reg(tk.Frame(body, height=1), "sep").pack(fill="x", pady=(10, 4))

    # Corrección + Octava centradas
    controles = reg(tk.Frame(body), "frame", {"bg":"PANEL"})
    controles.pack(anchor="center", pady=(2, 0))


    corr_var     = tk.IntVar(value=config.get("correccion", 3) if config else 3)
    oct_var      = tk.IntVar(value=config.get("octava",     0) if config else 0)
    fijar_do_var = tk.BooleanVar(value=config.get("fijar_do", False) if config else False)

    # Guardar la corrección base para el cálculo de Fijar Do
    corr_base = [corr_var.get()]

    def on_oct_change(d):
        nueva_oct = max(-4, min(4, oct_var.get() + d))
        oct_var.set(nueva_oct)
        if fijar_do_var.get():
            nueva_corr = corr_base[0] - (nueva_oct * 12)
            corr_var.set(max(-48, min(48, nueva_corr)))
        if ctrl.activo:
            ctrl.octava     = oct_var.get()
            ctrl.correccion = corr_var.get()

    def on_corr_change(d):
        corr_var.set(max(-48, min(48, corr_var.get() + d)))
        corr_base[0] = corr_var.get()
        if fijar_do_var.get():
            # Recalcular con la nueva base
            nueva_corr = corr_base[0] - (oct_var.get() * 12)
            corr_var.set(max(-48, min(48, nueva_corr)))
        if ctrl.activo:
            ctrl.correccion = corr_var.get()

    # Corrección de nota
    corr_col = reg(tk.Frame(controles), "frame", {"bg":"PANEL"})
    corr_col.pack(side="left", padx=12)
    reg(tk.Label(corr_col, text="CORRECCIÓN DE NOTA", font=("Courier New", 8)),
        "label", {"bg":"PANEL","fg":"SUBTEXT"}).pack()
    corr_row = reg(tk.Frame(corr_col), "frame", {"bg":"PANEL"})
    corr_row.pack()
    reg(tk.Button(corr_row, text="−", relief="flat", width=3,
        font=("Courier New", 12), cursor="hand2",
        command=lambda: on_corr_change(-1)),
        "btn", {"bg":"ENTRY_BG","fg":"TEXT"}).pack(side="left")
    reg(tk.Label(corr_row, textvariable=corr_var,
        font=("Courier New", 13, "bold"), width=4),
        "entry_lbl", {"fg":"ACCENT2"}).pack(side="left", padx=1)
    reg(tk.Button(corr_row, text="+", relief="flat", width=3,
        font=("Courier New", 12), cursor="hand2",
        command=lambda: on_corr_change(1)),
        "btn", {"bg":"ENTRY_BG","fg":"TEXT"}).pack(side="left")

    # Octava
    oct_col = reg(tk.Frame(controles), "frame", {"bg":"PANEL"})
    oct_col.pack(side="left", padx=12)
    reg(tk.Label(oct_col, text="OCTAVA", font=("Courier New", 8)),
        "label", {"bg":"PANEL","fg":"SUBTEXT"}).pack()
    oct_row = reg(tk.Frame(oct_col), "frame", {"bg":"PANEL"})
    oct_row.pack()
    reg(tk.Button(oct_row, text="−", relief="flat", width=3,
        font=("Courier New", 12), cursor="hand2",
        command=lambda: on_oct_change(-1)),
        "btn", {"bg":"ENTRY_BG","fg":"TEXT"}).pack(side="left")
    reg(tk.Label(oct_row, textvariable=oct_var,
        font=("Courier New", 13, "bold"), width=4),
        "entry_lbl", {"fg":"ACCENT2"}).pack(side="left", padx=1)
    reg(tk.Button(oct_row, text="+", relief="flat", width=3,
        font=("Courier New", 12), cursor="hand2",
        command=lambda: on_oct_change(1)),
        "btn", {"bg":"ENTRY_BG","fg":"TEXT"}).pack(side="left")

    # Fijar Do checkbox
    fijar_row = reg(tk.Frame(body), "frame", {"bg":"PANEL"})
    fijar_row.pack(pady=(8, 0))

    def toggle_fijar():
        corr_base[0] = corr_var.get()
        if fijar_do_var.get():
            nueva_corr = corr_base[0] - (oct_var.get() * 12)
            corr_var.set(max(-48, min(48, nueva_corr)))
            if ctrl.activo:
                ctrl.correccion = corr_var.get()

    fijar_chk = tk.Checkbutton(fijar_row, text="FIJAR DO",
        variable=fijar_do_var, command=toggle_fijar,
        font=("Courier New", 8, "bold"),
        relief="flat", bd=0, cursor="hand2")
    reg(fijar_chk, "label", {"bg":"PANEL","fg":"ACCENT2"})
    fijar_chk.config(selectcolor=TEMAS[tema_actual.get()]["ENTRY_BG"],
                     activebackground=TEMAS[tema_actual.get()]["PANEL"])
    fijar_chk.pack(side="left")

    tip(fijar_chk, "Ajusta la corrección automáticamente al cambiar de octava para mantener el Do en su lugar")

    def aplicar_controles():
        corr_base[0] = corr_var.get()
        if ctrl.activo:
            ctrl.correccion = corr_var.get()
            ctrl.octava     = oct_var.get()

    _btn_aplic = tk.Button(body, text="APLICAR CORRECCIÓN Y OCTAVA", relief="flat",
        font=("Courier New", 8, "bold"), padx=10, pady=3,
        command=aplicar_controles, cursor="hand2")
    reg(_btn_aplic, "btn", {"bg":"ENTRY_BG","fg":"ACCENT2"})
    tip(_btn_aplic, "Aplica los cambios de corrección y octava sin reiniciar el espejo")
    _btn_aplic.pack(pady=(4, 0))

    # Botones
    btns = reg(tk.Frame(panel), "frame", {"bg":"PANEL"})
    btns.pack(fill="x", padx=16, pady=(10, 12))

    def refrescar():
        e, s = obtener_puertos()
        ve, vs = cb_entrada.get(), cb_salida.get()
        cb_entrada["values"] = e
        cb_salida["values"]  = s
        cb_entrada.set(ve if ve in e else (e[0] if e else ""))
        cb_salida.set(vs if vs in s else (s[0] if s else ""))

    def activar():
        e, s = cb_entrada.get(), cb_salida.get()
        if not e or not s:
            return
        ctrl.iniciar(e, s, corr_var.get(), oct_var.get())
        _actualizar_btns(ctrl, refs)
        guardar_config()

    def desactivar():
        ctrl.detener()
        _actualizar_btns(ctrl, refs)
        guardar_config()

    btn_on  = tk.Button(btns, text="ACTIVAR", relief="flat",
                        font=("Courier New", 9, "bold"), padx=10, pady=5,
                        command=activar, cursor="hand2")
    btn_off = tk.Button(btns, text="DETENER", relief="flat",
                        font=("Courier New", 9, "bold"), padx=10, pady=5,
                        command=desactivar, cursor="hand2")
    reg(btn_on,  "btn_accent")
    reg(btn_off, "btn_danger")
    tip(btn_on,  "Activa el espejo MIDI para este controlador")
    tip(btn_off, "Detiene el espejo MIDI para este controlador")
    btn_on.pack(side="left", padx=(0,6))
    btn_off.pack(side="left", padx=(0,6))

    _btn_puertos = tk.Button(btns, text="⟳ PUERTOS", relief="flat",
        font=("Courier New", 8), padx=8, pady=5,
        command=refrescar, cursor="hand2")
    reg(_btn_puertos, "btn", {"bg":"ENTRY_BG","fg":"SUBTEXT"})
    tip(_btn_puertos, "Recarga la lista de dispositivos MIDI disponibles")
    _btn_puertos.pack(side="left")

    refs = (btn_on, btn_off, estado_lbl, estado_var, cb_entrada, cb_salida)
    paneles.append((panel, ctrl, refs, cb_entrada, cb_salida, corr_var, oct_var))
    _actualizar_btns(ctrl, refs)
    aplicar_tema()
    actualizar_numeros()
    root.after(120, actualizar_scroll)

def quitar_panel():
    if len(paneles) <= 1:
        return
    panel, ctrl, _, _, _, _, _ = paneles.pop()
    ctrl.detener()
    panel.destroy()
    actualizar_numeros()
    guardar_config()
    root.after(120, actualizar_scroll)

def actualizar_numeros():
    for i, (panel, _, _, _, _, _, _) in enumerate(paneles):
        for child in panel.winfo_children():
            for w in child.winfo_children():
                try:
                    if "CONTROLADOR" in str(w.cget("text")):
                        w.config(text=f"CONTROLADOR {i+1}")
                except:
                    pass

# ─── Layout ───────────────────────────────────────────────────────────────────
main_canvas  = reg(tk.Canvas(root, highlightthickness=0), "canvas", {"bg":"BG"})
scrollbar    = ttk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
scroll_frame = reg(tk.Frame(main_canvas), "frame", {"bg":"BG"})

scroll_frame.bind("<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
canvas_win = main_canvas.create_window((0,0), window=scroll_frame, anchor="nw")
main_canvas.bind("<Configure>",
    lambda e: main_canvas.itemconfig(canvas_win, width=e.width))
main_canvas.pack(side="left", fill="both", expand=True)
root.bind_all("<MouseWheel>",
    lambda e: main_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

# ─── Título ───────────────────────────────────────────────────────────────────
top = reg(tk.Frame(scroll_frame), "frame", {"bg":"BG"})
top.pack(fill="x", padx=16, pady=(18, 8))

reg(tk.Label(top, text="⬡ ESPEJO MIDI", font=("Courier New", 16, "bold")),
    "label", {"bg":"BG","fg":"ACCENT2"}).pack(side="left")
reg(tk.Label(top, text="v1.1", font=("Courier New", 8)),
    "label", {"bg":"BG","fg":"SUBTEXT"}).pack(side="left", padx=6)

_btn_cons = tk.Button(top, text="⌨  CONSOLA", relief="flat",
    font=("Courier New", 8), padx=8, pady=4,
    command=toggle_consola, cursor="hand2")
reg(_btn_cons, "btn", {"bg":"ENTRY_BG","fg":"SUBTEXT"})
tip(_btn_cons, "Abre la consola para ver mensajes de error")
_btn_cons.pack(side="right", padx=(6,0))
_btn_tema = tk.Button(top, text="☀  LIGHT", relief="flat",
    font=("Courier New", 8, "bold"), padx=8, pady=4,
    command=toggle_tema, cursor="hand2")
reg(_btn_tema, "btn_tema")
tip(_btn_tema, "Cambia entre tema oscuro y claro")
_btn_tema.pack(side="right")

# ─── Paneles y footer ─────────────────────────────────────────────────────────
paneles_frame = reg(tk.Frame(scroll_frame), "frame", {"bg":"BG"})
paneles_frame.pack(fill="both", expand=True)

footer = reg(tk.Frame(scroll_frame), "frame", {"bg":"BG"})
footer.pack(fill="x", padx=16, pady=(4, 18))

_btn_add = tk.Button(footer, text="＋  AGREGAR CONTROLADOR", relief="flat",
    font=("Courier New", 9, "bold"), padx=12, pady=6,
    command=lambda: crear_panel(paneles_frame), cursor="hand2")
reg(_btn_add, "btn_accent")
tip(_btn_add, "Añade un segundo controlador MIDI en paralelo")
_btn_add.pack(side="left", padx=(0,8))

_btn_rem = tk.Button(footer, text="－  QUITAR", relief="flat",
    font=("Courier New", 9, "bold"), padx=12, pady=6,
    command=quitar_panel, cursor="hand2")
reg(_btn_rem, "btn", {"bg":"ENTRY_BG","fg":"SUBTEXT"})
tip(_btn_rem, "Elimina el último controlador añadido")
_btn_rem.pack(side="left")



# ─── Init ─────────────────────────────────────────────────────────────────────
style = ttk.Style()
style.theme_use("clam")

cfg_paneles = cfg.get("paneles", [])
if cfg_paneles:
    for p in cfg_paneles:
        crear_panel(paneles_frame, config=p)
else:
    crear_panel(paneles_frame)

aplicar_tema()

def al_cerrar():
    guardar_config()
    for _, ctrl, _, _, _, _, _ in paneles:
        ctrl.detener()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", al_cerrar)
root.mainloop()
