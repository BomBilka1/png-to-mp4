import sys, os, time, re, threading, subprocess, tempfile
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext

# ── console encoding fix ──────────────────────────────────
# On localized Windows the console defaults to cp1251, which can't encode the
# box-drawing chars in the startup banner. Force UTF-8 where a stream exists.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── PyInstaller path fix ──────────────────────────────────
if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
    # _base itself must be in sys.path so "import moviepy" works
    if _base not in sys.path:
        sys.path.insert(0, _base)
    # Also check one level up (some PyInstaller versions unpack differently)
    _parent = os.path.dirname(_base)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)

# ── deps ──────────────────────────────────────────────────
try:
    from moviepy import ImageClip, VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

FFMPEG_AVAILABLE = False
FFMPEG_PATH = None

# Inside PyInstaller EXE — look in bundled binaries first
if getattr(sys, 'frozen', False):
    _binaries_dir = os.path.join(sys._MEIPASS, 'imageio_ffmpeg', 'binaries')
    if os.path.isdir(_binaries_dir):
        for _f in os.listdir(_binaries_dir):
            if 'ffmpeg' in _f.lower() and _f.endswith('.exe'):
                FFMPEG_PATH = os.path.join(_binaries_dir, _f)
                FFMPEG_AVAILABLE = True
                break

if not FFMPEG_AVAILABLE and MOVIEPY_AVAILABLE:
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
        FFMPEG_AVAILABLE = True
    except: pass

if not FFMPEG_AVAILABLE:
    for _c in ["ffmpeg", "ffmpeg.exe"]:
        try:
            if subprocess.run([_c,"-version"], capture_output=True).returncode == 0:
                FFMPEG_PATH = _c; FFMPEG_AVAILABLE = True; break
        except: pass

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

VERSION  = "8.4.0"
DURATION = 10
FPS      = 24
IMAGE_FORMATS = ["png","jpg","webp","bmp","tiff","ico"]
VIDEO_FORMATS = ["mp4","avi","mov","mkv","webm","gif"]
MERGE_FORMATS = ["mp4","avi","mov","mkv","webm"]

# ── auto-update settings ──────────────────────────────────
# УКАЖИТЕ здесь свой репозиторий на GitHub. После этого достаточно
# публиковать новый Release с приложенным файлом VideoMakerPro_Setup.exe —
# программа сама заметит обновление и предложит установить.
GITHUB_OWNER = "BomBilka1"                      # <-- ваш логин на GitHub
GITHUB_REPO  = "png-to-mp4"                    # <-- имя репозитория
UPDATE_ASSET = "VideoMakerPro_Setup.exe"       # имя файла установщика в релизе
UPDATE_API   = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# ── уровни сжатия PDF ─────────────────────────────────────
# dpi = None означает «не трогать картинки», только чистка структуры.
PDF_COMPRESS_LEVELS = [
    ("без потерь — только чистка", None, None),
    ("высокое — 200 dpi",          200,  80),
    ("среднее — 150 dpi",          150,  75),
    ("сильное — 120 dpi",          120,  70),
    ("максимальное — 96 dpi",       96,  65),
]

# ── palette ───────────────────────────────────────────────
D = {
    "bg0":"#0d0d0f","bg1":"#111114","bg2":"#16161a",
    "bg3":"#1c1c22","bg4":"#222228",
    "b0":"#1a1a1f","b1":"#24242c",
    "t0":"#e8e8f0","t1":"#888898","t2":"#44444e",
    "amber":"#c97d20","teal":"#1db87a","blue":"#3a7fd5",
    "violet":"#7c5cbf","rose":"#c43060","green":"#2ea855",
    "teal_bg":"#0a1f14","rose_bg":"#200810","blue_bg":"#0a1220",
}

def _fmt_time(s):
    s=max(0,int(s)); h,r=divmod(s,3600); m,sec=divmod(r,60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

# ── global styles ─────────────────────────────────────────
def _apply_styles():
    s=ttk.Style(); s.theme_use("clam")
    s.configure("Dark.Vertical.TScrollbar",background=D["bg4"],troughcolor=D["bg1"],
                arrowcolor=D["t2"],borderwidth=0,width=8)
    s.configure("D.TCombobox",fieldbackground=D["bg4"],background=D["bg4"],
                foreground=D["t0"],arrowcolor=D["t1"],borderwidth=0,
                selectbackground=D["bg4"],selectforeground=D["t0"])
    s.map("D.TCombobox",fieldbackground=[("readonly",D["bg4"])],
          foreground=[("readonly",D["t0"])])
    s.configure("Treeview",background=D["bg2"],fieldbackground=D["bg2"],
                foreground=D["t0"],font=("Segoe UI",9),rowheight=26)
    s.configure("Treeview.Heading",background=D["bg4"],foreground=D["t1"],
                font=("Segoe UI",8,"bold"),borderwidth=0)
    s.map("Treeview",background=[("selected",D["bg4"])],foreground=[("selected",D["teal"])])
    s.configure("Dark.Horizontal.TProgressbar",
                troughcolor=D["bg4"], background=D["amber"],
                borderwidth=0, thickness=5)
    s.configure("DarkTeal.Horizontal.TProgressbar",
                troughcolor=D["bg4"], background=D["teal"],
                borderwidth=0, thickness=5)
    s.configure("DarkRose.Horizontal.TProgressbar",
                troughcolor=D["bg4"], background=D["rose"],
                borderwidth=0, thickness=5)
    s.configure("DarkBlue.Horizontal.TProgressbar",
                troughcolor=D["bg4"], background=D["blue"],
                borderwidth=0, thickness=5)
    s.configure("DarkViolet.Horizontal.TProgressbar",
                troughcolor=D["bg4"], background=D["violet"],
                borderwidth=0, thickness=5)
    s.configure("DarkGreen.Horizontal.TProgressbar",
                troughcolor=D["bg4"], background=D["green"],
                borderwidth=0, thickness=5)

# ── widget helpers ────────────────────────────────────────
def _combo(parent, var, values, width=12):
    return ttk.Combobox(parent,textvariable=var,values=values,width=width,
                        state="readonly",font=("Segoe UI",9),style="D.TCombobox")

def _spinbox(parent, var, lo, hi, w=5):
    return tk.Spinbox(parent,from_=lo,to=hi,textvariable=var,width=w,
                      bg=D["bg4"],fg=D["t0"],relief="flat",
                      buttonbackground=D["bg3"],insertbackground=D["amber"],
                      font=("Segoe UI",9))

def _radio_group(parent, var, options, active_col=None):
    f=tk.Frame(parent,bg=parent.cget("bg"))
    for label,val in options:
        tk.Radiobutton(f,text=label,variable=var,value=val,
                       bg=parent.cget("bg"),fg=D["t1"],
                       selectcolor=D["bg3"],
                       activebackground=parent.cget("bg"),
                       activeforeground=active_col or D["t0"],
                       font=("Segoe UI",9)).pack(side="left",padx=(0,14))
    return f

def _pill(parent, text, accent, cmd, enabled=True):
    bg=accent if enabled else D["bg4"]
    fg=D["bg0"] if enabled else D["t2"]
    return tk.Button(parent,text=text,font=("Segoe UI",10,"bold"),
                     bg=bg,fg=fg,activebackground=accent,activeforeground=D["bg0"],
                     relief="flat",cursor="hand2" if enabled else "arrow",
                     state="normal" if enabled else "disabled",
                     command=cmd,padx=16,pady=9)

def _ghost(parent, text, accent, cmd, enabled=True):
    fg=accent if enabled else D["t2"]
    return tk.Button(parent,text=text,font=("Segoe UI",9),
                     bg=D["bg3"],fg=fg,activebackground=D["bg4"],activeforeground=fg,
                     relief="flat",cursor="hand2" if enabled else "arrow",
                     state="normal" if enabled else "disabled",
                     command=cmd,padx=14,pady=7)

# ── layout primitives ─────────────────────────────────────
def _page_header(page, title, subtitle, accent):
    hf=tk.Frame(page,bg=D["bg0"]); hf.pack(fill="x")
    tk.Frame(hf,bg=accent,height=2).pack(fill="x")
    body=tk.Frame(hf,bg=D["bg0"],padx=22,pady=14); body.pack(fill="x")
    tk.Label(body,text=title,font=("Segoe UI",15,"bold"),bg=D["bg0"],fg=D["t0"]).pack(side="left")
    tk.Label(body,text=subtitle,font=("Segoe UI",9),bg=D["bg0"],fg=D["t2"]).pack(side="left",padx=(12,0),pady=(3,0))
    tk.Frame(page,bg=D["b0"],height=1).pack(fill="x")

def _section(parent, title, accent):
    outer=tk.Frame(parent,bg=D["bg2"]); outer.pack(fill="x",padx=20,pady=(0,10))
    tk.Frame(outer,bg=accent,width=2).pack(side="left",fill="y")
    inner=tk.Frame(outer,bg=D["bg2"],padx=14,pady=12); inner.pack(side="left",fill="both",expand=True)
    if title:
        tk.Label(inner,text=title.upper(),font=("Segoe UI",8,"bold"),
                 bg=D["bg2"],fg=D["t2"]).pack(anchor="w",pady=(0,8))
    return inner

def _field(parent, label, build_fn):
    r=tk.Frame(parent,bg=parent.cget("bg")); r.pack(fill="x",pady=5)
    tk.Label(r,text=label,font=("Segoe UI",9),bg=r.cget("bg"),fg=D["t1"],
             width=22,anchor="w").pack(side="left")
    build_fn(r); return r

def _hint(parent, text):
    tk.Label(parent,text=text,font=("Segoe UI",8,"italic"),
             bg=parent.cget("bg"),fg=D["t2"]).pack(side="left",padx=6)

def _divider(parent):
    tk.Frame(parent,bg=D["b1"],height=1).pack(fill="x",padx=20,pady=8)

def _slider_block(parent, var, lo, hi, accent, on_change):
    top=tk.Frame(parent,bg=parent.cget("bg")); top.pack(fill="x",pady=(0,4))
    val_lbl=tk.Label(top,text=str(int(var.get())),font=("Courier New",16,"bold"),
                     bg=parent.cget("bg"),fg=accent,width=4); val_lbl.pack(side="left")
    hint_lbl=tk.Label(top,text="",font=("Segoe UI",9,"italic"),
                      bg=parent.cget("bg"),fg=D["t1"]); hint_lbl.pack(side="left",padx=8)
    row=tk.Frame(parent,bg=parent.cget("bg")); row.pack(fill="x",pady=(2,6))
    tk.Label(row,text=str(lo),font=("Segoe UI",8),bg=parent.cget("bg"),fg=D["t2"]).pack(side="left")
    scale=tk.Scale(row,from_=lo,to=hi,variable=var,orient="horizontal",showvalue=False,
                   bg=parent.cget("bg"),troughcolor=D["bg4"],activebackground=accent,
                   highlightthickness=0,bd=0,sliderlength=16)
    scale.pack(side="left",fill="x",expand=True,padx=6)
    tk.Label(row,text=str(hi),font=("Segoe UI",8),bg=parent.cget("bg"),fg=D["t2"]).pack(side="left")
    def _cb(v):
        val_lbl.configure(text=str(int(float(v))))
        if on_change: on_change(v, hint_lbl)
    scale.configure(command=_cb); _cb(var.get())
    return val_lbl, hint_lbl

# ══════════════════════════════════════════════════════════
#  LOGGER
# ══════════════════════════════════════════════════════════
class Logger:
    def __init__(self):
        self.logs=[]; self.log_window=None; self.log_text=None; self.log_file=None
        self._setup_file()

    def _setup_file(self):
        try:
            d=os.path.join(os.path.expanduser("~"),"VideoMakerPro_Logs")
            os.makedirs(d,exist_ok=True)
            self.log_file=os.path.join(d,f"log_{datetime.now():%Y%m%d_%H%M%S}.txt")
            open(self.log_file,'w',encoding='utf-8').write(f"=== Video Maker Pro v{VERSION} ===\n{datetime.now()}\n{'─'*50}\n\n")
        except: pass

    def add(self, msg, level="INFO"):
        ts=datetime.now().strftime("%H:%M:%S")
        em={"INFO":"·","SUCCESS":"✓","WARNING":"!","ERROR":"✕","PROCESS":"◎"}.get(level,"·")
        entry=f"[{ts}] {em} {msg}"
        self.logs.append({"level":level,"full":entry}); print(entry)
        if self.log_file:
            try: open(self.log_file,'a',encoding='utf-8').write(entry+"\n")
            except: pass
        self._refresh()

    def _refresh(self):
        if self.log_window and self.log_text:
            try:
                self.log_text.configure(state='normal')
                self.log_text.delete(1.0,tk.END)
                for l in self.logs[-300:]:
                    self.log_text.insert(tk.END,l['full']+"\n",l['level'].lower())
                self.log_text.see(tk.END); self.log_text.configure(state='disabled')
            except: pass

    def show(self, parent):
        if self.log_window:
            try: self.log_window.lift(); return
            except: self.log_window=None
        w=tk.Toplevel(parent); self.log_window=w
        w.title("Журнал"); w.geometry("780x500"); w.configure(bg=D["bg0"])
        hf=tk.Frame(w,bg=D["bg2"],height=46); hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf,bg=D["amber"],width=2).pack(side="left",fill="y")
        tk.Label(hf,text="  ЖУРНАЛ СОБЫТИЙ",font=("Courier New",11,"bold"),bg=D["bg2"],fg=D["amber"]).pack(side="left",pady=10)
        tb=tk.Frame(w,bg=D["bg1"],height=36); tb.pack(fill="x"); tb.pack_propagate(False)
        def _tbtn(t,col,cmd):
            tk.Button(tb,text=t,font=("Segoe UI",8),bg=D["bg3"],fg=col,relief="flat",
                      cursor="hand2",padx=10,command=cmd).pack(side="left",padx=3,pady=5)
        _tbtn("Очистить",D["rose"],self._clear); _tbtn("Сохранить",D["teal"],self._save)
        _tbtn("Папка",D["blue"],self._open_folder)
        fv=tk.StringVar(value="Все")
        tk.Label(tb,text="  Фильтр:",font=("Segoe UI",8),bg=D["bg1"],fg=D["t1"]).pack(side="left")
        cb=ttk.Combobox(tb,textvariable=fv,values=["Все","INFO","SUCCESS","WARNING","ERROR"],
                        width=9,state="readonly",font=("Segoe UI",8),style="D.TCombobox")
        cb.pack(side="left",padx=4,pady=5)
        cb.bind("<<ComboboxSelected>>",lambda e:self._filter(fv.get()))
        tf=tk.Frame(w,bg=D["bg0"]); tf.pack(fill="both",expand=True,padx=10,pady=6)
        self.log_text=scrolledtext.ScrolledText(tf,wrap=tk.WORD,font=("Courier New",9),
            bg=D["bg0"],fg=D["t0"],insertbackground=D["amber"],
            selectbackground=D["bg3"],state='disabled',relief="flat",bd=0)
        self.log_text.pack(fill="both",expand=True)
        for lv,col in [("success",D["teal"]),("warning",D["amber"]),("error",D["rose"]),("info",D["blue"])]:
            self.log_text.tag_configure(lv,foreground=col)
        self._refresh()

    def _filter(self,f):
        if not self.log_text: return
        self.log_text.configure(state='normal'); self.log_text.delete(1.0,tk.END)
        for l in self.logs:
            if f=="Все" or l['level']==f:
                self.log_text.insert(tk.END,l['full']+"\n",l['level'].lower())
        self.log_text.see(tk.END); self.log_text.configure(state='disabled')

    def _clear(self):
        if messagebox.askyesno("Подтверждение","Удалить все записи?"):
            self.logs=[]; self._refresh()

    def _save(self):
        fn=filedialog.asksaveasfilename(defaultextension=".txt",initialfile=f"log_{datetime.now():%Y%m%d}.txt")
        if fn:
            with open(fn,'w',encoding='utf-8') as f: [f.write(l['full']+"\n") for l in self.logs]

    def _open_folder(self):
        d=os.path.join(os.path.expanduser("~"),"VideoMakerPro_Logs")
        if os.path.exists(d): os.startfile(d)

# ══════════════════════════════════════════════════════════
#  PROGRESS POPUP
# ══════════════════════════════════════════════════════════
class ProgressPopup(tk.Toplevel):
    _STYLES={
        D["teal"]:   "DarkTeal.Horizontal.TProgressbar",
        D["blue"]:   "DarkBlue.Horizontal.TProgressbar",
        D["violet"]: "DarkViolet.Horizontal.TProgressbar",
        D["rose"]:   "DarkRose.Horizontal.TProgressbar",
        D["amber"]:  "Dark.Horizontal.TProgressbar",
        D["green"]:  "DarkGreen.Horizontal.TProgressbar",
    }

    def __init__(self, master, total, accent=D["amber"]):
        super().__init__(master)
        self.title("Обработка"); self.geometry("460x200")
        self.configure(bg=D["bg0"]); self.resizable(False,False)
        self._cancel_cb=None
        pstyle=self._STYLES.get(accent,"Dark.Horizontal.TProgressbar")
        tk.Frame(self,bg=accent,height=2).pack(fill="x")
        body=tk.Frame(self,bg=D["bg0"],padx=24,pady=16); body.pack(fill="both",expand=True)
        self.file_lbl=tk.Label(body,text="Подготовка…",font=("Segoe UI",10,"bold"),bg=D["bg0"],fg=D["t0"])
        self.file_lbl.pack(anchor="w",pady=(0,8))
        self.bar=ttk.Progressbar(body,length=410,maximum=max(total,1),style=pstyle)
        self.bar.pack()
        self.pct_lbl=tk.Label(body,text="0%",font=("Courier New",8),bg=D["bg0"],fg=D["t2"])
        self.pct_lbl.pack(anchor="e",pady=(2,8))
        self.ffmpeg_lbl=tk.Label(body,text="",font=("Segoe UI",8),bg=D["bg0"],fg=D["t1"])
        self.ffmpeg_lbl.pack(anchor="w",pady=(0,4))
        self.inner_bar=ttk.Progressbar(body,length=410,maximum=100,
                                       style="DarkTeal.Horizontal.TProgressbar")
        self.inner_bar.pack()
        self.speed_lbl=tk.Label(body,text="",font=("Courier New",8),bg=D["bg0"],fg=D["t2"])
        self.speed_lbl.pack(anchor="e",pady=(2,0))
        tk.Button(body,text="Отмена",font=("Segoe UI",8),bg=D["bg3"],fg=D["rose"],
                  relief="flat",cursor="hand2",command=self._cancel).pack(pady=(10,0))

    def update_state(self, cur, total, text):
        self.bar['value']=cur; pct=int(cur/total*100) if total else 0
        self.file_lbl.configure(text=f"[{cur}/{total}]  {text}")
        self.pct_lbl.configure(text=f"{pct}%"); self.update()

    def update_ffmpeg(self, pct, done, total, speed, eta):
        try:
            self.inner_bar['value']=max(0,min(100,pct))
            self.ffmpeg_lbl.configure(text=f"Обработано: {_fmt_time(done)} / {_fmt_time(total)}  ({pct:.0f}%)")
            s=f"  {speed}x" if speed else ""; e=f"  ETA {_fmt_time(eta)}" if eta>0 else ""
            self.speed_lbl.configure(text=s+e); self.update()
        except: pass

    def reset_ffmpeg(self):
        try:
            self.inner_bar['value']=0; self.ffmpeg_lbl.configure(text=""); self.speed_lbl.configure(text="")
        except: pass

    def set_cancel(self,cb): self._cancel_cb=cb
    def _cancel(self):
        if self._cancel_cb: self._cancel_cb()

# ══════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════
class Sidebar(tk.Frame):
    ITEMS=[("ФОТО","photo",D["teal"],"\U0001f5bc"),
           ("ВИДЕО","video",D["blue"],"\U0001f3ac"),
           ("СОЗДАТЬ","create",D["violet"],"\u2728"),
           ("СКЛЕИТЬ","merge",D["amber"],"\U0001f517"),
           ("СЖАТИЕ","compress",D["rose"],"\U0001f4e6"),
           ("PDF","pdf","#e8622a","\U0001f4c4"),
           ("АУДИО","audio","#d4a017","\U0001f3b5"),
           ("ИНСТР.","tools",D["green"],"\U0001f527")]

    def __init__(self, master, on_select, **kw):
        super().__init__(master,bg=D["bg0"],width=72,**kw)
        self.pack_propagate(False); self.on_select=on_select
        self._btns={}; self._active=None
        logo=tk.Frame(self,bg=D["bg0"],height=56); logo.pack(fill="x"); logo.pack_propagate(False)
        mark=tk.Frame(logo,bg=D["amber"],width=30,height=30)
        mark.place(relx=0.5,rely=0.5,anchor="center")
        tk.Label(mark,text="▶",font=("Courier New",12,"bold"),bg=D["amber"],fg=D["bg0"]).place(relx=0.5,rely=0.5,anchor="center")
        tk.Frame(self,bg=D["b0"],height=1).pack(fill="x")
        for label,key,col,icon in self.ITEMS:
            frame=tk.Frame(self,bg=D["bg0"],height=66,cursor="hand2")
            frame.pack(fill="x"); frame.pack_propagate(False)
            bar=tk.Frame(frame,bg=D["bg0"],width=2); bar.pack(side="left",fill="y")
            body=tk.Frame(frame,bg=D["bg0"])
            body.place(relx=0.5,rely=0.5,anchor="center")
            ico=tk.Label(body,text=icon,font=("Segoe UI Emoji",15),bg=D["bg0"],fg=D["t2"]); ico.pack()
            lbl=tk.Label(body,text=label,font=("Segoe UI",7,"bold"),bg=D["bg0"],fg=D["t2"]); lbl.pack()
            tk.Frame(self,bg=D["b0"],height=1).pack(fill="x")
            self._btns[key]=dict(frame=frame,bar=bar,body=body,ico=ico,lbl=lbl,col=col)
            for w in [frame,body,ico,lbl]:
                w.bind("<Button-1>",lambda e,k=key:self._click(k))
                w.bind("<Enter>",   lambda e,k=key:self._hover(k,True))
                w.bind("<Leave>",   lambda e,k=key:self._hover(k,False))
        self.select("photo")

    def _click(self,key): self.select(key); self.on_select(key)

    def _hover(self,key,on):
        if key==self._active: return
        d=self._btns[key]; bg=D["bg2"] if on else D["bg0"]
        for w in [d["frame"],d["body"],d["ico"],d["lbl"]]: w.configure(bg=bg)

    def select(self,key):
        if self._active:
            d=self._btns[self._active]
            for w in [d["frame"],d["body"],d["ico"],d["lbl"]]: w.configure(bg=D["bg0"])
            d["ico"].configure(fg=D["t2"]); d["lbl"].configure(fg=D["t2"]); d["bar"].configure(bg=D["bg0"])
        self._active=key; d=self._btns[key]
        for w in [d["frame"],d["body"],d["ico"],d["lbl"]]: w.configure(bg=D["bg2"])
        d["ico"].configure(fg=d["col"]); d["lbl"].configure(fg=d["col"]); d["bar"].configure(bg=d["col"])

# ══════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════
#  AUTO-UPDATE (GitHub Releases, только stdlib — без новых зависимостей)
# ══════════════════════════════════════════════════════════
def _parse_ver(s):
    """'v8.1.0' -> (8,1,0). Нечисловые хвосты частей отбрасываются."""
    s = (s or "").lstrip("vV").strip()
    parts = []
    for chunk in s.split("."):
        num = ""
        for ch in chunk:
            if ch.isdigit(): num += ch
            else: break
        parts.append(int(num) if num else 0)
    return tuple(parts) if parts else (0,)

def _is_newer(remote, local):
    r, l = _parse_ver(remote), _parse_ver(local)
    n = max(len(r), len(l))
    r += (0,)*(n-len(r)); l += (0,)*(n-len(l))
    return r > l

# ── TLS в корпоративных сетях ─────────────────────────────
# Многие организации расшифровывают HTTPS на прокси и подписывают соединения
# собственным корневым сертификатом. В хранилище Windows он есть, но Python
# внутри собранного .exe о нём не знает и рвёт соединение с
# CERTIFICATE_VERIFY_FAILED. truststore перекладывает проверку сертификатов
# на саму Windows, поэтому корпоративный корень принимается.
def _ssl_context():
    import ssl
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        return ssl.create_default_context()


def fetch_latest_release(timeout=8):
    """Спрашивает у GitHub последний релиз. Возвращает {version,url,notes} или None."""
    import json, urllib.request
    req = urllib.request.Request(UPDATE_API, headers={
        "User-Agent": "VideoMakerPro-Updater",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    url = None
    for asset in data.get("assets", []):
        if asset.get("name","").lower() == UPDATE_ASSET.lower():
            url = asset.get("browser_download_url"); break
    if url is None:  # запасной вариант — первый .exe среди файлов релиза
        for asset in data.get("assets", []):
            if asset.get("name","").lower().endswith(".exe"):
                url = asset.get("browser_download_url"); break
    return {"version": data.get("tag_name") or data.get("name") or "",
            "url": url, "notes": (data.get("body") or "").strip()}


class VideoMakerPro:

    def __init__(self):
        self.root=tk.Tk()
        self.root.title(f"Video Maker Pro  v{VERSION}")
        self.root.geometry("1000x700"); self.root.minsize(840,560)
        self.root.configure(bg=D["bg0"]); _apply_styles(); self._center()
        self.logger=Logger()
        self.logger.add("Программа запущена","INFO")
        self.logger.add(f"PIL: {'OK' if PIL_AVAILABLE else 'не найден'}","INFO" if PIL_AVAILABLE else "WARNING")
        self.logger.add(f"MoviePy: {'OK' if MOVIEPY_AVAILABLE else 'не найден'}","INFO" if MOVIEPY_AVAILABLE else "WARNING")
        self.logger.add(f"FFMPEG: {'OK' if FFMPEG_AVAILABLE else 'не найден'}","INFO" if FFMPEG_AVAILABLE else "WARNING")
        self.cancel_flag=False; self.progress_popup=None
        self.temp_dir=tempfile.mkdtemp(prefix="vmp_"); self._video_ext="mp4"
        # vars
        self.v_photo_fmt=tk.StringVar(value="png"); self.v_photo_q=tk.StringVar(value="95")
        self.v_ico_sz=tk.StringVar(value="256"); self.v_vid_fmt=tk.StringVar(value="mp4")
        self.v_vid_q=tk.StringVar(value="medium"); self.v_merge_fmt=tk.StringVar(value="mp4")
        self.v_merge_q=tk.StringVar(value="medium"); self.v_crf=tk.DoubleVar(value=28)
        self.v_preset=tk.StringVar(value="medium"); self.v_res=tk.StringVar(value="original")
        self.v_cmp_q=tk.IntVar(value=75); self.v_cmp_fmt=tk.StringVar(value="jpg")
        self.v_cmp_maxpx=tk.StringVar(value="без ограничений")
        # watermark vars
        self.v_wm_enabled   = tk.BooleanVar(value=False)
        self.v_wm_date      = tk.BooleanVar(value=True)
        self.v_wm_date_text = tk.StringVar(value="")
        self.v_wm_text      = tk.StringVar(value="")
        self.v_wm_corner    = tk.StringVar(value="правый нижний")
        self.v_wm_size      = tk.IntVar(value=28)
        self.v_wm_color     = tk.StringVar(value="белый")
        self.v_wm_opacity   = tk.IntVar(value=85)
        self.v_wm_margin    = tk.IntVar(value=16)
        # metadata removal vars
        self.v_meta_gps    = tk.BooleanVar(value=True)
        self.v_meta_camera = tk.BooleanVar(value=True)
        self.v_meta_date   = tk.BooleanVar(value=False)
        self.v_meta_author = tk.BooleanVar(value=True)
        self.v_meta_all    = tk.BooleanVar(value=False)
        # PDF vars
        self.v_pdf_pages_del   = tk.StringVar(value="")
        self.v_pdf_pages_ext   = tk.StringVar(value="")
        self.v_pdf_rotate_deg  = tk.StringVar(value="90")
        self.v_pdf_rotate_pgs  = tk.StringVar(value="все")
        self.v_pdf_cmp_level   = tk.StringVar(value=PDF_COMPRESS_LEVELS[2][0])
        self.v_pdf_cmp_target  = tk.StringVar(value="")
        self.v_pdf_num_pos     = tk.StringVar(value="по центру снизу")
        self.v_pdf_num_start   = tk.StringVar(value="1")
        self.v_pdf_num_size    = tk.StringVar(value="12")
        # Audio vars
        self.v_au_fmt      = tk.StringVar(value="mp3")
        self.v_au_bitrate  = tk.StringVar(value="192")
        self.v_au_trim_from= tk.StringVar(value="0:00")
        self.v_au_trim_to  = tk.StringVar(value="")
        self.v_au_merge_fmt= tk.StringVar(value="mp3")
        self.v_au_norm_lvl = tk.StringVar(value="-16")
        self._build_ui(); self._show_page("photo")
        # тихая проверка обновлений в фоне после запуска
        self.root.after(2000, lambda: self._check_updates(silent=True))

    def _center(self):
        self.root.update_idletasks(); w,h=1000,700
        self.root.geometry(f"{w}x{h}+{(self.root.winfo_screenwidth()-w)//2}+{(self.root.winfo_screenheight()-h)//2}")

    # ── shell ────────────────────────────────────────────────
    def _build_ui(self):
        # topbar
        top=tk.Frame(self.root,bg=D["bg2"],height=46); top.pack(fill="x"); top.pack_propagate(False)
        tk.Frame(top,bg=D["amber"],width=2).pack(side="left",fill="y")
        tk.Label(top,text="  VIDEO MAKER PRO",font=("Courier New",13,"bold"),bg=D["bg2"],fg=D["amber"]).pack(side="left",pady=10)
        tk.Label(top,text=f"v{VERSION}",font=("Segoe UI",9),bg=D["bg2"],fg=D["t2"]).pack(side="left",padx=6,pady=12)
        bf=tk.Frame(top,bg=D["bg2"]); bf.pack(side="right",padx=10)
        for name,ok in [("PIL",PIL_AVAILABLE),("MoviePy",MOVIEPY_AVAILABLE),("FFMPEG",FFMPEG_AVAILABLE)]:
            bg=D["teal_bg"] if ok else D["rose_bg"]; fg=D["teal"] if ok else D["rose"]
            tk.Label(bf,text=f" {name} ",font=("Segoe UI",8,"bold"),bg=bg,fg=fg,padx=4,pady=2).pack(side="left",padx=2)
        tk.Button(top,text=" ≡  Логи",font=("Segoe UI",9),bg=D["bg3"],fg=D["t1"],
                  relief="flat",cursor="hand2",
                  command=lambda:self.logger.show(self.root)).pack(side="right",padx=8,pady=10,ipadx=4)
        # Кнопка обновлений с красной точкой
        upd_wrap=tk.Frame(top,bg=D["bg2"]); upd_wrap.pack(side="right",padx=0,pady=8)
        self._upd_btn=tk.Button(upd_wrap,text=" ⭳  Обновления",font=("Segoe UI",9),
                  bg=D["bg3"],fg=D["t1"],relief="flat",cursor="hand2",
                  command=lambda:self._check_updates(silent=False),padx=4,pady=4)
        self._upd_btn.pack(side="left")
        # Красная точка — скрыта по умолчанию
        self._upd_dot=tk.Label(upd_wrap,text="●",font=("Segoe UI",9,"bold"),
                               bg=D["bg2"],fg=D["rose"])
        # dot не pack'ается пока нет обновлений
        tk.Frame(self.root,bg=D["b0"],height=1).pack(fill="x")
        # main
        main=tk.Frame(self.root,bg=D["bg0"]); main.pack(fill="both",expand=True)
        self.sidebar=Sidebar(main,self._show_page); self.sidebar.pack(side="left",fill="y")
        tk.Frame(main,bg=D["b0"],width=1).pack(side="left",fill="y")
        right=tk.Frame(main,bg=D["bg1"]); right.pack(side="left",fill="both",expand=True)
        self._cv=tk.Canvas(right,bg=D["bg1"],highlightthickness=0)
        sb=ttk.Scrollbar(right,orient="vertical",command=self._cv.yview,style="Dark.Vertical.TScrollbar")
        self._cf=tk.Frame(self._cv,bg=D["bg1"])
        self._cf.bind("<Configure>",lambda e:self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.create_window((0,0),window=self._cf,anchor="nw")
        self._cv.configure(yscrollcommand=sb.set)
        self._cv.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        self._cv.bind_all("<MouseWheel>",lambda e:self._cv.yview_scroll(int(-1*(e.delta/120)),"units"))
        # statusbar
        sbar=tk.Frame(self.root,bg=D["bg2"],height=22); sbar.pack(fill="x",side="bottom"); sbar.pack_propagate(False)
        tk.Frame(sbar,bg=D["b0"],height=1).pack(fill="x")
        self._status_var=tk.StringVar(value="Готов к работе")
        tk.Frame(sbar,bg=D["teal"],width=6,height=6).pack(side="left",padx=(12,5),pady=8)
        tk.Label(sbar,textvariable=self._status_var,font=("Segoe UI",8),bg=D["bg2"],fg=D["t1"]).pack(side="left")
        tk.Label(sbar,text=f"v{VERSION}",font=("Courier New",8),bg=D["bg2"],fg=D["t2"]).pack(side="right",padx=12)
        # pages
        self.pages={}
        self._build_photo_page(); self._build_video_page(); self._build_create_page()
        self._build_merge_page(); self._build_compress_page()
        self._build_pdf_page(); self._build_audio_page(); self._build_tools_page()

    def _show_page(self,key):
        for f in self.pages.values(): f.pack_forget()
        self.pages[key].pack(fill="both",expand=True)
        self._cv.yview_moveto(0); self.sidebar.select(key)

    # ── page: photo ──────────────────────────────────────────
    def _build_photo_page(self):
        p=tk.Frame(self._cf,bg=D["bg1"]); self.pages["photo"]=p
        _page_header(p,"Конвертер фото","Конвертация изображений в различные форматы",D["teal"])
        body=tk.Frame(p,bg=D["bg1"],pady=10); body.pack(fill="both",expand=True)

        # ── Конвертация ──
        sec=_section(body,"Параметры конвертации",D["teal"])
        _field(sec,"Выходной формат",lambda r:(_combo(r,self.v_photo_fmt,IMAGE_FORMATS,10).pack(side="left",padx=(0,16)),))
        _field(sec,"Качество JPG (1–100)",lambda r:(_spinbox(r,self.v_photo_q,1,100,5).pack(side="left"),_hint(r,"Только для JPG/JPEG")))
        _field(sec,"Размер ICO (px)",lambda r:(_combo(r,self.v_ico_sz,["16","32","48","64","128","256"],7).pack(side="left"),))
        bf=tk.Frame(body,bg=D["bg1"]); bf.pack(fill="x",padx=20,pady=(2,10))
        _pill(bf,"  Конвертировать фото",D["teal"],self._start_photo,PIL_AVAILABLE).pack(fill="x",ipady=2)
        if not PIL_AVAILABLE:
            tk.Label(bf,text="⚠  PIL не установлен — перейдите в Инструменты",
                     font=("Segoe UI",8,"italic"),bg=D["bg1"],fg=D["t2"]).pack(anchor="w",pady=4)

        _divider(body)

        # ── Водяной знак / подпись ──
        wsec=_section(body,"Подпись на фото (дата / комментарий)",D["amber"])

        # Включить/выключить
        wm_top=tk.Frame(wsec,bg=wsec.cget("bg")); wm_top.pack(fill="x",pady=(0,6))
        self._wm_cb=tk.Checkbutton(wm_top,text="Добавлять подпись",
                                   variable=self.v_wm_enabled,
                                   bg=wsec.cget("bg"),fg=D["t0"],
                                   selectcolor=D["bg3"],
                                   activebackground=wsec.cget("bg"),
                                   activeforeground=D["amber"],
                                   font=("Segoe UI",9,"bold"),
                                   command=self._wm_toggle)
        self._wm_cb.pack(side="left")

        # Контейнер настроек (скрыт по умолчанию)
        self._wm_body=tk.Frame(wsec,bg=wsec.cget("bg"))
        self._wm_body.pack(fill="x")
        wb=self._wm_body

        _field(wb,"Дата",lambda r:(
            tk.Checkbutton(r,text="Добавить дату",variable=self.v_wm_date,
                           bg=r.cget("bg"),fg=D["t1"],selectcolor=D["bg3"],
                           activebackground=r.cget("bg"),
                           font=("Segoe UI",9)).pack(side="left"),
            tk.Entry(r,textvariable=self.v_wm_date_text,width=16,
                     bg=D["bg4"],fg=D["t0"],insertbackground=D["amber"],
                     relief="flat",font=("Segoe UI",9)).pack(side="left",padx=8),
            _hint(r,"Пример: 15.06.2025  или  оставьте пустым для авто"),
        ))
        _field(wb,"Комментарий",lambda r:(
            tk.Entry(r,textvariable=self.v_wm_text,width=30,
                     bg=D["bg4"],fg=D["t0"],insertbackground=D["amber"],
                     relief="flat",font=("Segoe UI",9)).pack(side="left"),
            _hint(r,"Оставьте пустым если не нужен"),
        ))
        _field(wb,"Угол",lambda r:(
            _combo(r,self.v_wm_corner,
                   ["правый нижний","левый нижний","правый верхний","левый верхний"],14).pack(side="left"),
        ))
        _field(wb,"Размер шрифта",lambda r:(
            _spinbox(r,self.v_wm_size,10,120,5).pack(side="left"),
            _hint(r,"пикселей"),
        ))
        _field(wb,"Цвет текста",lambda r:(
            _combo(r,self.v_wm_color,["белый","чёрный","жёлтый","красный","синий"],10).pack(side="left"),
        ))
        _field(wb,"Отступ от края",lambda r:(
            _spinbox(r,self.v_wm_margin,4,80,4).pack(side="left"),
            _hint(r,"пикселей"),
        ))
        _field(wb,"Прозрачность %",lambda r:(
            _spinbox(r,self.v_wm_opacity,10,100,4).pack(side="left"),
            _hint(r,"100 = полностью непрозрачный"),
        ))

        bfw=tk.Frame(body,bg=D["bg1"]); bfw.pack(fill="x",padx=20,pady=(4,10))
        _pill(bfw,"  Добавить подпись на фото",D["amber"],
              self._start_watermark,PIL_AVAILABLE).pack(fill="x",ipady=2)

        self._wm_toggle()  # hide by default

        _divider(body)

        # ── Удаление метаданных ──
        msec=_section(body,"Удаление метаданных (EXIF)",D["rose"])

        tk.Label(msec,
                 text="Удаляет GPS, камеру, дату съёмки, автора и другие скрытые данные из фото.",
                 font=("Segoe UI",9),bg=msec.cget("bg"),fg=D["t1"]).pack(anchor="w",pady=(0,8))

        # Что именно удалять
        opts_row=tk.Frame(msec,bg=msec.cget("bg")); opts_row.pack(fill="x",pady=(0,6))
        for text,var in [
            ("GPS",        self.v_meta_gps),
            ("Камера",     self.v_meta_camera),
            ("Дата съёмки",self.v_meta_date),
            ("Автор",      self.v_meta_author),
            ("Всё EXIF",   self.v_meta_all),
        ]:
            tk.Checkbutton(opts_row,text=text,variable=var,
                           bg=msec.cget("bg"),fg=D["t1"],
                           selectcolor=D["bg3"],
                           activebackground=msec.cget("bg"),
                           font=("Segoe UI",9)).pack(side="left",padx=(0,16))

        # Подсказка: "Всё EXIF" перекрывает остальные
        _hint(msec,"«Всё EXIF» удаляет все метаданные сразу")
        msec.pack_propagate(False)

        bmeta=tk.Frame(body,bg=D["bg1"]); bmeta.pack(fill="x",padx=20,pady=(4,14))
        _pill(bmeta,"  Удалить метаданные",D["rose"],
              self._start_strip_meta,PIL_AVAILABLE).pack(fill="x",ipady=2)
    def _build_video_page(self):
        p=tk.Frame(self._cf,bg=D["bg1"]); self.pages["video"]=p
        _page_header(p,"Конвертер видео","Перекодирование видео в другие форматы",D["blue"])
        body=tk.Frame(p,bg=D["bg1"],pady=10); body.pack(fill="both",expand=True)
        sec=_section(body,"Параметры",D["blue"])
        _field(sec,"Выходной формат",lambda r:(_combo(r,self.v_vid_fmt,VIDEO_FORMATS,10).pack(side="left"),))
        _field(sec,"Качество",lambda r:(_radio_group(r,self.v_vid_q,[("Низкое","low"),("Среднее","medium"),("Высокое","high")],D["blue"]).pack(side="left"),))
        bf=tk.Frame(body,bg=D["bg1"]); bf.pack(fill="x",padx=20,pady=(2,14))
        _pill(bf,"  Конвертировать видео",D["blue"],self._start_video_conv,MOVIEPY_AVAILABLE).pack(fill="x",ipady=2)
        if not MOVIEPY_AVAILABLE:
            tk.Label(bf,text="⚠  MoviePy не установлен",font=("Segoe UI",8,"italic"),bg=D["bg1"],fg=D["t2"]).pack(anchor="w",pady=4)

    # ── page: create ─────────────────────────────────────────
    def _build_create_page(self):
        p=tk.Frame(self._cf,bg=D["bg1"]); self.pages["create"]=p
        _page_header(p,"Создатель видео","Создание 10-секундного видео из фотографии",D["violet"])
        body=tk.Frame(p,bg=D["bg1"],padx=20,pady=16); body.pack(fill="both",expand=True)
        tk.Label(body,text="Каждая фотография превращается в отдельное 10-секундное видео.",
                 font=("Segoe UI",9),bg=D["bg1"],fg=D["t1"]).pack(anchor="w",pady=(0,16))
        tiles=tk.Frame(body,bg=D["bg1"]); tiles.pack(fill="x")
        for label,fmt,col in [("MP4","mp4",D["teal"]),("AVI","avi",D["blue"]),("MOV","mov",D["violet"])]:
            tile=tk.Frame(tiles,bg=D["bg2"],cursor="hand2" if MOVIEPY_AVAILABLE else "arrow")
            tile.pack(side="left",padx=(0,10),fill="x",expand=True)
            fg=col if MOVIEPY_AVAILABLE else D["t2"]
            tk.Label(tile,text=label,font=("Courier New",20,"bold"),bg=D["bg2"],fg=fg,pady=14).pack(fill="x")
            tk.Label(tile,text=f".{fmt}",font=("Segoe UI",9),bg=D["bg2"],fg=D["t2"],pady=6).pack(fill="x")
            if MOVIEPY_AVAILABLE:
                for w in [tile]+list(tile.winfo_children()):
                    w.bind("<Button-1>",lambda e,v=fmt:self._start_create(v))
                tile.bind("<Enter>",lambda e,t=tile:t.configure(bg=D["bg3"]))
                tile.bind("<Leave>",lambda e,t=tile:t.configure(bg=D["bg2"]))
        if not MOVIEPY_AVAILABLE:
            tk.Label(body,text="⚠  MoviePy не установлен",font=("Segoe UI",8,"italic"),bg=D["bg1"],fg=D["t2"]).pack(anchor="w",pady=(12,0))

    # ── page: merge ──────────────────────────────────────────
    def _build_merge_page(self):
        p=tk.Frame(self._cf,bg=D["bg1"]); self.pages["merge"]=p
        _page_header(p,"Объединение видео","Склейка нескольких видеофайлов в один",D["amber"])
        body=tk.Frame(p,bg=D["bg1"],pady=10); body.pack(fill="both",expand=True)
        sec=_section(body,"Параметры",D["amber"])
        _field(sec,"Выходной формат",lambda r:(_combo(r,self.v_merge_fmt,MERGE_FORMATS,10).pack(side="left"),))
        _field(sec,"Качество",lambda r:(_radio_group(r,self.v_merge_q,[("Низкое","low"),("Среднее","medium"),("Высокое","high")],D["amber"]).pack(side="left"),))
        bf=tk.Frame(body,bg=D["bg1"]); bf.pack(fill="x",padx=20,pady=(2,14))
        tk.Label(bf,text="ℹ  Видео объединяются в порядке выбора",font=("Segoe UI",8,"italic"),bg=D["bg1"],fg=D["t2"]).pack(anchor="w",pady=(0,6))
        avail=MOVIEPY_AVAILABLE or FFMPEG_AVAILABLE
        _pill(bf,"  Объединить видео",D["amber"],self._start_merge,avail).pack(fill="x",ipady=2)
        if not avail:
            tk.Label(bf,text="⚠  FFMPEG не найден",font=("Segoe UI",8,"italic"),bg=D["bg1"],fg=D["t2"]).pack(anchor="w",pady=4)

    # ── page: compress ───────────────────────────────────────
    def _build_compress_page(self):
        p=tk.Frame(self._cf,bg=D["bg1"]); self.pages["compress"]=p
        _page_header(p,"Сжатие","Уменьшение размера видео и фото",D["rose"])
        body=tk.Frame(p,bg=D["bg1"],pady=10); body.pack(fill="both",expand=True)

        # ── Видео ──
        vsec=_section(body,"Сжатие видео",D["rose"])
        def _crf_hint(val,lbl):
            v=int(float(val))
            if v<=22:   t,c="Высокое качество — файл большой",D["teal"]
            elif v<=28: t,c="Средний баланс качество/размер",D["amber"]
            elif v<=35: t,c="Низкое качество — файл меньше",D["amber"]
            else:       t,c="Очень низкое качество",D["rose"]
            lbl.configure(text=t,fg=c); self._crf_val_lbl=lbl
        tk.Label(vsec,text="Степень сжатия (CRF)",font=("Segoe UI",9),bg=vsec.cget("bg"),fg=D["t1"]).pack(anchor="w",pady=(0,4))
        self._crf_val_lbl,_=_slider_block(vsec,self.v_crf,18,51,D["rose"],_crf_hint)
        _field(vsec,"Скорость кодирования",lambda r:(_radio_group(r,self.v_preset,[("Быстро","ultrafast"),("Авто","medium"),("Медленно","slow")],D["rose"]).pack(side="left"),))
        _field(vsec,"Разрешение",lambda r:(_combo(r,self.v_res,["original","1080p","720p","480p","360p"],12).pack(side="left"),_hint(r,"Уменьшение даёт значительное сжатие")))
        vbf=tk.Frame(body,bg=D["bg1"]); vbf.pack(fill="x",padx=20,pady=(2,14))
        _ghost(vbf,"  Анализ перед сжатием",D["rose"],self._analyze_compress,FFMPEG_AVAILABLE).pack(side="left",padx=(0,8),ipady=2)
        _pill(vbf,"  Сжать видео",D["rose"],self._start_compress,FFMPEG_AVAILABLE).pack(side="left",ipady=2)
        if not FFMPEG_AVAILABLE:
            tk.Label(body,text="⚠  FFMPEG не найден — перейдите в Инструменты",
                     font=("Segoe UI",8,"italic"),bg=D["bg1"],fg=D["t2"]).pack(anchor="w",padx=20)

        _divider(body)

        # ── Фото ──
        psec=_section(body,"Сжатие фото",D["teal"])
        def _cmp_hint(val,lbl):
            v=int(float(val))
            if v>=90:   t,c="Почти без потерь — файл большой",D["teal"]
            elif v>=75: t,c="Хорошее качество — хороший баланс",D["amber"]
            elif v>=50: t,c="Среднее качество — файл меньше",D["amber"]
            else:       t,c="Низкое качество — максимальное сжатие",D["rose"]
            lbl.configure(text=t,fg=c); self._cmp_val_lbl=lbl
        tk.Label(psec,text="Качество (1–100)",font=("Segoe UI",9),bg=psec.cget("bg"),fg=D["t1"]).pack(anchor="w",pady=(0,4))
        self._cmp_val_lbl,_=_slider_block(psec,self.v_cmp_q,1,100,D["teal"],_cmp_hint)
        _field(psec,"Макс. сторона (px)",lambda r:(_combo(r,self.v_cmp_maxpx,["без ограничений","4096","2048","1920","1280","1024","800","640"],16).pack(side="left"),_hint(r,"Уменьшает если сторона больше")))
        _field(psec,"Сохранить как",lambda r:(_combo(r,self.v_cmp_fmt,["jpg","webp","png"],8).pack(side="left"),_hint(r,"JPG/WebP дают лучшее сжатие")))
        pbf=tk.Frame(body,bg=D["bg1"]); pbf.pack(fill="x",padx=20,pady=(2,14))
        _ghost(pbf,"  Анализ размеров",D["teal"],self._analyze_photos,PIL_AVAILABLE).pack(side="left",padx=(0,8),ipady=2)
        _pill(pbf,"  Сжать фото",D["teal"],self._start_compress_photo,PIL_AVAILABLE).pack(side="left",ipady=2)
        if not PIL_AVAILABLE:
            tk.Label(body,text="⚠  PIL не установлен — перейдите в Инструменты",
                     font=("Segoe UI",8,"italic"),bg=D["bg1"],fg=D["t2"]).pack(anchor="w",padx=20)

    # ── page: tools ──────────────────────────────────────────
    def _build_tools_page(self):
        p=tk.Frame(self._cf,bg=D["bg1"]); self.pages["tools"]=p
        _page_header(p,"Инструменты","Диагностика и обслуживание",D["green"])
        body=tk.Frame(p,bg=D["bg1"],padx=20,pady=14); body.pack(fill="both",expand=True)
        tools=[
            ("Проверить целостность видео","Анализирует файлы на повреждения через FFMPEG",D["blue"],self._check_video,FFMPEG_AVAILABLE),
            ("Восстановить повреждённое видео","Перекодирует файл для устранения повреждений",D["green"],self._repair_video,FFMPEG_AVAILABLE),
            ("Скачать VLC","Откроет сайт загрузки VLC media player",D["amber"],self._install_vlc,True),
            ("Очистить временные файлы","Удалить вспомогательные файлы из рабочей папки",D["violet"],self._clean_temp,True),
            ("О программе","Версия, состав, зависимости",D["teal"],self._show_about,True),
        ]
        for title,desc,col,cmd,enabled in tools:
            card=tk.Frame(body,bg=D["bg2"],cursor="hand2" if enabled else "arrow"); card.pack(fill="x",pady=4)
            tk.Frame(card,bg=col if enabled else D["t2"],width=2).pack(side="left",fill="y")
            inner=tk.Frame(card,bg=D["bg2"],padx=14,pady=11); inner.pack(fill="x",side="left")
            head=tk.Frame(inner,bg=D["bg2"]); head.pack(fill="x")
            tk.Label(head,text=title,font=("Segoe UI",10,"bold"),bg=D["bg2"],fg=D["t0"] if enabled else D["t2"]).pack(side="left")
            if not enabled:
                tk.Label(head,text=" недоступно ",font=("Segoe UI",7,"bold"),bg=D["rose_bg"],fg=D["rose"],padx=4).pack(side="left",padx=8)
            tk.Label(inner,text=desc,font=("Segoe UI",8),bg=D["bg2"],fg=D["t2"]).pack(anchor="w",pady=(2,0))
            if enabled:
                def _bind(w,c=cmd,f=card):
                    w.bind("<Button-1>",lambda e:c())
                    w.bind("<Enter>",lambda e,x=f:x.configure(bg=D["bg3"]))
                    w.bind("<Leave>",lambda e,x=f:x.configure(bg=D["bg2"]))
                _bind(card); _bind(inner)
                for w in head.winfo_children(): _bind(w)

    # ══════════════════════════════════════════════════════════
    #  BUSINESS LOGIC
    # ══════════════════════════════════════════════════════════

    def _wm_toggle(self):
        if self.v_wm_enabled.get():
            self._wm_body.pack(fill="x")
        else:
            self._wm_body.pack_forget()

    def _start_watermark(self):
        if not PIL_AVAILABLE: messagebox.showerror("Ошибка","PIL не установлен!"); return
        self.root.withdraw()
        threading.Thread(target=self._run_watermark,daemon=True).start()

    def _run_watermark(self):
        try:
            files=self._pick_files("photo")
            if not files: return self._warn("Файлы не выбраны")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")

            add_date   = self.v_wm_date.get()
            date_manual= self.v_wm_date_text.get().strip()
            comment    = self.v_wm_text.get().strip()
            corner     = self.v_wm_corner.get()
            font_size  = self.v_wm_size.get()
            color_name = self.v_wm_color.get()
            opacity    = self.v_wm_opacity.get()
            margin     = self.v_wm_margin.get()

            color_map = {
                "белый":  (255,255,255),
                "чёрный": (0,0,0),
                "жёлтый": (255,220,50),
                "красный":(220,50,50),
                "синий":  (80,150,255),
            }
            rgb = color_map.get(color_name,(255,255,255))
            alpha = int(opacity/100*255)
            rgba = rgb + (alpha,)

            ok=fail=0
            self._show_progress(len(files),D["amber"])

            # Try to load a font
            from PIL import ImageDraw, ImageFont
            font = None
            for font_path in [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/tahoma.ttf",
            ]:
                if os.path.exists(font_path):
                    try: font=ImageFont.truetype(font_path,font_size); break
                    except: pass
            if font is None:
                font=ImageFont.load_default()

            for i,path in enumerate(files,1):
                if self.cancel_flag: break
                try:
                    name=Path(path).stem
                    ext=Path(path).suffix.lower() or ".jpg"
                    op=os.path.join(out,f"{name}_signed{ext}")
                    n=1
                    while os.path.exists(op):
                        op=os.path.join(out,f"{name}_signed_{n}{ext}"); n+=1

                    with Image.open(path) as img:
                        # Get date string
                        date_str=""
                        if add_date:
                            if date_manual:
                                # Вручную введённая дата
                                date_str = date_manual
                            else:
                                # Авто: сначала из EXIF, потом дата файла
                                try:
                                    exif=img._getexif()
                                    if exif:
                                        for tag_id,val in exif.items():
                                            from PIL.ExifTags import TAGS
                                            if TAGS.get(tag_id)=="DateTimeOriginal":
                                                parts=val.split(" ")
                                                d=parts[0].replace(":",".") if parts else val
                                                t=parts[1][:5] if len(parts)>1 else ""
                                                date_str=f"{d} {t}".strip()
                                                break
                                except: pass
                                if not date_str:
                                    mtime=os.path.getmtime(path)
                                    date_str=datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M")

                        # Build text
                        lines=[]
                        if date_str: lines.append(date_str)
                        if comment:  lines.append(comment)
                        if not lines:
                            self.logger.add(f"Нет текста для {Path(path).name} — пропущено","WARNING")
                            ok+=1; self._upd(i,len(files),f"✓ {name}"); continue

                        text="\n".join(lines)

                        # Convert to RGBA for transparency support
                        base=img.convert("RGBA")
                        w,h=base.size

                        # Create text layer
                        txt_layer=Image.new("RGBA",base.size,(0,0,0,0))
                        draw=ImageDraw.Draw(txt_layer)

                        # Measure text
                        bbox=draw.textbbox((0,0),text,font=font)
                        tw=bbox[2]-bbox[0]; th=bbox[3]-bbox[1]

                        # Position
                        if corner=="правый нижний":   x=w-tw-margin; y=h-th-margin
                        elif corner=="левый нижний":  x=margin;       y=h-th-margin
                        elif corner=="правый верхний":x=w-tw-margin; y=margin
                        else:                         x=margin;       y=margin  # левый верхний

                        # Shadow for readability (semi-transparent black)
                        shadow_col=(0,0,0,min(alpha,180))
                        for dx,dy in [(1,1),(2,2),(-1,1),(1,-1)]:
                            draw.text((x+dx,y+dy),text,font=font,fill=shadow_col)

                        # Main text
                        draw.text((x,y),text,font=font,fill=rgba)

                        # Merge layers
                        result=Image.alpha_composite(base,txt_layer)

                        # Save (convert back to RGB for jpg)
                        if ext in (".jpg",".jpeg"):
                            result=result.convert("RGB")
                            result.save(op,quality=95,optimize=True)
                        else:
                            result.save(op)

                    ok+=1; self._upd(i,len(files),f"✓ {name}")
                    self.logger.add(f"Подпись добавлена: {Path(path).name}","SUCCESS")
                except Exception as e:
                    fail+=1; self.logger.add(f"Ошибка {Path(path).name}: {e}","ERROR")

            if not self.cancel_flag:
                self._done("Добавление подписи",ok,fail,out)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _start_strip_meta(self):
        if not PIL_AVAILABLE: messagebox.showerror("Ошибка","PIL не установлен!"); return
        self.root.withdraw()
        threading.Thread(target=self._run_strip_meta,daemon=True).start()

    def _run_strip_meta(self):
        try:
            files=self._pick_files("photo")
            if not files: return self._warn("Файлы не выбраны")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")

            strip_all    = self.v_meta_all.get()
            strip_gps    = self.v_meta_gps.get()
            strip_camera = self.v_meta_camera.get()
            strip_date   = self.v_meta_date.get()
            strip_author = self.v_meta_author.get()

            if not any([strip_all, strip_gps, strip_camera, strip_date, strip_author]):
                return self._warn("Выберите хотя бы один тип метаданных для удаления")

            # EXIF tag groups
            # GPS tags: 0x0000–0x001F in GPS IFD (tag 34853)
            GPS_TAGS = {34853}  # GPSInfo IFD pointer

            # Camera/device tags
            CAMERA_TAGS = {
                271,   # Make
                272,   # Model
                305,   # Software
                306,   # DateTime (file change) — also date
                315,   # Artist
                316,   # HostComputer
                42033, # BodySerialNumber
                42034, # LensSpecification
                42035, # LensMake
                42036, # LensModel
                42037, # LensSerialNumber
                37386, # FocalLength
                37385, # Flash
                37383, # MeteringMode
                33434, # ExposureTime
                33437, # FNumber
                34855, # ISOSpeedRatings
            }

            DATE_TAGS = {
                306,   # DateTime
                36867, # DateTimeOriginal
                36868, # DateTimeDigitized
            }

            AUTHOR_TAGS = {
                315,   # Artist
                33432, # Copyright
                305,   # Software
            }

            ok=fail=0
            self._show_progress(len(files),D["rose"])

            from PIL import Image as PILImage
            import piexif

            for i,path in enumerate(files,1):
                if self.cancel_flag: break
                try:
                    name=Path(path).stem
                    ext=Path(path).suffix.lower()
                    op=os.path.join(out,f"{name}_clean{ext}")
                    n=1
                    while os.path.exists(op):
                        op=os.path.join(out,f"{name}_clean_{n}{ext}"); n+=1

                    with PILImage.open(path) as img:
                        if strip_all:
                            # Пересохраняем без каких-либо метаданных
                            data=img.tobytes()
                            clean=PILImage.frombytes(img.mode,img.size,data)
                            if ext in ('.jpg','.jpeg'):
                                clean.save(op,format='JPEG',quality=95,optimize=True)
                            else:
                                clean.save(op)
                        else:
                            # Выборочное удаление через piexif
                            try:
                                exif_dict=piexif.load(img.info.get('exif',b''))
                            except:
                                exif_dict={"0th":{},"Exif":{},"GPS":{},"1st":{}}

                            if strip_gps:
                                exif_dict["GPS"]={}

                            if strip_camera:
                                for tag in list(exif_dict.get("0th",{}).keys()):
                                    if tag in CAMERA_TAGS:
                                        del exif_dict["0th"][tag]
                                for tag in list(exif_dict.get("Exif",{}).keys()):
                                    if tag in CAMERA_TAGS:
                                        del exif_dict["Exif"][tag]

                            if strip_date:
                                for ifd in ["0th","Exif"]:
                                    for tag in list(exif_dict.get(ifd,{}).keys()):
                                        if tag in DATE_TAGS:
                                            del exif_dict[ifd][tag]

                            if strip_author:
                                for ifd in ["0th","Exif"]:
                                    for tag in list(exif_dict.get(ifd,{}).keys()):
                                        if tag in AUTHOR_TAGS:
                                            del exif_dict[ifd][tag]

                            exif_bytes=piexif.dump(exif_dict)
                            if ext in ('.jpg','.jpeg'):
                                img.save(op,format='JPEG',exif=exif_bytes,quality=95,optimize=True)
                            elif ext=='.png':
                                # PNG не поддерживает EXIF напрямую — просто пересохраняем
                                img.save(op,format='PNG')
                            else:
                                img.save(op,exif=exif_bytes)

                    ok+=1
                    self._upd(i,len(files),f"✓ {name}")
                    self.logger.add(f"Метаданные удалены: {Path(path).name}","SUCCESS")
                except ImportError:
                    # piexif не установлен — используем простой метод
                    try:
                        with PILImage.open(path) as img:
                            data=img.tobytes()
                            clean=PILImage.frombytes(img.mode,img.size,data)
                            ext2=Path(path).suffix.lower()
                            if ext2 in ('.jpg','.jpeg'):
                                clean.save(op,format='JPEG',quality=95,optimize=True)
                            else:
                                clean.save(op)
                        ok+=1
                        self._upd(i,len(files),f"✓ {name} (все EXIF удалены)")
                        self.logger.add(f"Метаданные удалены: {Path(path).name}","SUCCESS")
                    except Exception as e2:
                        fail+=1
                        self.logger.add(f"Ошибка {Path(path).name}: {e2}","ERROR")
                except Exception as e:
                    fail+=1
                    self.logger.add(f"Ошибка {Path(path).name}: {e}","ERROR")
                    self._upd(i,len(files),f"✗ {Path(path).name}")

            if not self.cancel_flag:
                self._done("Удаление метаданных",ok,fail,out)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _start_photo(self):
        if not PIL_AVAILABLE: messagebox.showerror("Ошибка","PIL не установлен!"); return
        self.root.withdraw(); threading.Thread(target=self._run_photo,daemon=True).start()

    def _run_photo(self):
        try:
            files=self._pick_files("photo")
            if not files: return self._warn("Файлы не выбраны")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            fmt=self.v_photo_fmt.get(); q=int(self.v_photo_q.get()); ico=int(self.v_ico_sz.get())
            ok=fail=0; self._show_progress(len(files),D["teal"])
            for i,path in enumerate(files,1):
                if self.cancel_flag: break
                try:
                    name=Path(path).stem; op=os.path.join(out,f"{name}.{fmt}")
                    with Image.open(path) as img:
                        if fmt in ('jpg','jpeg') and img.mode in ('RGBA','P'): img=img.convert('RGB')
                        if fmt=='ico': img.save(op,format='ICO',sizes=[(ico,ico)])
                        elif fmt in ('jpg','jpeg'): img.save(op,quality=q,optimize=True)
                        else: img.save(op)
                    ok+=1; self._upd(i,len(files),f"✓ {name}.{fmt}")
                except Exception as e:
                    fail+=1; self.logger.add(f"Ошибка {Path(path).name}: {e}","ERROR")
            if not self.cancel_flag: self._done("Конвертация фото",ok,fail,out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _analyze_photos(self):
        if not PIL_AVAILABLE: messagebox.showerror("Ошибка","PIL не установлен!"); return
        files=self._pick_files("photo")
        if not files: return
        import io
        q=self.v_cmp_q.get(); fmt=self.v_cmp_fmt.get(); maxpx=self.v_cmp_maxpx.get()
        limit=int(maxpx) if maxpx!="без ограничений" else 0
        results=[]
        for fp in files:
            try:
                orig=os.path.getsize(fp)
                with Image.open(fp) as img:
                    w,h=img.size; nw,nh=w,h
                    if limit and max(w,h)>limit:
                        r=limit/max(w,h); nw,nh=int(w*r),int(h*r)
                    buf=io.BytesIO(); tmp=img.copy()
                    if nw!=w or nh!=h: tmp=tmp.resize((nw,nh),Image.LANCZOS)
                    if fmt in ('jpg','jpeg'):
                        if tmp.mode in ('RGBA','P'): tmp=tmp.convert('RGB')
                        tmp.save(buf,format='JPEG',quality=q,optimize=True)
                    elif fmt=='webp': tmp.save(buf,format='WEBP',quality=q)
                    else: tmp.save(buf,format='PNG',optimize=True)
                    est=buf.tell()
                results.append({'file':Path(fp).name,'orig':orig,'est':est,
                                'res_orig':f"{w}×{h}",'res_new':f"{nw}×{nh}" if (nw!=w or nh!=h) else "без изм."})
            except Exception as e:
                results.append({'file':Path(fp).name,'error':str(e)})
        self._show_photo_analysis(results,q,fmt,maxpx)

    def _show_photo_analysis(self,results,q,fmt,maxpx):
        def fsz(b): return f"{b/1024/1024:.2f} MB" if b>=1024*1024 else f"{b/1024:.0f} KB"
        win=tk.Toplevel(self.root); win.title("Анализ сжатия фото"); win.geometry("800x460"); win.configure(bg=D["bg0"])
        hf=tk.Frame(win,bg=D["bg2"],height=46); hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf,bg=D["teal"],width=2).pack(side="left",fill="y")
        tk.Label(hf,text="  АНАЛИЗ СЖАТИЯ ФОТО",font=("Courier New",12,"bold"),bg=D["bg2"],fg=D["teal"]).pack(side="left",pady=10)
        tk.Label(hf,text=f"  качество {q}  ·  {fmt.upper()}  ·  макс.: {maxpx}",font=("Segoe UI",9),bg=D["bg2"],fg=D["t1"]).pack(side="left")
        tf=tk.Frame(win,bg=D["bg0"]); tf.pack(fill="both",expand=True,padx=10,pady=8)
        cols=("Файл","Оригинал","→ После","Экономия","Было","Станет")
        tree=ttk.Treeview(tf,columns=cols,show="headings")
        for col,w in zip(cols,[200,90,90,120,100,110]):
            tree.heading(col,text=col); tree.column(col,width=w,anchor="center")
        tree.tag_configure("good",foreground=D["teal"]); tree.tag_configure("mid",foreground=D["amber"]); tree.tag_configure("err",foreground=D["t2"])
        tot_o=tot_e=0
        for r in results:
            if 'error' in r: tree.insert("","end",values=(r['file'],"—","—","—","—",r['error']),tags=("err",)); continue
            s=(1-r['est']/r['orig'])*100 if r['orig'] else 0; tot_o+=r['orig']; tot_e+=r['est']
            tree.insert("","end",values=(r['file'],fsz(r['orig']),fsz(r['est']),f"−{s:.0f}%  ({fsz(r['orig']-r['est'])})",r['res_orig'],r['res_new']),tags=("good" if s>20 else "mid",))
        sb2=ttk.Scrollbar(tf,orient="vertical",command=tree.yview,style="Dark.Vertical.TScrollbar")
        tree.configure(yscrollcommand=sb2.set); tree.pack(side="left",fill="both",expand=True); sb2.pack(side="right",fill="y")
        ft=tk.Frame(win,bg=D["bg2"],height=44); ft.pack(fill="x",side="bottom"); ft.pack_propagate(False)
        if tot_o:
            ts=(1-tot_e/tot_o)*100
            tk.Label(ft,text=f"  Итого: {fsz(tot_o)} → {fsz(tot_e)}  (−{ts:.0f}%)",font=("Segoe UI",9,"bold"),bg=D["bg2"],fg=D["teal"]).pack(side="left",padx=12)
        _pill(ft,"  Сжать фото",D["teal"],lambda:(win.destroy(),self._start_compress_photo()),PIL_AVAILABLE).pack(side="right",padx=10,pady=6,ipadx=4)
        tk.Button(ft,text="Закрыть",font=("Segoe UI",9),bg=D["bg3"],fg=D["t1"],relief="flat",command=win.destroy).pack(side="right",padx=6,pady=6,ipadx=8)

    def _start_compress_photo(self):
        if not PIL_AVAILABLE: messagebox.showerror("Ошибка","PIL не установлен!"); return
        self.root.withdraw(); threading.Thread(target=self._run_compress_photo,daemon=True).start()

    def _run_compress_photo(self):
        try:
            files=self._pick_files("photo")
            if not files: return self._warn("Файлы не выбраны")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            q=self.v_cmp_q.get(); fmt=self.v_cmp_fmt.get(); maxpx=self.v_cmp_maxpx.get()
            limit=int(maxpx) if maxpx!="без ограничений" else 0
            ok=fail=0; self._show_progress(len(files),D["teal"])
            for i,path in enumerate(files,1):
                if self.cancel_flag: break
                try:
                    name=Path(path).stem; op=os.path.join(out,f"{name}_compressed.{fmt}")
                    n=1
                    while os.path.exists(op): op=os.path.join(out,f"{name}_compressed_{n}.{fmt}"); n+=1
                    with Image.open(path) as img:
                        w,h=img.size
                        if limit and max(w,h)>limit:
                            ratio=limit/max(w,h); img=img.resize((int(w*ratio),int(h*ratio)),Image.LANCZOS)
                        if fmt in ('jpg','jpeg'):
                            if img.mode in ('RGBA','P'): img=img.convert('RGB')
                            img.save(op,format='JPEG',quality=q,optimize=True)
                        elif fmt=='webp': img.save(op,format='WEBP',quality=q)
                        else: img.save(op,format='PNG',optimize=True)
                    orig=os.path.getsize(path); comp=os.path.getsize(op); saved=(1-comp/orig)*100
                    self.logger.add(f"Сжато: {Path(path).name} | {orig/1024:.0f} KB → {comp/1024:.0f} KB (−{saved:.0f}%)","SUCCESS")
                    ok+=1; self._upd(i,len(files),f"✓ {name}  −{saved:.0f}%")
                except Exception as e:
                    fail+=1; self.logger.add(f"Ошибка {Path(path).name}: {e}","ERROR")
            if not self.cancel_flag: self._done("Сжатие фото",ok,fail,out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _start_video_conv(self):
        if not MOVIEPY_AVAILABLE: messagebox.showerror("Ошибка","MoviePy не установлен!"); return
        self.root.withdraw(); threading.Thread(target=self._run_video_conv,daemon=True).start()

    def _run_video_conv(self):
        try:
            files=self._pick_files("video")
            if not files: return self._warn("Файлы не выбраны")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            fmt=self.v_vid_fmt.get(); q=self.v_vid_q.get()
            qs={'low':('500k','ultrafast'),'medium':('1000k','medium'),'high':('2000k','slow')}
            bitrate,preset=qs.get(q,qs['medium']); ok=fail=0; self._show_progress(len(files),D["blue"])
            for i,path in enumerate(files,1):
                if self.cancel_flag: break
                try:
                    name=Path(path).stem; op=os.path.join(out,f"{name}.{fmt}")
                    with VideoFileClip(path) as v:
                        if fmt=='gif': v.write_gif(op,fps=10,program='ffmpeg',opt='optimizeplus')
                        else:
                            codec={'mp4':'libx264','avi':'libx264','mov':'libx264','mkv':'libx264','webm':'libvpx'}.get(fmt,'libx264')
                            v.write_videofile(op,codec=codec,audio_codec='aac',bitrate=bitrate,preset=preset,logger=None)
                    ok+=1; self._upd(i,len(files),f"✓ {name}.{fmt}")
                except Exception as e:
                    fail+=1; self.logger.add(f"Ошибка {Path(path).name}: {e}","ERROR")
            if not self.cancel_flag: self._done("Конвертация видео",ok,fail,out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _fix_size(self,path):
        try:
            with Image.open(path) as img:
                w,h=img.size
                if w%2 or h%2:
                    tp=os.path.join(self.temp_dir,f"fx_{int(time.time())}.png")
                    img.resize((w+(w%2),h+(h%2)),Image.Resampling.LANCZOS).save(tp,'PNG'); return tp
                return path
        except: return path

    def _start_create(self,fmt):
        if not MOVIEPY_AVAILABLE: messagebox.showerror("Ошибка","MoviePy не установлен!"); return
        self._video_ext=fmt; self.root.withdraw()
        threading.Thread(target=self._run_create,daemon=True).start()

    def _run_create(self):
        try:
            files=self._pick_files("photo")
            if not files: return self._warn("Файлы не выбраны")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            ok=fail=0; tmp=[]; self._show_progress(len(files),D["violet"])
            for i,path in enumerate(files,1):
                if self.cancel_flag: break
                try:
                    name=Path(path).stem; op=os.path.join(out,f"{name}.{self._video_ext}")
                    wp=self._fix_size(path)
                    if wp!=path: tmp.append(wp)
                    with ImageClip(wp).with_duration(DURATION) as clip:
                        clip.fps=FPS
                        clip.write_videofile(op,codec='libx264',audio=False,logger=None,
                            ffmpeg_params=["-pix_fmt","yuv420p","-vf","scale=trunc(iw/2)*2:trunc(ih/2)*2"])
                    ok+=1; self._upd(i,len(files),f"✓ {name}.{self._video_ext}")
                except Exception as e:
                    fail+=1; self.logger.add(f"Ошибка {Path(path).name}: {e}","ERROR")
            for t in tmp:
                try: os.remove(t)
                except: pass
            if not self.cancel_flag: self._done("Создание видео",ok,fail,out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _start_merge(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка","FFMPEG не найден!"); return
        self.root.withdraw(); threading.Thread(target=self._run_merge,daemon=True).start()

    def _run_merge(self):
        try:
            files=self._pick_files("video")
            if not files or len(files)<2: return self._warn("Выберите минимум 2 видеофайла")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            order="\n".join(f"{n}. {Path(f).name}" for n,f in enumerate(files,1))
            if not messagebox.askyesno("Подтверждение",f"Объединить {len(files)} видео?\n\n{order}\n\nПродолжить?"):
                self._cleanup(); return
            self._merge_ffmpeg(files,out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _merge_ffmpeg(self,files,out):
        fmt=self.v_merge_fmt.get(); q=self.v_merge_q.get()
        qs={'low':('28','ultrafast'),'medium':('23','medium'),'high':('18','slow')}
        crf,preset=qs.get(q,qs['medium'])
        base=f"{Path(files[0]).stem}_and_{Path(files[1]).stem}" if len(files)==2 else f"merged_{len(files)}_videos"
        op=os.path.join(out,f"{base}.{fmt}"); n=1
        while os.path.exists(op): op=os.path.join(out,f"{base}_{n}.{fmt}"); n+=1
        tmp=os.path.join(self.temp_dir,f"mrg_{int(time.time())}.{fmt}")
        self._show_progress(len(files),D["amber"])
        try:
            inputs,fv,fa=[],[],[]
            for i,f in enumerate(files): inputs+=['-i',f]; fv.append(f'[{i}:v]'); fa.append(f'[{i}:a]')
            fg=f"{''.join(fv)}{''.join(fa)}concat=n={len(files)}:v=1:a=1[v][a]"
            cmd=([FFMPEG_PATH]+inputs+['-filter_complex',fg,'-map','[v]','-map','[a]',
                  '-c:v','libx264','-c:a','aac','-preset',preset,'-crf',crf,'-movflags','+faststart','-y',tmp])
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            while proc.poll() is None:
                if self.cancel_flag: proc.terminate(); os.path.exists(tmp) and os.remove(tmp); return
                time.sleep(0.4)
            if proc.wait()==0 and os.path.exists(tmp) and os.path.getsize(tmp)>1000:
                os.path.exists(op) and os.remove(op); os.rename(tmp,op)
                if self.progress_popup: self.progress_popup.destroy(); self.progress_popup=None
                messagebox.showinfo("Готово",f"✓ Объединено!\n\nСохранено:\n{op}"); self._cleanup()
            else:
                os.path.exists(tmp) and os.remove(tmp); self._merge_alt(files,out,fmt,crf,preset,base)
        except Exception as e:
            try: os.path.exists(tmp) and os.remove(tmp)
            except: pass
            try: self._merge_alt(files,out,fmt,crf,preset,base)
            except Exception as e2:
                self._err(f"Ошибка объединения: {e2}")
                if self.progress_popup: self.progress_popup.destroy()
                self._cleanup()

    def _merge_alt(self,files,out,fmt,crf,preset,base):
        op=os.path.join(out,f"{base}.{fmt}"); n=1
        while os.path.exists(op): op=os.path.join(out,f"{base}_{n}.{fmt}"); n+=1
        tmp=os.path.join(self.temp_dir,f"mrg_alt_{int(time.time())}.{fmt}")
        lf=os.path.join(self.temp_dir,"clist.txt"); tsf=[]
        with open(lf,'w',encoding='utf-8') as f:
            for i,fp in enumerate(files):
                ts=os.path.join(self.temp_dir,f"t{i}_{int(time.time())}.ts")
                r=subprocess.run([FFMPEG_PATH,'-i',fp,'-c','copy','-bsf:v','h264_mp4toannexb','-f','mpegts','-y',ts],capture_output=True)
                if r.returncode==0 and os.path.exists(ts) and os.path.getsize(ts)>0:
                    tsf.append(ts); f.write(f"file '{ts.replace(chr(92),'/')}'\n")
        if len(tsf)<2: raise Exception("Недостаточно файлов")
        r=subprocess.run([FFMPEG_PATH,'-f','concat','-safe','0','-i',lf,'-c:v','libx264','-c:a','aac',
                          '-preset',preset,'-crf',crf,'-movflags','+faststart','-y',tmp],capture_output=True)
        if r.returncode==0 and os.path.exists(tmp) and os.path.getsize(tmp)>1000:
            os.path.exists(op) and os.remove(op); os.rename(tmp,op)
            if self.progress_popup: self.progress_popup.destroy(); self.progress_popup=None
            messagebox.showinfo("Готово",f"✓ Объединено!\n\nСохранено:\n{op}"); self._cleanup()
        else:
            os.path.exists(tmp) and os.remove(tmp); raise Exception("Альтернативный метод не сработал")
        for t in tsf:
            try: os.remove(t)
            except: pass
        try: os.remove(lf)
        except: pass

    def _get_info(self,fp):
        try:
            r=subprocess.run([FFMPEG_PATH,'-i',fp],capture_output=True,text=True,encoding='utf-8',errors='replace')
            s=r.stderr; info={}
            m=re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)',s)
            if m: info['dur']=int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))
            m=re.search(r'Video:\s*(\w+).*?(\d{3,5})x(\d{3,5})',s)
            if m: info['codec']=m.group(1); info['w']=int(m.group(2)); info['h']=int(m.group(3))
            m=re.search(r'(\d+(?:\.\d+)?)\s*fps',s)
            if m: info['fps']=float(m.group(1))
            m=re.search(r'bitrate:\s*(\d+)\s*kb/s',s)
            if m: info['br']=int(m.group(1))
            return info or None
        except: return None

    def _get_duration(self,fp):
        try:
            r=subprocess.run([FFMPEG_PATH,'-i',fp],capture_output=True,text=True,encoding='utf-8',errors='replace')
            m=re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)',r.stderr)
            if m: return int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))
        except: pass
        return 0.0

    def _est_size(self,info,crf,res):
        dur=info.get('dur',0); w=info.get('w',1920); h=info.get('h',1080)
        fps=info.get('fps',25); obr=info.get('br',4000)
        rm={'1080p':(1920,1080),'720p':(1280,720),'480p':(854,480),'360p':(640,360),'original':(w,h)}
        tw,th=rm.get(res,(w,h)); tw=min(tw,w); th=min(th,h)
        return int((min(0.07*tw*th*fps/1000*2**((23-crf)/6),obr*0.95)+128)*1000/8*dur)

    def _analyze_compress(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка","FFMPEG не найден!"); return
        files=self._pick_files("video")
        if not files: return
        crf=int(self.v_crf.get()); res=self.v_res.get(); results=[]
        for fp in files:
            inf=self._get_info(fp)
            if inf:
                orig=os.path.getsize(fp); est=self._est_size(inf,crf,res)
                results.append({'file':Path(fp).name,'path':fp,'orig':orig,'est':est,
                                'w':inf.get('w',0),'h':inf.get('h',0),'dur':inf.get('dur',0),'codec':inf.get('codec','?')})
            else: results.append({'file':Path(fp).name,'error':True})
        self._show_vid_analysis(results,crf,res)

    def _show_vid_analysis(self,results,crf,res):
        def fsz(b): return f"{b/1024/1024:.1f} MB" if b>=1024*1024 else f"{b/1024:.0f} KB"
        win=tk.Toplevel(self.root); win.title("Анализ сжатия видео"); win.geometry("860x480"); win.configure(bg=D["bg0"])
        hf=tk.Frame(win,bg=D["bg2"],height=46); hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf,bg=D["rose"],width=2).pack(side="left",fill="y")
        tk.Label(hf,text="  АНАЛИЗ СЖАТИЯ ВИДЕО",font=("Courier New",12,"bold"),bg=D["bg2"],fg=D["rose"]).pack(side="left",pady=10)
        tk.Label(hf,text=f"  CRF {crf}  ·  {res}",font=("Segoe UI",9),bg=D["bg2"],fg=D["t1"]).pack(side="left")
        tf=tk.Frame(win,bg=D["bg0"]); tf.pack(fill="both",expand=True,padx=10,pady=8)
        cols=("Файл","Оригинал","→ После","Экономия","Разрешение","Длит.","Кодек")
        tree=ttk.Treeview(tf,columns=cols,show="headings")
        for col,w in zip(cols,[240,100,100,130,110,70,70]):
            tree.heading(col,text=col); tree.column(col,width=w,anchor="center")
        tree.tag_configure("good",foreground=D["teal"]); tree.tag_configure("mid",foreground=D["amber"])
        tree.tag_configure("low",foreground=D["rose"]); tree.tag_configure("err",foreground=D["t2"])
        for r in results:
            if r.get("error"): tree.insert("","end",values=(r['file'],"—","—","—","—","—","—"),tags=("err",)); continue
            s=(1-r['est']/r['orig'])*100 if r['orig'] else 0
            dur=r['dur']; dm=f"{int(dur//60)}:{int(dur%60):02d}"
            tag="good" if s>30 else ("mid" if s>5 else "low")
            tree.insert("","end",values=(r['file'],fsz(r['orig']),f"≈ {fsz(r['est'])}",
                f"−{s:.0f}%  ({fsz(r['orig']-r['est'])})",f"{r['w']}×{r['h']}",dm,r['codec']),tags=(tag,))
        sb2=ttk.Scrollbar(tf,orient="vertical",command=tree.yview,style="Dark.Vertical.TScrollbar")
        tree.configure(yscrollcommand=sb2.set); tree.pack(side="left",fill="both",expand=True); sb2.pack(side="right",fill="y")
        ft=tk.Frame(win,bg=D["bg2"],height=44); ft.pack(fill="x",side="bottom"); ft.pack_propagate(False)
        tk.Label(ft,text="  * Оценка приблизительная",font=("Segoe UI",8,"italic"),bg=D["bg2"],fg=D["t2"]).pack(side="left",padx=8)
        _pill(ft,"  Сжать видео",D["rose"],lambda:(win.destroy(),self._start_compress()),FFMPEG_AVAILABLE).pack(side="right",padx=10,pady=6,ipadx=4)
        tk.Button(ft,text="Закрыть",font=("Segoe UI",9),bg=D["bg3"],fg=D["t1"],relief="flat",command=win.destroy).pack(side="right",padx=6,pady=6,ipadx=8)

    def _start_compress(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка","FFMPEG не найден!"); return
        self.root.withdraw(); threading.Thread(target=self._run_compress,daemon=True).start()

    def _run_compress(self):
        try:
            files=self._pick_files("video")
            if not files: return self._warn("Файлы не выбраны")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            crf=str(int(self.v_crf.get())); preset=self.v_preset.get(); res=self.v_res.get()
            ok=fail=0; self._show_progress(len(files),D["rose"])
            rs={'1080p':'scale=1920:1080:force_original_aspect_ratio=decrease',
                '720p':'scale=1280:720:force_original_aspect_ratio=decrease',
                '480p':'scale=854:480:force_original_aspect_ratio=decrease',
                '360p':'scale=640:360:force_original_aspect_ratio=decrease'}
            for i,fp in enumerate(files,1):
                if self.cancel_flag: break
                proc=None; op=None
                try:
                    name=Path(fp).stem; op=os.path.join(out,f"{name}_compressed.mp4"); n=1
                    while os.path.exists(op): op=os.path.join(out,f"{name}_compressed_{n}.mp4"); n+=1
                    dur=self._get_duration(fp)
                    cmd=[FFMPEG_PATH,'-i',fp,'-c:v','libx264','-crf',crf,'-preset',preset,
                         '-c:a','aac','-b:a','128k','-movflags','+faststart','-progress','pipe:2','-nostats']
                    if res in rs: cmd+=['-vf',rs[res]]
                    cmd+=['-y',op]
                    self._upd(i,len(files),f"Сжатие: {name}")
                    if self.progress_popup: self.progress_popup.reset_ffmpeg()
                    proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
                    out_time=0.0; speed_val=""
                    while True:
                        line=proc.stderr.readline()
                        if not line and proc.poll() is not None: break
                        if self.cancel_flag:
                            proc.terminate()
                            try: proc.wait(timeout=5)
                            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                            for _ in range(10):
                                try:
                                    if op and os.path.exists(op): os.remove(op)
                                    break
                                except PermissionError: time.sleep(0.5)
                            return
                        line=line.strip()
                        if line.startswith("out_time_ms="):
                            try: out_time=int(line.split("=")[1])/1_000_000
                            except: pass
                        elif line.startswith("speed="):
                            try: speed_val=f"{float(line.split('=')[1].strip().replace('x','')):.2f}"
                            except: speed_val=""
                        elif line.startswith("progress=") and dur>0 and self.progress_popup:
                            pct=min(out_time/dur*100,99); eta=0.0
                            if speed_val:
                                try:
                                    spd=float(speed_val)
                                    if spd>0: eta=(dur-out_time)/spd
                                except: pass
                            self.progress_popup.update_ffmpeg(pct,out_time,dur,speed_val,eta)
                    ret=proc.wait()
                    if ret==0 and op and os.path.exists(op) and os.path.getsize(op)>100:
                        orig=os.path.getsize(fp); comp=os.path.getsize(op); sv=(1-comp/orig)*100
                        self.logger.add(f"Сжато: {Path(fp).name} | {orig/1024/1024:.1f} MB → {comp/1024/1024:.1f} MB (−{sv:.0f}%)","SUCCESS")
                        ok+=1; self._upd(i,len(files),f"✓ {name}  −{sv:.0f}%")
                        if self.progress_popup: self.progress_popup.update_ffmpeg(100,dur,dur,speed_val,0)
                    else: raise Exception(f"FFMPEG код {ret}")
                except Exception as e:
                    fail+=1; self.logger.add(f"Ошибка {Path(fp).name}: {e}","ERROR"); self._upd(i,len(files),f"✗ {Path(fp).name}")
                    if proc and proc.poll() is None:
                        try: proc.terminate(); proc.wait(timeout=5)
                        except:
                            try: proc.kill()
                            except: pass
                    if op:
                        for _ in range(6):
                            try:
                                if os.path.exists(op): os.remove(op)
                                break
                            except PermissionError: time.sleep(0.5)
            if not self.cancel_flag: self._done("Сжатие видео",ok,fail,out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _check_video(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка","FFMPEG не найден!"); return
        files=self._pick_files("video")
        if not files: return
        results=[]
        for fp in files:
            try:
                sz=os.path.getsize(fp)
                r=subprocess.run([FFMPEG_PATH,'-i',fp],capture_output=True,text=True,encoding='utf-8',errors='replace')
                m=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',r.stderr)
                if m:
                    dur=int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))
                    results.append({'file':Path(fp).name,'size':f"{sz/1024/1024:.2f} MB",'dur':f"{dur:.1f} сек",'ok':True,'err':'—'})
                else:
                    results.append({'file':Path(fp).name,'size':f"{sz/1024/1024:.2f} MB",'dur':'?','ok':False,'err':'Длительность не определена'})
            except Exception as e:
                results.append({'file':Path(fp).name,'size':'—','dur':'—','ok':False,'err':str(e)})
        self._show_check(results)

    def _show_check(self,results):
        win=tk.Toplevel(self.root); win.title("Проверка видео"); win.geometry("760x420"); win.configure(bg=D["bg0"])
        hf=tk.Frame(win,bg=D["bg2"],height=44); hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf,bg=D["green"],width=2).pack(side="left",fill="y")
        tk.Label(hf,text="  ПРОВЕРКА ЦЕЛОСТНОСТИ",font=("Courier New",11,"bold"),bg=D["bg2"],fg=D["green"]).pack(side="left",pady=10)
        tf=tk.Frame(win,bg=D["bg0"]); tf.pack(fill="both",expand=True,padx=10,pady=8)
        cols=("Файл","Размер","Длительность","Статус","Ошибка")
        tree=ttk.Treeview(tf,columns=cols,show="headings")
        for col,w in zip(cols,[230,90,110,100,190]): tree.heading(col,text=col); tree.column(col,width=w,anchor="center")
        tree.tag_configure("ok",foreground=D["teal"]); tree.tag_configure("bad",foreground=D["rose"])
        for r in results:
            tag="ok" if r['ok'] else "bad"
            tree.insert("","end",values=(r['file'],r['size'],r['dur'],"✓ OK" if r['ok'] else "✕ Повреждено",r['err']),tags=(tag,))
        sb2=ttk.Scrollbar(tf,orient="vertical",command=tree.yview,style="Dark.Vertical.TScrollbar")
        tree.configure(yscrollcommand=sb2.set); tree.pack(side="left",fill="both",expand=True); sb2.pack(side="right",fill="y")
        ft=tk.Frame(win,bg=D["bg2"],height=40); ft.pack(fill="x",side="bottom"); ft.pack_propagate(False)
        tk.Button(ft,text="Закрыть",font=("Segoe UI",9),bg=D["bg3"],fg=D["t1"],relief="flat",command=win.destroy).pack(side="right",padx=10,pady=7,ipadx=10)

    def _repair_video(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка","FFMPEG не найден!"); return
        self.root.withdraw(); threading.Thread(target=self._run_repair,daemon=True).start()

    def _run_repair(self):
        try:
            files=self._pick_files("video")
            if not files: return self._warn("Файлы не выбраны")
            out=self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            ok=fail=0; self._show_progress(len(files),D["green"])
            for i,fp in enumerate(files,1):
                if self.cancel_flag: break
                try:
                    name=Path(fp).stem; op=os.path.join(out,f"{name}_repaired.mp4"); n=1
                    while os.path.exists(op): op=os.path.join(out,f"{name}_repaired_{n}.mp4"); n+=1
                    r=subprocess.run([FFMPEG_PATH,'-i',fp,'-c:v','libx264','-c:a','aac',
                        '-preset','fast','-crf','23','-movflags','+faststart','-y',op],capture_output=True)
                    if r.returncode==0 and os.path.exists(op) and os.path.getsize(op)>0: ok+=1; self._upd(i,len(files),f"✓ {name}")
                    else: raise Exception("FFMPEG завершился с ошибкой")
                except Exception as e: fail+=1; self.logger.add(f"Ошибка {Path(fp).name}: {e}","ERROR")
            if not self.cancel_flag: self._done("Восстановление",ok,fail,out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    def _show_about(self):
        win=tk.Toplevel(self.root); win.title("О программе"); win.geometry("480x360"); win.configure(bg=D["bg0"])
        hf=tk.Frame(win,bg=D["bg2"],height=46); hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf,bg=D["teal"],width=2).pack(side="left",fill="y")
        tk.Label(hf,text="  О ПРОГРАММЕ",font=("Courier New",12,"bold"),bg=D["bg2"],fg=D["teal"]).pack(side="left",pady=10)

        body=tk.Frame(win,bg=D["bg0"],padx=24,pady=20); body.pack(fill="both",expand=True)

        tk.Label(body,text="Video Maker Pro",font=("Courier New",18,"bold"),bg=D["bg0"],fg=D["amber"]).pack(anchor="w")
        tk.Label(body,text=f"Версия {VERSION}",font=("Segoe UI",10),bg=D["bg0"],fg=D["t1"]).pack(anchor="w",pady=(2,16))

        # Компоненты
        items=[
            ("PIL (Pillow)",    PIL_AVAILABLE,    "Конвертация и сжатие изображений"),
            ("MoviePy",         MOVIEPY_AVAILABLE,"Конвертация и создание видео"),
            ("FFMPEG",          FFMPEG_AVAILABLE, "Сжатие, склейка, восстановление видео"),
        ]
        for name, ok, desc in items:
            row=tk.Frame(body,bg=D["bg0"]); row.pack(fill="x",pady=3)
            col=D["teal"] if ok else D["rose"]
            status="✓" if ok else "✕"
            tk.Label(row,text=status,font=("Courier New",11,"bold"),bg=D["bg0"],fg=col,width=3).pack(side="left")
            tk.Label(row,text=name,font=("Segoe UI",9,"bold"),bg=D["bg0"],fg=D["t0"],width=16,anchor="w").pack(side="left")
            tk.Label(row,text=desc,font=("Segoe UI",9),bg=D["bg0"],fg=D["t2"]).pack(side="left")

        if not all([PIL_AVAILABLE, MOVIEPY_AVAILABLE, FFMPEG_AVAILABLE]):
            tk.Frame(body,bg=D["b1"],height=1).pack(fill="x",pady=(14,8))
            tk.Label(body,text="⚠  Некоторые компоненты не найдены.\nПопробуйте переустановить программу.",
                     font=("Segoe UI",9),bg=D["bg0"],fg=D["rose"],justify="left").pack(anchor="w")

        ft=tk.Frame(win,bg=D["bg2"],height=44); ft.pack(fill="x",side="bottom"); ft.pack_propagate(False)
        tk.Button(ft,text="Закрыть",font=("Segoe UI",9),bg=D["bg3"],fg=D["t1"],
                  relief="flat",command=win.destroy).pack(side="right",padx=10,pady=8,ipadx=16)

    def _install_vlc(self):
        import webbrowser; webbrowser.open("https://www.videolan.org/vlc/download-windows.html")

    def _clean_temp(self):
        try:
            cnt=0
            for f in os.listdir(self.temp_dir):
                fp=os.path.join(self.temp_dir,f)
                if os.path.isfile(fp): os.remove(fp); cnt+=1
            messagebox.showinfo("Очистка",f"Удалено файлов: {cnt}")
        except Exception as e: messagebox.showerror("Ошибка",str(e))

    # ── helpers ──────────────────────────────────────────────
    def _pick_files(self,kind):
        if kind=="photo": types=[("Изображения","*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif *.ico")]; title="Выберите фотографии"
        else: types=[("Видео","*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv *.m4v")]; title="Выберите видеофайлы"
        files=filedialog.askopenfilenames(title=title,filetypes=types)
        return files if files else None

    def _pick_dir(self):
        d=filedialog.askdirectory(title="Выберите папку для сохранения"); return d or None

    def _show_progress(self,total,accent=D["amber"]):
        self.cancel_flag=False
        self.progress_popup=ProgressPopup(self.root,total,accent)
        self.progress_popup.set_cancel(self._cancel)

    def _upd(self,cur,total,text):
        if self.progress_popup: self.progress_popup.update_state(cur,total,text)

    def _cancel(self):
        self.cancel_flag=True; self.logger.add("Отменено пользователем","WARNING")
        if self.progress_popup: self.progress_popup.destroy(); self.progress_popup=None
        self.root.deiconify()

    def _done(self,title,ok,fail,out):
        if self.progress_popup: self.progress_popup.destroy(); self.progress_popup=None
        msg=f"{'✓' if fail==0 else '⚠'}  {title}\n\nУспешно: {ok}\nОшибок:  {fail}\n\nПапка:\n{out}"
        self.logger.add(f"{title}: {ok} OK, {fail} ошибок","SUCCESS" if fail==0 else "WARNING")
        (messagebox.showinfo if fail==0 else messagebox.showwarning)("Готово",msg)
        self._cleanup()

    def _warn(self,msg):
        self.logger.add(msg,"WARNING"); self.root.deiconify(); messagebox.showwarning("Внимание",msg)

    def _err(self,msg):
        self.logger.add(msg,"ERROR"); self.root.deiconify(); messagebox.showerror("Ошибка",msg)

    def _cleanup(self):
        try:
            if self.progress_popup: self.progress_popup.destroy(); self.progress_popup=None
            self.root.deiconify()
        except: pass

    # ── updates ──────────────────────────────────────────────
    def _show_update_dot(self):
        """Показывает красную точку на кнопке обновлений."""
        try:
            self._upd_dot.pack(side="left", padx=(2, 0))
            self._upd_btn.configure(fg=D["rose"])
        except: pass

    def _check_updates(self, silent=True):
        """Проверяет обновления в фоне. silent=True — молчать, если их нет
        или если проверка не удалась (используется при автостарте)."""
        if "YOUR_GITHUB_USERNAME" in UPDATE_API:
            if not silent:
                messagebox.showinfo("Обновления",
                    "Автообновление ещё не настроено.\n\n"
                    "Укажите GITHUB_OWNER и GITHUB_REPO в начале файла программы.")
            return
        def worker():
            try:
                info = fetch_latest_release()
            except Exception as e:
                self.logger.add(f"Проверка обновлений не удалась: {e}", "WARNING")
                if not silent:
                    if "CERTIFICATE_VERIFY" in str(e).upper():
                        msg = ("Не удалось проверить обновления: сеть подменяет\n"
                               "сертификат github.com.\n\n"
                               "Так делают корпоративные прокси и антивирусы.\n"
                               "Обратитесь к системному администратору или\n"
                               "скачайте обновление вручную со страницы релизов.")
                    else:
                        msg = "Не удалось проверить обновления.\nПроверьте интернет-соединение."
                    self.root.after(0, lambda: messagebox.showwarning("Обновления", msg))
                return
            if info and info.get("version") and _is_newer(info["version"], VERSION):
                self.logger.add(f"Доступна новая версия: {info['version']}", "INFO")
                # Показываем красную точку на кнопке обновлений
                self.root.after(0, self._show_update_dot)
                self.root.after(0, lambda: self._prompt_update(info))
            else:
                self.logger.add("Установлена последняя версия", "INFO")
                if not silent:
                    self.root.after(0, lambda: messagebox.showinfo("Обновления",
                        f"У вас установлена последняя версия (v{VERSION})."))
        threading.Thread(target=worker, daemon=True).start()

    def _prompt_update(self, info):
        ver = info["version"].lstrip("vV")
        notes = info.get("notes") or ""
        if len(notes) > 400: notes = notes[:400] + "…"
        msg = f"Доступна новая версия: v{ver}\nУ вас установлена: v{VERSION}\n"
        if notes: msg += f"\nЧто нового:\n{notes}\n"
        if not info.get("url"):
            messagebox.showinfo("Обновление", msg +
                "\n\nФайл установщика в релизе не найден — обновите вручную.")
            return
        if messagebox.askyesno("Доступно обновление",
                               msg + "\nСкачать и установить обновление сейчас?"):
            self._download_and_install(info)

    def _download_and_install(self, info):
        # маленькое окно прогресса загрузки
        pop = tk.Toplevel(self.root); pop.title("Загрузка обновления")
        pop.geometry("440x140"); pop.configure(bg=D["bg0"]); pop.resizable(False,False)
        pop.transient(self.root); pop.grab_set()
        tk.Frame(pop,bg=D["violet"],height=2).pack(fill="x")
        body=tk.Frame(pop,bg=D["bg0"],padx=24,pady=18); body.pack(fill="both",expand=True)
        lbl=tk.Label(body,text="Скачивание установщика…",font=("Segoe UI",10,"bold"),
                     bg=D["bg0"],fg=D["t0"]); lbl.pack(anchor="w",pady=(0,10))
        bar=ttk.Progressbar(body,length=390,maximum=100,
                            style="DarkViolet.Horizontal.TProgressbar"); bar.pack()
        pct=tk.Label(body,text="0%",font=("Courier New",8),bg=D["bg0"],fg=D["t2"])
        pct.pack(anchor="e",pady=(4,0))

        def worker():
            import urllib.request
            dst = os.path.join(tempfile.gettempdir(), UPDATE_ASSET)
            try:
                req = urllib.request.Request(info["url"],
                        headers={"User-Agent":"VideoMakerPro-Updater"})
                with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as r, open(dst,"wb") as f:
                    total = int(r.headers.get("Content-Length") or 0); got = 0
                    while True:
                        chunk = r.read(262144)
                        if not chunk: break
                        f.write(chunk); got += len(chunk)
                        if total:
                            p = got*100//total
                            self.root.after(0, lambda p=p: (bar.configure(value=p),
                                            pct.configure(text=f"{p}%")))
            except Exception as e:
                self.root.after(0, lambda: (pop.destroy(), messagebox.showerror(
                    "Обновление", f"Не удалось скачать обновление:\n{e}")))
                return
            self.root.after(0, lambda: (pop.destroy(), self._launch_installer(dst)))
        threading.Thread(target=worker, daemon=True).start()

    def _launch_installer(self, path):
        try:
            exe = sys.executable if getattr(sys, 'frozen', False) else ""
            bat = os.path.join(tempfile.gettempdir(), "vmp_update.bat")
            with open(bat, "w", encoding="cp866", errors="replace") as f:
                f.write("@echo off\n")
                # Очищаем переменные PyInstaller — иначе новая программа
                # унаследует путь к временной папке старой и не запустится
                f.write("set _MEIPASS2=\n")
                f.write("set _PYI_ARCHIVE_FILE=\n")
                f.write("set _PYI_APPLICATION_HOME_DIR=\n")
                f.write("set _PYI_PARENT_PROCESS_LEVEL=\n")
                f.write("set _PYI_SPLASH_IPC=\n")
                f.write("timeout /t 2 /nobreak >nul\n")
                # Принудительно убиваем ВСЕ процессы программы (включая родительский PyInstaller)
                f.write("taskkill /F /IM VideoMakerPro.exe >nul 2>&1\n")
                f.write("timeout /t 2 /nobreak >nul\n")
                # Тихая установка, ждём завершения
                # Тихая установка — установщик сам запустит программу после завершения
                f.write(f'"{path}" /SILENT /NORESTART /CLOSEAPPLICATIONS /FORCECLOSEAPPLICATIONS\n')
                f.write('del "%~f0"\n')
            env = {k: v for k, v in os.environ.items()
                   if k != "_MEIPASS2" and not k.startswith("_PYI_")}
            subprocess.Popen(
                ["cmd", "/c", "start", "", "/min", bat],
                close_fds=True, env=env,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            messagebox.showerror("Обновление", f"Не удалось запустить установщик:\n{e}")
            return
        try: self.root.destroy()
        except: pass
        os._exit(0)

    # ── page: pdf ────────────────────────────────────────────
    def _build_pdf_page(self):
        PDF_COL = "#e8622a"
        p = tk.Frame(self._cf, bg=D["bg1"])
        self.pages["pdf"] = p
        _page_header(p, "Работа с PDF",
                     "Объединение, разделение, редактирование страниц", PDF_COL)

        body = tk.Frame(p, bg=D["bg1"], pady=10)
        body.pack(fill="both", expand=True)

        # ── 1. Объединить ──
        s1 = _section(body, "Объединить PDF файлы", PDF_COL)
        tk.Label(s1, text="Выберите несколько PDF — они объединятся в указанном порядке.",
                 font=("Segoe UI", 9), bg=s1.cget("bg"), fg=D["t1"]).pack(anchor="w", pady=(0, 6))
        _pill(s1, "  Объединить PDF", PDF_COL,
              self._start_pdf_merge, True).pack(anchor="w", ipady=3)

        _divider(body)

        # ── 2. Разделить ──
        s2 = _section(body, "Разделить PDF", PDF_COL)
        tk.Label(s2, text="Каждая страница сохранится как отдельный PDF файл.",
                 font=("Segoe UI", 9), bg=s2.cget("bg"), fg=D["t1"]).pack(anchor="w", pady=(0, 6))
        _pill(s2, "  Разделить PDF", PDF_COL,
              self._start_pdf_split, True).pack(anchor="w", ipady=3)

        _divider(body)

        # ── 3. Удалить страницы ──
        s3 = _section(body, "Удалить страницы", PDF_COL)
        _field(s3, "Номера страниц", lambda r: (
            tk.Entry(r, textvariable=self.v_pdf_pages_del, width=28,
                     bg=D["bg4"], fg=D["t0"], insertbackground=D["amber"],
                     relief="flat", font=("Segoe UI", 9)).pack(side="left", padx=(0, 8)),
            _hint(r, "Необязательно — страницы можно выбрать в окне"),
        ))
        _pill(s3, "  Удалить страницы", PDF_COL,
              self._start_pdf_delete, True).pack(anchor="w", ipady=3)

        _divider(body)

        # ── 4. Извлечь страницы ──
        s4 = _section(body, "Извлечь страницы", PDF_COL)
        _field(s4, "Страницы", lambda r: (
            tk.Entry(r, textvariable=self.v_pdf_pages_ext, width=28,
                     bg=D["bg4"], fg=D["t0"], insertbackground=D["amber"],
                     relief="flat", font=("Segoe UI", 9)).pack(side="left", padx=(0, 8)),
            _hint(r, "Необязательно — страницы можно выбрать в окне"),
        ))
        _pill(s4, "  Извлечь в новый PDF", PDF_COL,
              self._start_pdf_extract, True).pack(anchor="w", ipady=3)

        _divider(body)

        # ── 5. Повернуть ──
        s5 = _section(body, "Повернуть страницы", PDF_COL)
        tk.Label(s5, text="Откроется окно с миниатюрами: клик по странице — поворот на 90° по часовой, "
                          "правый клик — против. Есть кнопки «Все +90°».",
                 font=("Segoe UI", 9), bg=s5.cget("bg"), fg=D["t1"], wraplength=640,
                 justify="left").pack(anchor="w", pady=(0, 6))
        _pill(s5, "  Повернуть", PDF_COL,
              self._start_pdf_rotate, True).pack(anchor="w", ipady=3)

        _divider(body)

        # ── 6. Сжать ──
        s6 = _section(body, "Сжать PDF", PDF_COL)
        tk.Label(s6, text="Уменьшает размер файла — убирает лишние данные и пережимает изображения.",
                 font=("Segoe UI", 9), bg=s6.cget("bg"), fg=D["t1"]).pack(anchor="w", pady=(0, 6))
        _field(s6, "Качество картинок", lambda r: (
            _combo(r, self.v_pdf_cmp_level,
                   [lv[0] for lv in PDF_COMPRESS_LEVELS], 24).pack(side="left"),
            _hint(r, "Меньше dpi — меньше файл"),
        ))
        _field(s6, "Уложиться в (МБ)", lambda r: (
            tk.Entry(r, textvariable=self.v_pdf_cmp_target, width=10,
                     bg=D["bg4"], fg=D["t0"], insertbackground=D["amber"],
                     relief="flat", font=("Segoe UI", 9)).pack(side="left", padx=(0, 8)),
            _hint(r, "Пусто — без ограничения. Иначе качество снижается, пока не влезет"),
        ))
        _pill(s6, "  Сжать PDF", PDF_COL,
              self._start_pdf_compress, True).pack(anchor="w", ipady=3)

        _divider(body)

        # ── 7. Пронумеровать ──
        s7 = _section(body, "Пронумеровать страницы", PDF_COL)
        _field(s7, "Позиция номера", lambda r: (
            _combo(r, self.v_pdf_num_pos,
                   ["по центру снизу", "справа снизу", "слева снизу",
                    "по центру сверху", "справа сверху", "слева сверху"], 20).pack(side="left"),
        ))
        _field(s7, "Начать с номера", lambda r: (
            _spinbox(r, self.v_pdf_num_start, 0, 9999, 5).pack(side="left"),
        ))
        _field(s7, "Размер шрифта", lambda r: (
            _spinbox(r, self.v_pdf_num_size, 6, 48, 4).pack(side="left"),
        ))
        _pill(s7, "  Пронумеровать", PDF_COL,
              self._start_pdf_number, True).pack(anchor="w", pady=(8, 2), ipady=3)

        tk.Label(body,
                 text="ℹ  Для работы с PDF требуется библиотека pypdf  (pip install pypdf reportlab)",
                 font=("Segoe UI", 8, "italic"), bg=D["bg1"], fg=D["t2"]).pack(
            anchor="w", padx=20, pady=(8, 14))

    # ── PDF helpers ──────────────────────────────────────────

    @staticmethod
    def _parse_pages(s, total):
        """Parse page string like '1,3,5-8' → sorted list of 0-based indices."""
        pages = set()
        for part in s.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                a, _, b = part.partition("-")
                try:
                    for i in range(int(a), int(b) + 1):
                        if 1 <= i <= total:
                            pages.add(i - 1)
                except ValueError:
                    pass
            else:
                try:
                    i = int(part)
                    if 1 <= i <= total:
                        pages.add(i - 1)
                except ValueError:
                    pass
        return sorted(pages)

    @staticmethod
    def _check_pypdf():
        try:
            import pypdf
            return True
        except ImportError:
            messagebox.showerror(
                "Ошибка",
                "Библиотека pypdf не установлена.\n\n"
                "Откройте командную строку и выполните:\n"
                "pip install pypdf reportlab")
            return False

    # ── PDF: объединить ──────────────────────────────────────

    def _start_pdf_merge(self):
        if not self._check_pypdf(): return
        self.root.withdraw()
        threading.Thread(target=self._run_pdf_merge, daemon=True).start()

    def _run_pdf_merge(self):
        try:
            files = filedialog.askopenfilenames(
                title="Выберите PDF файлы (в нужном порядке)",
                filetypes=[("PDF", "*.pdf")])
            if not files: return self._warn("Файлы не выбраны")

            # Показываем диалог порядка
            ordered = self._pdf_order_dialog(list(files))
            if ordered is None: return self._cleanup()

            out_dir = self._pick_dir()
            if not out_dir: return self._warn("Папка не выбрана")

            import pypdf
            writer = pypdf.PdfWriter()
            self._show_progress(len(ordered), "#e8622a")
            for i, fp in enumerate(ordered, 1):
                if self.cancel_flag: break
                reader = pypdf.PdfReader(fp)
                for page in reader.pages:
                    writer.add_page(page)
                self._upd(i, len(ordered), f"✓ {Path(fp).name}")

            if not self.cancel_flag:
                op = os.path.join(out_dir, "merged.pdf")
                n = 1
                while os.path.exists(op):
                    op = os.path.join(out_dir, f"merged_{n}.pdf"); n += 1
                with open(op, "wb") as f:
                    writer.write(f)
                self.logger.add(f"PDF объединён: {op}", "SUCCESS")
                self._done("Объединение PDF", len(ordered), 0, out_dir)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    # ── PDF: разделить ───────────────────────────────────────

    def _start_pdf_split(self):
        if not self._check_pypdf(): return
        self.root.withdraw()
        threading.Thread(target=self._run_pdf_split, daemon=True).start()

    def _run_pdf_split(self):
        try:
            fp = filedialog.askopenfilename(
                title="Выберите PDF для разделения",
                filetypes=[("PDF", "*.pdf")])
            if not fp: return self._warn("Файл не выбран")

            out_dir = self._pick_dir()
            if not out_dir: return self._warn("Папка не выбрана")

            import pypdf
            reader = pypdf.PdfReader(fp)
            total = len(reader.pages)
            stem = Path(fp).stem
            ok = fail = 0
            self._show_progress(total, "#e8622a")

            for i in range(total):
                if self.cancel_flag: break
                try:
                    writer = pypdf.PdfWriter()
                    writer.add_page(reader.pages[i])
                    op = os.path.join(out_dir, f"{stem}_page_{i+1:03d}.pdf")
                    with open(op, "wb") as f:
                        writer.write(f)
                    ok += 1
                    self._upd(i + 1, total, f"Страница {i+1}")
                except Exception as e:
                    fail += 1
                    self.logger.add(f"Ошибка стр.{i+1}: {e}", "ERROR")

            if not self.cancel_flag:
                self._done("Разделение PDF", ok, fail, out_dir)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    # ── PDF: визуальный выбор страниц ────────────────────────

    def _pdf_page_picker(self, fp, title, accent, preselect=""):
        """Окно с миниатюрами страниц. Клик — выбрать/снять. Возвращает
        отсортированный список 0-based индексов или None (отмена)."""
        import pypdf
        try:
            total = len(pypdf.PdfReader(fp).pages)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть PDF:\n{e}"); return None
        if total == 0:
            messagebox.showwarning("Внимание", "В PDF нет страниц"); return None

        selected = set(self._parse_pages(preselect, total))
        result = [None]

        win = tk.Toplevel(self.root); win.title(title); win.geometry("900x640")
        win.configure(bg=D["bg0"]); win.grab_set(); win.minsize(640, 420)

        hf = tk.Frame(win, bg=D["bg2"], height=46); hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf, bg=accent, width=2).pack(side="left", fill="y")
        tk.Label(hf, text="  " + title.upper(), font=("Courier New", 11, "bold"),
                 bg=D["bg2"], fg=accent).pack(side="left", pady=10)
        cnt_var = tk.StringVar()
        tk.Label(hf, textvariable=cnt_var, font=("Segoe UI", 9),
                 bg=D["bg2"], fg=D["t1"]).pack(side="right", padx=14)

        # панель инструментов
        tb = tk.Frame(win, bg=D["bg1"]); tb.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(tb, text=f"{Path(fp).name}  ·  {total} стр.", font=("Segoe UI", 9),
                 bg=D["bg1"], fg=D["t1"]).pack(side="left")
        entry_var = tk.StringVar(value=preselect)
        ent = tk.Entry(tb, textvariable=entry_var, width=22, bg=D["bg4"], fg=D["t0"],
                       insertbackground=D["amber"], relief="flat", font=("Segoe UI", 9))
        ent.pack(side="right", padx=(6, 0))
        tk.Label(tb, text="Или введите: 1, 3, 5-8", font=("Segoe UI", 8, "italic"),
                 bg=D["bg1"], fg=D["t2"]).pack(side="right", padx=(12, 0))

        # сетка миниатюр
        area = tk.Frame(win, bg=D["bg1"]); area.pack(fill="both", expand=True, padx=12, pady=4)
        cv = tk.Canvas(area, bg=D["bg1"], highlightthickness=0)
        sb = ttk.Scrollbar(area, orient="vertical", command=cv.yview, style="Dark.Vertical.TScrollbar")
        grid = tk.Frame(cv, bg=D["bg1"])
        grid.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=grid, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        def _wheel(e): cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
        cv.bind("<MouseWheel>", _wheel); grid.bind("<MouseWheel>", _wheel)

        cells = {}   # idx -> (frame, widgets)
        photos = []  # держим ссылки на картинки
        COLS = 5; TW = 140

        def refresh(i):
            fr = cells[i][0]
            on = i in selected
            fr.configure(bg=accent if on else D["b1"])
            for w in cells[i][1]:
                w.configure(bg=D["bg3"] if on else D["bg2"])
            cnt_var.set(f"Выбрано: {len(selected)} из {total}")

        def toggle(i):
            if i in selected: selected.discard(i)
            else: selected.add(i)
            refresh(i)

        def set_all(mode):
            if mode == "all": selected.update(range(total))
            elif mode == "none": selected.clear()
            else: selected.symmetric_difference_update(range(total))
            for i in cells: refresh(i)

        def apply_entry(*_):
            selected.clear(); selected.update(self._parse_pages(entry_var.get(), total))
            for i in cells: refresh(i)
        ent.bind("<Return>", apply_entry)

        # попытка рендера миниатюр
        fitz = None
        try:
            import fitz as _fitz; fitz = _fitz
        except Exception:
            pass
        doc = None
        if fitz:
            try: doc = fitz.open(fp)
            except Exception: doc = None

        try:
            from PIL import ImageTk
        except Exception:
            ImageTk = None

        for i in range(total):
            fr = tk.Frame(grid, bg=D["b1"], padx=2, pady=2, cursor="hand2")
            fr.grid(row=i // COLS, column=i % COLS, padx=6, pady=6)
            inner = tk.Frame(fr, bg=D["bg2"]); inner.pack()
            img_lbl = None
            if doc is not None and ImageTk is not None:
                try:
                    page = doc[i]
                    zoom = TW / max(page.rect.width, 1)
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    ph = ImageTk.PhotoImage(im); photos.append(ph)
                    img_lbl = tk.Label(inner, image=ph, bg=D["bg2"], bd=0)
                except Exception:
                    img_lbl = None
            if img_lbl is None:
                img_lbl = tk.Label(inner, text=f"стр.\n{i+1}", width=14, height=8,
                                   font=("Courier New", 12, "bold"), bg=D["bg2"], fg=D["t1"])
            img_lbl.pack(padx=4, pady=(4, 0))
            num = tk.Label(inner, text=str(i + 1), font=("Segoe UI", 9, "bold"),
                           bg=D["bg2"], fg=D["t0"])
            num.pack(pady=(2, 4))
            cells[i] = (fr, [inner, img_lbl, num])
            for w in (fr, inner, img_lbl, num):
                w.bind("<Button-1>", lambda e, k=i: toggle(k))
                w.bind("<MouseWheel>", _wheel)
            refresh(i)
            if i % 10 == 0:
                try: win.update()
                except Exception: return None
        if doc is not None:
            try: doc.close()
            except Exception: pass

        # нижняя панель
        ft = tk.Frame(win, bg=D["bg2"], height=48); ft.pack(fill="x", side="bottom"); ft.pack_propagate(False)
        for txt, m in (("Все", "all"), ("Ничего", "none"), ("Инвертировать", "inv")):
            tk.Button(ft, text=txt, font=("Segoe UI", 9), bg=D["bg3"], fg=D["t1"], relief="flat",
                      command=lambda m=m: set_all(m), padx=10).pack(side="left", padx=(10, 0), pady=8)
        def ok():
            if not selected:
                messagebox.showwarning("Внимание", "Не выбрано ни одной страницы"); return
            result[0] = sorted(selected); win.destroy()
        _pill(ft, "  Продолжить", accent, ok).pack(side="right", padx=10, pady=6, ipadx=4)
        tk.Button(ft, text="Отмена", font=("Segoe UI", 9), bg=D["bg3"], fg=D["t1"], relief="flat",
                  command=win.destroy).pack(side="right", padx=6, pady=6, ipadx=8)

        cnt_var.set(f"Выбрано: {len(selected)} из {total}")
        win.wait_window()
        return result[0]

    # ── PDF: удалить страницы ────────────────────────────────

    def _start_pdf_delete(self):
        if not self._check_pypdf(): return
        fp = filedialog.askopenfilename(title="Выберите PDF", filetypes=[("PDF", "*.pdf")])
        if not fp: return
        pages = self._pdf_page_picker(fp, "Выберите страницы для удаления", "#e8622a",
                                      self.v_pdf_pages_del.get())
        if pages is None: return
        out_dir = self._pick_dir()
        if not out_dir: return
        self.root.withdraw()
        threading.Thread(target=self._run_pdf_delete, args=(fp, pages, out_dir), daemon=True).start()

    def _run_pdf_delete(self, fp, to_del, out_dir):
        try:
            import pypdf
            reader = pypdf.PdfReader(fp); total = len(reader.pages)
            to_del = set(to_del)
            if len(to_del) >= total:
                return self._warn("Нельзя удалить все страницы PDF")
            writer = pypdf.PdfWriter(); kept = 0
            for i, page in enumerate(reader.pages):
                if i not in to_del:
                    writer.add_page(page); kept += 1
            stem = Path(fp).stem
            op = os.path.join(out_dir, f"{stem}_edited.pdf"); n = 1
            while os.path.exists(op):
                op = os.path.join(out_dir, f"{stem}_edited_{n}.pdf"); n += 1
            with open(op, "wb") as f: writer.write(f)
            self.logger.add(f"Удалено {len(to_del)} стр. из {total}, осталось {kept}: {op}", "SUCCESS")
            self._done("Удаление страниц PDF", kept, 0, out_dir)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    # ── PDF: извлечь страницы ────────────────────────────────

    def _start_pdf_extract(self):
        if not self._check_pypdf(): return
        fp = filedialog.askopenfilename(title="Выберите PDF", filetypes=[("PDF", "*.pdf")])
        if not fp: return
        pages = self._pdf_page_picker(fp, "Выберите страницы для извлечения", "#e8622a",
                                      self.v_pdf_pages_ext.get())
        if pages is None: return
        out_dir = self._pick_dir()
        if not out_dir: return
        self.root.withdraw()
        threading.Thread(target=self._run_pdf_extract, args=(fp, pages, out_dir), daemon=True).start()

    def _run_pdf_extract(self, fp, to_ext, out_dir):
        try:
            import pypdf
            reader = pypdf.PdfReader(fp)
            writer = pypdf.PdfWriter()
            for i in to_ext: writer.add_page(reader.pages[i])
            stem = Path(fp).stem
            op = os.path.join(out_dir, f"{stem}_pages.pdf"); n = 1
            while os.path.exists(op):
                op = os.path.join(out_dir, f"{stem}_pages_{n}.pdf"); n += 1
            with open(op, "wb") as f: writer.write(f)
            self.logger.add(f"Извлечено {len(to_ext)} стр.: {op}", "SUCCESS")
            self._done("Извлечение страниц PDF", len(to_ext), 0, out_dir)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()


    # ── PDF: повернуть (с предпросмотром) ────────────────────

    def _pdf_rotate_picker(self, fp, accent):
        """Окно с миниатюрами. Клик по странице поворачивает её на 90°.
        Возвращает {idx: угол} только для повёрнутых страниц, или None."""
        import pypdf
        try:
            total = len(pypdf.PdfReader(fp).pages)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть PDF:\n{e}"); return None
        if total == 0:
            messagebox.showwarning("Внимание", "В PDF нет страниц"); return None

        angles = {i: 0 for i in range(total)}
        result = [None]

        win = tk.Toplevel(self.root); win.title("Поворот страниц"); win.geometry("900x660")
        win.configure(bg=D["bg0"]); win.grab_set(); win.minsize(640, 440)

        hf = tk.Frame(win, bg=D["bg2"], height=46); hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf, bg=accent, width=2).pack(side="left", fill="y")
        tk.Label(hf, text="  ПОВОРОТ СТРАНИЦ", font=("Courier New", 11, "bold"),
                 bg=D["bg2"], fg=accent).pack(side="left", pady=10)
        cnt_var = tk.StringVar()
        tk.Label(hf, textvariable=cnt_var, font=("Segoe UI", 9), bg=D["bg2"], fg=D["t1"]).pack(side="right", padx=14)

        tb = tk.Frame(win, bg=D["bg1"]); tb.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(tb, text=f"{Path(fp).name}  ·  {total} стр.   —   клик по странице = поворот на 90° по часовой",
                 font=("Segoe UI", 9), bg=D["bg1"], fg=D["t1"]).pack(side="left")

        area = tk.Frame(win, bg=D["bg1"]); area.pack(fill="both", expand=True, padx=12, pady=4)
        cv = tk.Canvas(area, bg=D["bg1"], highlightthickness=0)
        sb = ttk.Scrollbar(area, orient="vertical", command=cv.yview, style="Dark.Vertical.TScrollbar")
        grid = tk.Frame(cv, bg=D["bg1"])
        grid.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=grid, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        def _wheel(e): cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
        cv.bind("<MouseWheel>", _wheel); grid.bind("<MouseWheel>", _wheel)

        COLS = 5; TW = 140
        base_imgs = {}   # idx -> PIL image (0°) или None
        cells = {}       # idx -> dict(frame, img_lbl, badge)
        photos = {}      # idx -> PhotoImage (актуальная)

        fitz = None
        try:
            import fitz as _fitz; fitz = _fitz
        except Exception: pass
        doc = None
        if fitz:
            try: doc = fitz.open(fp)
            except Exception: doc = None
        try:
            from PIL import ImageTk
        except Exception:
            ImageTk = None

        def render(i):
            """Перерисовать миниатюру i с учётом угла."""
            c = cells[i]; a = angles[i]
            im = base_imgs.get(i)
            if im is not None and ImageTk is not None:
                # PIL rotate против часовой → для «по часовой» берём -a
                rot = im.rotate(-a, expand=True)
                ph = ImageTk.PhotoImage(rot); photos[i] = ph
                c["img_lbl"].configure(image=ph, text="")
            else:
                c["img_lbl"].configure(text=f"стр.\n{i+1}\n↻ {a}°")
            on = a != 0
            c["frame"].configure(bg=accent if on else D["b1"])
            c["badge"].configure(text=f"{a}°" if on else "", fg=accent)
            cnt_var.set(f"Повёрнуто: {sum(1 for v in angles.values() if v)} из {total}")

        def rotate(i, step=90):
            angles[i] = (angles[i] + step) % 360
            render(i)

        def rotate_all(step):
            for i in angles: angles[i] = (angles[i] + step) % 360
            for i in cells: render(i)

        def reset_all():
            for i in angles: angles[i] = 0
            for i in cells: render(i)

        for i in range(total):
            fr = tk.Frame(grid, bg=D["b1"], padx=2, pady=2, cursor="hand2")
            fr.grid(row=i // COLS, column=i % COLS, padx=6, pady=6)
            inner = tk.Frame(fr, bg=D["bg2"], width=TW + 16, height=TW + 50)
            inner.pack(); inner.pack_propagate(False)
            im = None
            if doc is not None:
                try:
                    page = doc[i]
                    zoom = TW / max(page.rect.width, page.rect.height, 1)
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                except Exception:
                    im = None
            base_imgs[i] = im
            img_lbl = tk.Label(inner, bg=D["bg2"], bd=0, font=("Courier New", 11, "bold"), fg=D["t1"])
            img_lbl.pack(expand=True)
            row = tk.Frame(inner, bg=D["bg2"]); row.pack(fill="x", pady=(0, 4))
            num = tk.Label(row, text=str(i + 1), font=("Segoe UI", 9, "bold"), bg=D["bg2"], fg=D["t0"])
            num.pack(side="left", padx=8)
            badge = tk.Label(row, text="", font=("Segoe UI", 8, "bold"), bg=D["bg2"], fg=accent)
            badge.pack(side="right", padx=8)
            cells[i] = dict(frame=fr, img_lbl=img_lbl, badge=badge)
            for w in (fr, inner, img_lbl, row, num, badge):
                w.bind("<Button-1>", lambda e, k=i: rotate(k))
                w.bind("<Button-3>", lambda e, k=i: rotate(k, -90))   # правая кнопка — против часовой
                w.bind("<MouseWheel>", _wheel)
            render(i)
            if i % 10 == 0:
                try: win.update()
                except Exception: return None
        if doc is not None:
            try: doc.close()
            except Exception: pass

        ft = tk.Frame(win, bg=D["bg2"], height=48); ft.pack(fill="x", side="bottom"); ft.pack_propagate(False)
        for txt, st in (("Все +90°", 90), ("Все +180°", 180), ("Все −90°", -90)):
            tk.Button(ft, text=txt, font=("Segoe UI", 9), bg=D["bg3"], fg=D["t1"], relief="flat",
                      command=lambda s=st: rotate_all(s), padx=10).pack(side="left", padx=(10, 0), pady=8)
        tk.Button(ft, text="Сбросить", font=("Segoe UI", 9), bg=D["bg3"], fg=D["rose"], relief="flat",
                  command=reset_all, padx=10).pack(side="left", padx=(10, 0), pady=8)
        def ok():
            res = {i: a for i, a in angles.items() if a}
            if not res:
                messagebox.showwarning("Внимание", "Ни одна страница не повёрнута"); return
            result[0] = res; win.destroy()
        _pill(ft, "  Сохранить", accent, ok).pack(side="right", padx=10, pady=6, ipadx=4)
        tk.Button(ft, text="Отмена", font=("Segoe UI", 9), bg=D["bg3"], fg=D["t1"], relief="flat",
                  command=win.destroy).pack(side="right", padx=6, pady=6, ipadx=8)

        win.wait_window()
        return result[0]

    def _start_pdf_rotate(self):
        if not self._check_pypdf(): return
        fp = filedialog.askopenfilename(title="Выберите PDF", filetypes=[("PDF", "*.pdf")])
        if not fp: return
        rot = self._pdf_rotate_picker(fp, "#e8622a")
        if rot is None: return
        out_dir = self._pick_dir()
        if not out_dir: return
        self.root.withdraw()
        threading.Thread(target=self._run_pdf_rotate, args=(fp, rot, out_dir), daemon=True).start()

    def _run_pdf_rotate(self, fp, rot, out_dir):
        try:
            import pypdf
            reader = pypdf.PdfReader(fp)
            writer = pypdf.PdfWriter()
            for i, page in enumerate(reader.pages):
                a = rot.get(i, 0)
                if a: page.rotate(a)
                writer.add_page(page)
            stem = Path(fp).stem
            op = os.path.join(out_dir, f"{stem}_rotated.pdf"); n = 1
            while os.path.exists(op):
                op = os.path.join(out_dir, f"{stem}_rotated_{n}.pdf"); n += 1
            with open(op, "wb") as f: writer.write(f)
            self.logger.add(f"Повёрнуто {len(rot)} стр.: {op}", "SUCCESS")
            self._done("Поворот страниц PDF", len(rot), 0, out_dir)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()


    # ── PDF: сжать ───────────────────────────────────────────

    def _start_pdf_compress(self):
        if not self._check_pypdf(): return
        self.root.withdraw()
        threading.Thread(target=self._run_pdf_compress, daemon=True).start()

    def _pdf_write_compressed(self, fp, op, dpi, quality):
        """Пишет сжатую копию fp в op. dpi=None — картинки не трогаем."""
        import fitz, io
        from PIL import Image
        doc = fitz.open(fp)
        try:
            if dpi:
                for page in doc:
                    for info in page.get_images(full=True):
                        xref = info[0]
                        try:
                            rects = page.get_image_rects(xref)
                            if not rects:
                                continue
                            r = rects[0]
                            # Целевой размер — сколько пикселей нужно, чтобы
                            # картинка на странице выглядела с заданным dpi.
                            tw = max(1, int(r.width  / 72.0 * dpi))
                            th = max(1, int(r.height / 72.0 * dpi))
                            base = doc.extract_image(xref)
                            img = Image.open(io.BytesIO(base["image"]))
                            if img.width <= tw and img.height <= th:
                                continue                # уже мельче цели
                            if img.mode not in ("RGB", "L"):
                                img = img.convert("RGB")
                            img = img.resize((tw, th), Image.LANCZOS)
                            buf = io.BytesIO()
                            img.save(buf, "JPEG", quality=quality, optimize=True)
                            page.replace_image(xref, stream=buf.getvalue())
                        except Exception:
                            continue                    # эту картинку оставляем как есть
            doc.save(op, garbage=4, deflate=True, deflate_images=True,
                     deflate_fonts=True, clean=True)
        finally:
            doc.close()

    def _run_pdf_compress(self):
        try:
            files = filedialog.askopenfilenames(
                title="Выберите PDF файлы",
                filetypes=[("PDF", "*.pdf")])
            if not files: return self._warn("Файлы не выбраны")

            out_dir = self._pick_dir()
            if not out_dir: return self._warn("Папка не выбрана")

            import pypdf
            limit = None
            raw = self.v_pdf_cmp_target.get().strip().replace(",", ".")
            if raw:
                try:
                    limit = int(float(raw) * 1048576)
                    if limit <= 0: limit = None
                except ValueError:
                    return self._warn("Целевой размер должен быть числом, например 100")

            ok = fail = 0
            self._show_progress(len(files), "#e8622a")

            for i, fp in enumerate(files, 1):
                if self.cancel_flag: break
                try:
                    stem = Path(fp).stem
                    op = os.path.join(out_dir, f"{stem}_compressed.pdf")
                    n = 1
                    while os.path.exists(op):
                        op = os.path.join(out_dir, f"{stem}_compressed_{n}.pdf"); n += 1

                    # Уровни перебираем от выбранного и ниже, пока файл не
                    # уложится в заданный размер. Без цели — ровно один проход.
                    start = next((k for k, lv in enumerate(PDF_COMPRESS_LEVELS)
                                  if lv[0] == self.v_pdf_cmp_level.get()), 0)
                    tries = PDF_COMPRESS_LEVELS[start:] if limit else [PDF_COMPRESS_LEVELS[start]]

                    by_fitz = False
                    for name, dpi, q in tries:
                        try:
                            self._pdf_write_compressed(fp, op, dpi, q)
                            by_fitz = True
                        except Exception:
                            if os.path.exists(op):
                                try: os.remove(op)
                                except Exception: pass
                            break
                        if not limit or os.path.getsize(op) <= limit:
                            break
                        self.logger.add(
                            f"{Path(fp).name}: «{name}» дало "
                            f"{os.path.getsize(op)/1048576:.1f} МБ — пробую сильнее", "INFO")

                    if not by_fitz:
                        reader = pypdf.PdfReader(fp)
                        writer = pypdf.PdfWriter()
                        # add_page возвращает страницу, уже принадлежащую writer.
                        # Сжимать нужно именно её: у страницы из reader метод
                        # падает с "Page must be part of a PdfWriter".
                        for page in reader.pages:
                            writer.add_page(page).compress_content_streams()
                        if reader.metadata:
                            writer.add_metadata(reader.metadata)
                        with open(op, "wb") as f:
                            writer.write(f)

                    orig = os.path.getsize(fp)
                    comp = os.path.getsize(op)
                    saved = (1 - comp / orig) * 100 if orig else 0
                    self.logger.add(
                        f"PDF сжат: {Path(fp).name} | "
                        f"{orig/1024:.0f} KB → {comp/1024:.0f} KB (−{saved:.0f}%)", "SUCCESS")
                    if limit and comp > limit:
                        self.logger.add(
                            f"{Path(fp).name}: уложиться в {limit/1048576:.0f} МБ не вышло "
                            f"даже на максимальном сжатии — получилось "
                            f"{comp/1048576:.1f} МБ", "WARNING")
                    ok += 1
                    self._upd(i, len(files), f"✓ {stem}  −{saved:.0f}%")
                except Exception as e:
                    fail += 1
                    self.logger.add(f"Ошибка {Path(fp).name}: {e}", "ERROR")

            if not self.cancel_flag:
                self._done("Сжатие PDF", ok, fail, out_dir)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    # ── PDF: пронумеровать ───────────────────────────────────

    def _start_pdf_number(self):
        if not self._check_pypdf(): return
        try:
            import reportlab  # noqa
        except ImportError:
            messagebox.showerror(
                "Ошибка",
                "Для нумерации страниц нужна библиотека reportlab.\n\n"
                "Выполните:\npip install reportlab")
            return
        self.root.withdraw()
        threading.Thread(target=self._run_pdf_number, daemon=True).start()

    def _run_pdf_number(self):
        try:
            files = filedialog.askopenfilenames(
                title="Выберите PDF файлы",
                filetypes=[("PDF", "*.pdf")])
            if not files: return self._warn("Файлы не выбраны")

            out_dir = self._pick_dir()
            if not out_dir: return self._warn("Папка не выбрана")

            import pypdf
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.units import mm
            import io

            pos_map = {
                "по центру снизу":  ("center", "bottom"),
                "справа снизу":     ("right",  "bottom"),
                "слева снизу":      ("left",   "bottom"),
                "по центру сверху": ("center", "top"),
                "справа сверху":    ("right",  "top"),
                "слева сверху":     ("left",   "top"),
            }
            halign, valign = pos_map.get(self.v_pdf_num_pos.get(), ("center", "bottom"))
            start = int(self.v_pdf_num_start.get())
            font_size = int(self.v_pdf_num_size.get())
            margin = 10 * mm

            ok = fail = 0
            self._show_progress(len(files), "#e8622a")

            for fi, fp in enumerate(files, 1):
                if self.cancel_flag: break
                try:
                    reader = pypdf.PdfReader(fp)
                    writer = pypdf.PdfWriter()
                    total = len(reader.pages)

                    for i, page in enumerate(reader.pages):
                        # Get page dimensions
                        w = float(page.mediabox.width)
                        h = float(page.mediabox.height)

                        # Create overlay with number
                        buf = io.BytesIO()
                        c = rl_canvas.Canvas(buf, pagesize=(w, h))
                        c.setFont("Helvetica", font_size)
                        c.setFillColorRGB(0.2, 0.2, 0.2)

                        num_text = str(start + i)

                        if valign == "bottom":
                            y = margin
                        else:
                            y = h - margin - font_size

                        if halign == "center":
                            c.drawCentredString(w / 2, y, num_text)
                        elif halign == "right":
                            c.drawRightString(w - margin, y, num_text)
                        else:
                            c.drawString(margin, y, num_text)

                        c.save()
                        buf.seek(0)

                        # Merge overlay onto page
                        overlay = pypdf.PdfReader(buf).pages[0]
                        page.merge_page(overlay)
                        writer.add_page(page)

                    stem = Path(fp).stem
                    op = os.path.join(out_dir, f"{stem}_numbered.pdf")
                    n = 1
                    while os.path.exists(op):
                        op = os.path.join(out_dir, f"{stem}_numbered_{n}.pdf"); n += 1

                    with open(op, "wb") as f:
                        writer.write(f)

                    self.logger.add(f"Пронумеровано {total} стр.: {op}", "SUCCESS")
                    ok += 1
                    self._upd(fi, len(files), f"✓ {stem} ({total} стр.)")
                except Exception as e:
                    fail += 1
                    self.logger.add(f"Ошибка {Path(fp).name}: {e}", "ERROR")

            if not self.cancel_flag:
                self._done("Нумерация страниц PDF", ok, fail, out_dir)
        except Exception as e:
            self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    # ── PDF: диалог порядка файлов ───────────────────────────

    def _pdf_order_dialog(self, files):
        """Show dialog to reorder PDF files before merging. Returns ordered list or None."""
        result = [None]
        win = tk.Toplevel(self.root)
        win.title("Порядок файлов для объединения")
        win.geometry("560x440")
        win.configure(bg=D["bg0"])
        win.grab_set()

        PDF_COL = "#e8622a"
        hf = tk.Frame(win, bg=D["bg2"], height=46)
        hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf, bg=PDF_COL, width=2).pack(side="left", fill="y")
        tk.Label(hf, text="  ПОРЯДОК ФАЙЛОВ ДЛЯ ОБЪЕДИНЕНИЯ",
                 font=("Courier New", 11, "bold"),
                 bg=D["bg2"], fg=PDF_COL).pack(side="left", pady=10)

        tk.Label(win, text="Перетащите файлы для изменения порядка:",
                 font=("Segoe UI", 9), bg=D["bg0"], fg=D["t1"]).pack(anchor="w", padx=16, pady=(10, 4))

        lf = tk.Frame(win, bg=D["bg0"])
        lf.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        listbox = tk.Listbox(lf, bg=D["bg2"], fg=D["t0"],
                             selectbackground=D["bg4"], selectforeground="#e8622a",
                             font=("Segoe UI", 9), relief="flat",
                             activestyle="none", bd=0)
        sb = ttk.Scrollbar(lf, orient="vertical", command=listbox.yview,
                           style="Dark.Vertical.TScrollbar")
        listbox.configure(yscrollcommand=sb.set)
        listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for f in files:
            listbox.insert(tk.END, f"  {Path(f).name}")

        # Drag-and-drop reorder via buttons
        btn_f = tk.Frame(win, bg=D["bg0"])
        btn_f.pack(fill="x", padx=16, pady=(0, 8))

        def move_up():
            sel = listbox.curselection()
            if not sel or sel[0] == 0: return
            i = sel[0]
            files[i-1], files[i] = files[i], files[i-1]
            txt = listbox.get(i); listbox.delete(i)
            listbox.insert(i-1, txt)
            listbox.selection_set(i-1)

        def move_down():
            sel = listbox.curselection()
            if not sel or sel[0] >= len(files)-1: return
            i = sel[0]
            files[i], files[i+1] = files[i+1], files[i]
            txt = listbox.get(i); listbox.delete(i)
            listbox.insert(i+1, txt)
            listbox.selection_set(i+1)

        tk.Button(btn_f, text="▲  Вверх", font=("Segoe UI", 9),
                  bg=D["bg3"], fg=D["t1"], relief="flat", command=move_up,
                  padx=12, pady=4).pack(side="left", padx=(0, 6))
        tk.Button(btn_f, text="▼  Вниз", font=("Segoe UI", 9),
                  bg=D["bg3"], fg=D["t1"], relief="flat", command=move_down,
                  padx=12, pady=4).pack(side="left")

        ft = tk.Frame(win, bg=D["bg2"], height=44)
        ft.pack(fill="x", side="bottom"); ft.pack_propagate(False)

        def ok_cb():
            result[0] = list(files)
            win.destroy()

        def cancel_cb():
            win.destroy()

        _pill(ft, "  Объединить", PDF_COL, ok_cb).pack(side="right", padx=10, pady=6, ipadx=4)
        tk.Button(ft, text="Отмена", font=("Segoe UI", 9),
                  bg=D["bg3"], fg=D["t1"], relief="flat",
                  command=cancel_cb).pack(side="right", padx=6, pady=6, ipadx=8)

        win.wait_window()
        return result[0]


    # ── page: audio ──────────────────────────────────────────
    AU_COL = "#d4a017"
    AU_EXTS = "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma *.opus *.aiff"

    def _build_audio_page(self):
        C = self.AU_COL
        p = tk.Frame(self._cf, bg=D["bg1"]); self.pages["audio"] = p
        _page_header(p, "Аудио", "Конвертация, обрезка, склейка, громкость", C)
        body = tk.Frame(p, bg=D["bg1"], pady=10); body.pack(fill="both", expand=True)

        # 1. Конвертация
        s1 = _section(body, "Конвертация аудио", C)
        _field(s1, "Выходной формат", lambda r: (
            _combo(r, self.v_au_fmt, ["mp3", "wav", "flac", "ogg", "m4a"], 8).pack(side="left"),
        ))
        _field(s1, "Битрейт (kbps)", lambda r: (
            _combo(r, self.v_au_bitrate, ["96", "128", "192", "256", "320"], 8).pack(side="left"),
            _hint(r, "Для mp3 / ogg / m4a. WAV и FLAC — без потерь"),
        ))
        _pill(s1, "  Конвертировать", C, self._start_au_convert, FFMPEG_AVAILABLE).pack(anchor="w", ipady=3)

        _divider(body)

        # 2. Обрезка
        s2 = _section(body, "Обрезка аудио", C)
        _field(s2, "От (мм:сс)", lambda r: (
            tk.Entry(r, textvariable=self.v_au_trim_from, width=10, bg=D["bg4"], fg=D["t0"],
                     insertbackground=D["amber"], relief="flat", font=("Segoe UI", 9)).pack(side="left"),
            _hint(r, "Например 0:00 или 1:23:45"),
        ))
        _field(s2, "До (мм:сс)", lambda r: (
            tk.Entry(r, textvariable=self.v_au_trim_to, width=10, bg=D["bg4"], fg=D["t0"],
                     insertbackground=D["amber"], relief="flat", font=("Segoe UI", 9)).pack(side="left"),
            _hint(r, "Пусто — до конца файла"),
        ))
        _pill(s2, "  Обрезать", C, self._start_au_trim, FFMPEG_AVAILABLE).pack(anchor="w", ipady=3)

        _divider(body)

        # 3. Склейка
        s3 = _section(body, "Склейка треков", C)
        tk.Label(s3, text="Выберите несколько файлов — порядок можно поменять в следующем окне.",
                 font=("Segoe UI", 9), bg=s3.cget("bg"), fg=D["t1"]).pack(anchor="w", pady=(0, 6))
        _field(s3, "Выходной формат", lambda r: (
            _combo(r, self.v_au_merge_fmt, ["mp3", "wav", "flac", "ogg", "m4a"], 8).pack(side="left"),
        ))
        _pill(s3, "  Склеить", C, self._start_au_merge, FFMPEG_AVAILABLE).pack(anchor="w", ipady=3)

        _divider(body)

        # 4. Нормализация
        s4 = _section(body, "Нормализация громкости", C)
        tk.Label(s4, text="Выравнивает громкость всех файлов к единому уровню (стандарт EBU R128).",
                 font=("Segoe UI", 9), bg=s4.cget("bg"), fg=D["t1"]).pack(anchor="w", pady=(0, 6))
        _field(s4, "Целевой уровень", lambda r: (
            _combo(r, self.v_au_norm_lvl, ["-14", "-16", "-18", "-23"], 8).pack(side="left"),
            _hint(r, "LUFS. −14 стриминг, −16 подкасты, −23 ТВ"),
        ))
        _pill(s4, "  Нормализовать", C, self._start_au_normalize, FFMPEG_AVAILABLE).pack(anchor="w", pady=(0, 6), ipady=3)

        if not FFMPEG_AVAILABLE:
            tk.Label(body, text="⚠  FFMPEG не найден", font=("Segoe UI", 8, "italic"),
                     bg=D["bg1"], fg=D["t2"]).pack(anchor="w", padx=20, pady=(0, 14))

    # ── audio helpers ────────────────────────────────────────
    def _au_pick(self, multi=True):
        types = [("Аудио", self.AU_EXTS), ("Все файлы", "*.*")]
        if multi:
            f = filedialog.askopenfilenames(title="Выберите аудио файлы", filetypes=types)
            return list(f) if f else None
        f = filedialog.askopenfilename(title="Выберите аудио файл", filetypes=types)
        return f or None

    @staticmethod
    def _au_codec_args(fmt, bitrate):
        return {
            "mp3":  ["-c:a", "libmp3lame", "-b:a", f"{bitrate}k"],
            "wav":  ["-c:a", "pcm_s16le"],
            "flac": ["-c:a", "flac"],
            "ogg":  ["-c:a", "libvorbis", "-b:a", f"{bitrate}k"],
            "m4a":  ["-c:a", "aac", "-b:a", f"{bitrate}k"],
        }.get(fmt, ["-c:a", "libmp3lame", "-b:a", f"{bitrate}k"])

    @staticmethod
    def _parse_time(s):
        """'1:23' / '1:23:45' / '83' -> seconds (float). Empty -> None."""
        s = (s or "").strip().replace(",", ".")
        if not s: return None
        parts = s.split(":")
        try:
            parts = [float(x) for x in parts]
        except ValueError:
            return None
        if len(parts) == 1: return parts[0]
        if len(parts) == 2: return parts[0]*60 + parts[1]
        if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
        return None

    def _au_unique(self, out_dir, stem, suffix, ext):
        op = os.path.join(out_dir, f"{stem}{suffix}.{ext}"); n = 1
        while os.path.exists(op):
            op = os.path.join(out_dir, f"{stem}{suffix}_{n}.{ext}"); n += 1
        return op

    def _au_run_ffmpeg(self, cmd):
        r = subprocess.run([FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error"] + cmd,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise Exception((r.stderr or "").strip().splitlines()[-1] if r.stderr else f"код {r.returncode}")

    def _order_dialog(self, files, title, accent):
        """Универсальный диалог порядка файлов. Возвращает список или None."""
        result = [None]
        win = tk.Toplevel(self.root); win.title(title); win.geometry("560x440")
        win.configure(bg=D["bg0"]); win.grab_set()
        hf = tk.Frame(win, bg=D["bg2"], height=46); hf.pack(fill="x"); hf.pack_propagate(False)
        tk.Frame(hf, bg=accent, width=2).pack(side="left", fill="y")
        tk.Label(hf, text="  " + title.upper(), font=("Courier New", 11, "bold"),
                 bg=D["bg2"], fg=accent).pack(side="left", pady=10)
        tk.Label(win, text="Выделите файл и двигайте кнопками:",
                 font=("Segoe UI", 9), bg=D["bg0"], fg=D["t1"]).pack(anchor="w", padx=16, pady=(10, 4))
        lf = tk.Frame(win, bg=D["bg0"]); lf.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        lb = tk.Listbox(lf, bg=D["bg2"], fg=D["t0"], selectbackground=D["bg4"],
                        selectforeground=accent, font=("Segoe UI", 9), relief="flat",
                        activestyle="none", bd=0)
        sb = ttk.Scrollbar(lf, orient="vertical", command=lb.yview, style="Dark.Vertical.TScrollbar")
        lb.configure(yscrollcommand=sb.set); lb.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        for f in files: lb.insert(tk.END, f"  {Path(f).name}")
        bf = tk.Frame(win, bg=D["bg0"]); bf.pack(fill="x", padx=16, pady=(0, 8))
        def mv(d):
            sel = lb.curselection()
            if not sel: return
            i = sel[0]; j = i + d
            if j < 0 or j >= len(files): return
            files[i], files[j] = files[j], files[i]
            t = lb.get(i); lb.delete(i); lb.insert(j, t); lb.selection_set(j)
        tk.Button(bf, text="▲  Вверх", font=("Segoe UI", 9), bg=D["bg3"], fg=D["t1"], relief="flat",
                  command=lambda: mv(-1), padx=12, pady=4).pack(side="left", padx=(0, 6))
        tk.Button(bf, text="▼  Вниз", font=("Segoe UI", 9), bg=D["bg3"], fg=D["t1"], relief="flat",
                  command=lambda: mv(1), padx=12, pady=4).pack(side="left")
        ft = tk.Frame(win, bg=D["bg2"], height=44); ft.pack(fill="x", side="bottom"); ft.pack_propagate(False)
        def ok(): result[0] = list(files); win.destroy()
        _pill(ft, "  Продолжить", accent, ok).pack(side="right", padx=10, pady=6, ipadx=4)
        tk.Button(ft, text="Отмена", font=("Segoe UI", 9), bg=D["bg3"], fg=D["t1"], relief="flat",
                  command=win.destroy).pack(side="right", padx=6, pady=6, ipadx=8)
        win.wait_window()
        return result[0]

    # ── audio: convert ───────────────────────────────────────
    def _start_au_convert(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка", "FFMPEG не найден!"); return
        self.root.withdraw(); threading.Thread(target=self._run_au_convert, daemon=True).start()

    def _run_au_convert(self):
        try:
            files = self._au_pick()
            if not files: return self._warn("Файлы не выбраны")
            out = self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            fmt = self.v_au_fmt.get(); br = self.v_au_bitrate.get()
            ok = fail = 0; self._show_progress(len(files), self.AU_COL)
            for i, fp in enumerate(files, 1):
                if self.cancel_flag: break
                try:
                    stem = Path(fp).stem; op = self._au_unique(out, stem, "", fmt)
                    self._upd(i, len(files), f"Конвертация: {stem}")
                    self._au_run_ffmpeg(["-i", fp, "-vn"] + self._au_codec_args(fmt, br) + [op])
                    ok += 1; self._upd(i, len(files), f"✓ {stem}.{fmt}")
                    self.logger.add(f"Аудио: {Path(fp).name} → {fmt}", "SUCCESS")
                except Exception as e:
                    fail += 1; self.logger.add(f"Ошибка {Path(fp).name}: {e}", "ERROR")
            if not self.cancel_flag: self._done("Конвертация аудио", ok, fail, out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    # ── audio: trim ──────────────────────────────────────────
    def _start_au_trim(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка", "FFMPEG не найден!"); return
        t0 = self._parse_time(self.v_au_trim_from.get()); t1 = self._parse_time(self.v_au_trim_to.get())
        if t0 is None:
            messagebox.showwarning("Внимание", "Неверный формат времени «От». Пример: 1:23"); return
        if self.v_au_trim_to.get().strip() and t1 is None:
            messagebox.showwarning("Внимание", "Неверный формат времени «До». Пример: 2:45"); return
        if t1 is not None and t1 <= t0:
            messagebox.showwarning("Внимание", "«До» должно быть больше «От»"); return
        self.root.withdraw(); threading.Thread(target=self._run_au_trim, daemon=True).start()

    def _run_au_trim(self):
        try:
            files = self._au_pick()
            if not files: return self._warn("Файлы не выбраны")
            out = self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            t0 = self._parse_time(self.v_au_trim_from.get()); t1 = self._parse_time(self.v_au_trim_to.get())
            ok = fail = 0; self._show_progress(len(files), self.AU_COL)
            for i, fp in enumerate(files, 1):
                if self.cancel_flag: break
                try:
                    stem = Path(fp).stem; ext = Path(fp).suffix.lstrip(".").lower() or "mp3"
                    if ext not in ("mp3", "wav", "flac", "ogg", "m4a"): ext = "mp3"
                    op = self._au_unique(out, stem, "_trim", ext)
                    self._upd(i, len(files), f"Обрезка: {stem}")
                    cmd = ["-i", fp, "-ss", str(t0)]
                    if t1 is not None: cmd += ["-to", str(t1)]
                    cmd += ["-vn"] + self._au_codec_args(ext, "192") + [op]
                    self._au_run_ffmpeg(cmd)
                    ok += 1; self._upd(i, len(files), f"✓ {stem}")
                    self.logger.add(f"Обрезано: {Path(fp).name}", "SUCCESS")
                except Exception as e:
                    fail += 1; self.logger.add(f"Ошибка {Path(fp).name}: {e}", "ERROR")
            if not self.cancel_flag: self._done("Обрезка аудио", ok, fail, out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    # ── audio: merge ─────────────────────────────────────────
    def _start_au_merge(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка", "FFMPEG не найден!"); return
        self.root.withdraw(); threading.Thread(target=self._run_au_merge, daemon=True).start()

    def _run_au_merge(self):
        try:
            files = self._au_pick()
            if not files or len(files) < 2: return self._warn("Выберите минимум 2 файла")
            ordered = self._order_dialog(files, "Порядок треков", self.AU_COL)
            if ordered is None: return self._cleanup()
            out = self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            fmt = self.v_au_merge_fmt.get()
            op = self._au_unique(out, "merged", "", fmt)
            self._show_progress(1, self.AU_COL); self._upd(0, 1, "Склейка…")
            inputs = []; labels = ""
            for i, f in enumerate(ordered):
                inputs += ["-i", f]; labels += f"[{i}:a]"
            fc = f"{labels}concat=n={len(ordered)}:v=0:a=1[a]"
            self._au_run_ffmpeg(inputs + ["-filter_complex", fc, "-map", "[a]"] +
                                self._au_codec_args(fmt, "192") + [op])
            self.logger.add(f"Склеено {len(ordered)} треков: {op}", "SUCCESS")
            if not self.cancel_flag: self._done("Склейка аудио", 1, 0, out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()

    # ── audio: normalize ─────────────────────────────────────
    def _start_au_normalize(self):
        if not FFMPEG_AVAILABLE: messagebox.showerror("Ошибка", "FFMPEG не найден!"); return
        self.root.withdraw(); threading.Thread(target=self._run_au_normalize, daemon=True).start()

    def _run_au_normalize(self):
        try:
            files = self._au_pick()
            if not files: return self._warn("Файлы не выбраны")
            out = self._pick_dir()
            if not out: return self._warn("Папка не выбрана")
            lvl = self.v_au_norm_lvl.get()
            ok = fail = 0; self._show_progress(len(files), self.AU_COL)
            for i, fp in enumerate(files, 1):
                if self.cancel_flag: break
                try:
                    stem = Path(fp).stem; ext = Path(fp).suffix.lstrip(".").lower() or "mp3"
                    if ext not in ("mp3", "wav", "flac", "ogg", "m4a"): ext = "mp3"
                    op = self._au_unique(out, stem, "_norm", ext)
                    self._upd(i, len(files), f"Нормализация: {stem}")
                    self._au_run_ffmpeg(["-i", fp, "-vn", "-af", f"loudnorm=I={lvl}:TP=-1.5:LRA=11"]
                                        + self._au_codec_args(ext, "192") + [op])
                    ok += 1; self._upd(i, len(files), f"✓ {stem}")
                    self.logger.add(f"Нормализовано: {Path(fp).name} → {lvl} LUFS", "SUCCESS")
                except Exception as e:
                    fail += 1; self.logger.add(f"Ошибка {Path(fp).name}: {e}", "ERROR")
            if not self.cancel_flag: self._done("Нормализация громкости", ok, fail, out)
        except Exception as e: self._err(str(e))
        finally:
            if not self.cancel_flag: self._cleanup()


# ══════════════════════════════════════════════════════════
def main():
    print(f"\n{'─'*55}\n  Video Maker Pro v{VERSION}\n{'─'*55}")
    print(f"  PIL:     {'OK' if PIL_AVAILABLE else 'NOT FOUND'}")
    print(f"  MoviePy: {'OK' if MOVIEPY_AVAILABLE else 'NOT FOUND'}")
    print(f"  FFMPEG:  {'OK' if FFMPEG_AVAILABLE else 'NOT FOUND'}")
    if FFMPEG_PATH: print(f"  Path:    {FFMPEG_PATH}")
    print(f"{'─'*55}\n")
    try: VideoMakerPro().root.mainloop()
    except Exception as e: print(f"\nFATAL: {e}"); input("Press Enter...")

if __name__ == "__main__":
    main()
