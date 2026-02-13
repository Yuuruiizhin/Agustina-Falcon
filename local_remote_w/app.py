import os
import json
import socket
import threading
import webbrowser
import time
import requests
import sys # Importado para gestionar rutas del EXE
from PIL import Image
import shutil
import pystray
from pystray import MenuItem as item
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import customtkinter as ctk

# --- FUNCIÓN CRÍTICA PARA PYINSTALLER ---
def get_resource_path(relative_path):
    """Obtiene la ruta absoluta de los recursos, compatible con PyInstaller y ejecución normal"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        # Siempre relativo a este archivo, no al cwd
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

app = FastAPI()
nombre_host = socket.gethostname()
direccion_ip_local = socket.gethostbyname(nombre_host)
PUERTO = 6284

# --- RUTAS CORREGIDAS ---
STATIC_DIR = get_resource_path("static")
DOCS_PATH = os.path.join(os.path.expanduser("~"), "Documents", "Yuuruii", "AgustinaFalcon")
GRAPHICS_PATH = os.path.join(DOCS_PATH, "graphics")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Montar estáticos solo si la ruta existe
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="No se encontró index.html en static")

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/bodegas")
async def listar_bodegas():
    config_path = os.path.join(DOCS_PATH, "bodegas_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                return list(json.load(f).keys())
        except: pass
    
    if os.path.exists(DOCS_PATH):
        archivos = [f for f in os.listdir(DOCS_PATH) if f.startswith("yrz_") and f.endswith(".json")]
        return [f.replace("yrz_", "").replace(".json", "").replace("_", " ").title() for f in archivos]
    return []

@app.get("/api/puntos/{nombre_bodega}")
async def obtener_puntos(nombre_bodega: str):
    archivo_json = f"yrz_{nombre_bodega.lower().replace(' ', '_')}.json"
    ruta = os.path.join(DOCS_PATH, archivo_json)
    if os.path.exists(ruta):
        with open(ruta, "r", encoding='utf-8') as f: return json.load(f)
    return []

@app.get("/api/imagen/{nombre_bodega}")
async def obtener_imagen_bodega(nombre_bodega: str):
    posibles = [f"{nombre_bodega}.png", f"{nombre_bodega.lower().replace(' ', '_')}.png"]
    for n in posibles:
        ruta = os.path.join(GRAPHICS_PATH, n)
        if os.path.exists(ruta): return FileResponse(ruta, media_type="image/png")
    raise HTTPException(status_code=404)

class ControlPanel(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Agustina Falcon - Web Server Control Panel")
        self.geometry("360x540")
        self.resizable(False, False)
        self.configure(fg_color="#0b0c0d")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        # Cargar Logo desde ruta corregida
        logo_path = os.path.join(STATIC_DIR, "ysd.png")
        # Asegurar copia local del icono junto a este archivo para compatibilidad PyInstaller
        try:
            local_icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ysd.png')
            if not os.path.exists(local_icon) and os.path.exists(logo_path):
                try:
                    shutil.copy(logo_path, local_icon)
                except Exception:
                    pass
            # Preferir el icono local si existe
            use_icon = local_icon if os.path.exists(local_icon) else logo_path
            if os.path.exists(use_icon):
                img_logo = Image.open(use_icon)
                self.logo_ctk = ctk.CTkImage(light_image=img_logo, dark_image=img_logo, size=(100, 100))
                ctk.CTkLabel(self, image=self.logo_ctk, text="").pack(pady=(30, 10))
                # Intentar aplicar icono de ventana (iconphoto + .ico en Windows)
                try:
                    try:
                        from PIL import ImageTk
                    except Exception:
                        ImageTk = None
                    if ImageTk:
                        tk_img = ImageTk.PhotoImage(Image.open(use_icon))
                        try:
                            self.iconphoto(False, tk_img)
                            self._icon_img = tk_img
                        except Exception:
                            pass
                    # Generar .ico en Windows para que aparezca en la barra de tareas
                    if os.name == 'nt':
                        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ysd.ico')
                        if not os.path.exists(ico_path):
                            try:
                                img2 = Image.open(use_icon)
                                img2.save(ico_path, format='ICO', sizes=[(64,64),(32,32),(16,16)])
                            except Exception:
                                pass
                        if os.path.exists(ico_path):
                            try:
                                self.iconbitmap(ico_path)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

        ctk.CTkLabel(self, text="Agustina Falcon", font=("Orbitron", 22, "bold"), text_color="#ffffff").pack()
        ctk.CTkLabel(self, text="Server Control Panel", font=("Helvetica", 12), text_color="#666").pack(pady=(0, 20))

        self.card = ctk.CTkFrame(self, fg_color="#151618", corner_radius=15, border_width=1, border_color="#1a1c1e")
        self.card.pack(pady=10, padx=30, fill="x")

        self.led = ctk.CTkLabel(self.card, text="●", font=("Helvetica", 24), text_color="#ff3b3b")
        self.led.pack(side="left", padx=(20, 10), pady=15)
        
        self.status_lbl = ctk.CTkLabel(self.card, text="SISTEMA OFFLINE", font=("Helvetica", 13, "bold"), text_color="#fff")
        self.status_lbl.pack(side="left")

        self.sw_var = ctk.StringVar(value="off")

        self.sw = ctk.CTkSwitch(self, text="Activar Host Local", command=self.toggle, 
                    variable=self.sw_var, onvalue="on", offvalue="off",
                    progress_color="#3b3b3b", button_color="#fff")
        self.sw.pack(pady=30)
        self.uvicorn_process = None

        self.btn_web = ctk.CTkButton(self, text="ABRIR MAPA INTERACTIVO", font=("Helvetica", 12, "bold"),
                       fg_color="#3b3b3b", text_color="#ffffff", hover_color="#2f2038",
                       height=45, corner_radius=10, command=lambda: webbrowser.open(f"http://{direccion_ip_local}:{PUERTO}"))
        self.btn_web.pack(pady=5, padx=30, fill="x")

        ctk.CTkButton(self, text="Salir", fg_color="transparent", text_color="#FFFFFF", hover_color="#1a1c1e",
                 command=self.confirmar_cierre).pack(pady=20)

        # Tray Icon corregido
        icon_img = Image.open(logo_path) if os.path.exists(logo_path) else Image.new('RGB', (64, 64), (170, 0, 255))
        menu = (item('Mostrar Panel', self.deiconify), item('Cerrar Sistema', lambda: os._exit(0)))
        self.tray = pystray.Icon("YRZ", icon_img, "Agustina Falcon", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def toggle(self):
        import subprocess
        if self.sw_var.get() == "on":
            self.led.configure(text_color="#ffd700")
            self.status_lbl.configure(text="INICIANDO...")
            # Ejecutar uvicorn como proceso externo, usando RUN_UVICORN=1 para evitar bucle
            if self.uvicorn_process is None or self.uvicorn_process.poll() is not None:
                env = os.environ.copy()
                env["RUN_UVICORN"] = "1"
                self.uvicorn_process = subprocess.Popen([sys.executable, os.path.abspath(__file__)], cwd=os.path.dirname(os.path.abspath(__file__)), env=env)
            threading.Thread(target=self.health_loop, daemon=True).start()
        else:
            # Solo apaga el host, no la app
            self.led.configure(text_color="#ff3b3b")
            self.status_lbl.configure(text="SISTEMA OFFLINE")
            if self.uvicorn_process and self.uvicorn_process.poll() is None:
                self.uvicorn_process.terminate()
                self.uvicorn_process = None
    def confirmar_cierre(self):
        import tkinter.messagebox as mb
        respuesta = mb.askquestion(
            "Cerrar App",
            "¿Quieres cerrar completamente la aplicación o minimizarla a la barra?\n\nSí = Cerrar completamente\nNo = Minimizar a barra"
        )
        if respuesta == "yes":
            # Cerrar completamente
            self.tray.stop()
            self.destroy()
            os._exit(0)
        else:
            # Minimizar a barra
            self.withdraw()
            # Puedes restaurar desde el icono de la bandeja

    def health_loop(self):
        while True:
            try:
                if requests.get(f"http://{direccion_ip_local}:{PUERTO}/api/health", timeout=1).status_code == 200:
                    self.led.configure(text_color="#00ff7f")
                    self.status_lbl.configure(text="SISTEMA ONLINE")
                    break
            except: pass
            time.sleep(1)

if __name__ == "__main__":
    # Si se ejecuta con RUN_UVICORN=1, solo lanza el servidor y no la GUI
    if os.environ.get("RUN_UVICORN") == "1":
        # Redirigir stdout/stderr a un objeto válido si están en None
        import sys
        import io
        if sys.stdout is None:
            sys.stdout = io.StringIO()
        if sys.stderr is None:
            sys.stderr = io.StringIO()
        import uvicorn
        uvicorn.run(app, host=direccion_ip_local, port=PUERTO, log_level="critical", access_log=False)
    else:
        # Evitar que los prints crasheen la app sin consola
        if sys.executable.endswith("pythonw.exe"):
            sys.stdout = open(os.devnull, "w")
            sys.stderr = open(os.devnull, "w")

        ctk.set_appearance_mode("dark")
        app_gui = ControlPanel()
        app_gui.mainloop()