import cv2
import json
import os
import customtkinter as ctk
from PIL import Image
import shutil
import sys
try:
    from PIL import ImageTk
except Exception:
    ImageTk = None
from pyzbar.pyzbar import decode
import numpy as np
from datetime import datetime
from pathlib import Path
import tkinter.ttk as ttk

# --- CONFIGURACIÓN DLL (preferir copia local junto al exe, luego detectar) ---
pyzbar_path = None
current_dir = os.path.dirname(os.path.abspath(__file__))
# 1) Preferir paquete `pyzbar` incluido junto al ejecutable (pyzbar/ en el directorio)
local_pyzbar = os.path.join(current_dir, 'pyzbar')
if os.path.exists(local_pyzbar):
    pyzbar_path = local_pyzbar
else:
    # 2) Si hay DLLs locales (copiadas al folder de la app), úsalas
    if os.name == 'nt':
        try:
            import glob
            local_dlls = glob.glob(os.path.join(current_dir, '*.dll'))
            if local_dlls:
                try:
                    os.add_dll_directory(current_dir)
                except Exception:
                    pass
        except Exception:
            pass

    # 3) Intentar detectar paquete instalado/importable
    if pyzbar_path is None:
        try:
            import pyzbar
            pyzbar_path = os.path.dirname(pyzbar.__file__)
        except Exception:
            import site, sysconfig
            candidates = []
            try:
                candidates.extend(site.getsitepackages())
            except Exception:
                pass
            try:
                pure = sysconfig.get_paths().get('purelib')
                if pure:
                    candidates.append(pure)
            except Exception:
                pass
            # Removed AppData site-packages fallback (no hardcoded per-user Python paths)

            for base in candidates:
                if not base:
                    continue
                p = os.path.join(base, 'pyzbar')
                if os.path.exists(p):
                    pyzbar_path = p
                    break

    # 4) Si aún no hay path, ver si PyInstaller colocó la carpeta en _MEIPASS
    if pyzbar_path is None and hasattr(sys, '_MEIPASS'):
        candidate = os.path.join(sys._MEIPASS, 'pyzbar')
        if os.path.exists(candidate):
            pyzbar_path = candidate

# Si encontramos una carpeta pyzbar, registrar como carpeta de DLLs en Windows
if pyzbar_path and os.name == 'nt':
    try:
        os.add_dll_directory(pyzbar_path)
    except Exception:
        pass

ACCENT_COLOR = "#DA9CFF"
BG_DARK = "#121212"
FRAME_BG = "#1E1E1E"

class BodegaStorageMap(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Agustina Falcon | Gestión de Unidades")
        # Establecer icono YSD local (copiar si es necesario)
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            local_icon = os.path.join(current_dir, 'ysd.png')
            if not os.path.exists(local_icon):
                possible = []
                if hasattr(sys, '_MEIPASS'):
                    possible.append(os.path.join(sys._MEIPASS, 'static', 'ysd.png'))
                    possible.append(os.path.join(sys._MEIPASS, 'ysd.png'))
                possible.append(os.path.join(current_dir, 'static', 'ysd.png'))
                possible.append(os.path.join(current_dir, '..', 'local_remote_w', 'static', 'ysd.png'))
                for p in possible:
                    if p and os.path.exists(p):
                        try:
                            shutil.copy(p, local_icon)
                        except Exception:
                            pass
                        break
            if ImageTk and os.path.exists(local_icon):
                try:
                    tk_img = ImageTk.PhotoImage(Image.open(local_icon))
                    self.iconphoto(False, tk_img)
                    self._icon_img = tk_img
                except Exception:
                    pass
            # Generar .ico en Windows para que aparezca en la barra de tareas
            if os.name == 'nt' and os.path.exists(local_icon):
                try:
                    ico_path = os.path.join(current_dir, 'ysd.ico')
                    if not os.path.exists(ico_path):
                        img2 = Image.open(local_icon)
                        img2.save(ico_path, format='ICO', sizes=[(64,64),(32,32),(16,16)])
                    if os.path.exists(ico_path):
                        try:
                            self.iconbitmap(ico_path)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        self.after(0, lambda: self.state('zoomed'))
        self.configure(fg_color=BG_DARK)

        # RUTA ESPECÍFICA EN DOCUMENTS DEL USUARIO (portable)
        storage_dir = Path.home() / "Documents" / "Yuuruii" / "AgustinaFalcon"
        storage_dir.mkdir(parents=True, exist_ok=True)
        self.ruta_json = storage_dir / "inventario_global.json"
        self.inventario = self.cargar_datos()
        self.carrito = {} 
        self.ultimo_scan_time = 0

        self.setup_ui()
        
        self.cap = cv2.VideoCapture(1)
        self.bucle_video()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        # --- PANEL IZQUIERDO: INVENTARIO GLOBAL ---
        self.panel_izq = ctk.CTkFrame(self, fg_color=FRAME_BG, corner_radius=20)
        self.panel_izq.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self.lbl_camara = ctk.CTkLabel(self.panel_izq, text="")
        self.lbl_camara.pack(pady=10)

        self.busqueda_var = ctk.StringVar()
        self.busqueda_var.trace_add("write", self.filtrar_tabla_global)
        self.entry_busqueda = ctk.CTkEntry(self.panel_izq, placeholder_text=" 🔍 Buscar...", height=40, border_color=ACCENT_COLOR, textvariable=self.busqueda_var)
        self.entry_busqueda.pack(fill="x", padx=40, pady=10)

        self.estilizar_tablas()
        self.tabla_global = self.crear_tabla(self.panel_izq, ["ID Interno", "Nombre", "Stock Total"])
        self.tabla_global.pack(fill="both", expand=True, padx=40, pady=20)

        # --- PANEL DERECHO: LISTA DE ESCANEO (CENTRADAS) ---
        self.panel_der = ctk.CTkFrame(self, fg_color=FRAME_BG, corner_radius=20, border_width=2, border_color=ACCENT_COLOR)
        self.panel_der.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(self.panel_der, text="LISTA DE ESCANEO", font=("Segoe UI", 22, "bold"), text_color=ACCENT_COLOR).pack(pady=15)
        
        self.tabla_carrito = self.crear_tabla(self.panel_der, ["ID Interno", "Producto", "Cant."])
        self.tabla_carrito.pack(fill="both", expand=True, padx=20, pady=10)
        self.tabla_carrito.bind("<Button-3>", self.eliminar_del_carrito_click_derecho)  # Click derecho para eliminar
        self.tabla_carrito.bind("<Double-1>", self.editar_cantidad_carrito)  # Doble clic para editar cantidad
        
        # AJUSTE MANUAL DE COLUMNAS PARA LLENAR EL ESPACIO
        self.tabla_carrito.column("ID Interno", width=100, anchor="center", stretch=False)
        self.tabla_carrito.column("Producto", width=200, anchor="w", stretch=True) 
        self.tabla_carrito.column("Cant.", width=80, anchor="center", stretch=False)
        
        # Agregar etiqueta de ayuda para indicar que es editable
        ctk.CTkLabel(
            self.panel_der, 
            text="💡 Doble clic en la cantidad para editar manualmente", 
            font=("Segoe UI", 9, "italic"), 
            text_color="#999999"
        ).pack(pady=5)

        # --- BOTONES DE ACCIÓN DEL CARRITO - LAYOUT MINIMALISTA ---
        frame_botones_carrito = ctk.CTkFrame(self.panel_der, fg_color="transparent", corner_radius=12)
        frame_botones_carrito.pack(fill="x", padx=15, pady=8)
        
        self.btn_eliminar_carrito = ctk.CTkButton(
            frame_botones_carrito, 
            text="❌ Eliminar", 
            fg_color="#CC3333", 
            hover_color="#EE5555",
            text_color="white", 
            height=38, 
            font=("Segoe UI", 11, "bold"), 
            corner_radius=10,
            command=self.eliminar_del_carrito
        )
        self.btn_eliminar_carrito.pack(side="left", fill="both", expand=True, padx=3)
        
        self.btn_limpiar_carrito = ctk.CTkButton(
            frame_botones_carrito, 
            text="🗑️ Limpiar", 
            fg_color="#884444", 
            hover_color="#BB6666",
            text_color="white", 
            height=38, 
            font=("Segoe UI", 11, "bold"), 
            corner_radius=10,
            command=self.limpiar_carrito
        )
        self.btn_limpiar_carrito.pack(side="left", fill="both", expand=True, padx=3)

        # --- BOTONES DE REGISTRO - LAYOUT LIMPIO ---
        frame_botones_registro = ctk.CTkFrame(self.panel_der, fg_color="transparent", corner_radius=12)
        frame_botones_registro.pack(fill="x", padx=15, pady=8)

        self.btn_out = ctk.CTkButton(
            frame_botones_registro, 
            text="➖ DESPACHO", 
            fg_color="#884444", 
            hover_color="#BB6666",
            text_color="white", 
            height=38, 
            font=("Segoe UI", 11, "bold"), 
            corner_radius=10,
            command=lambda: self.finalizar("venta")
        )
        self.btn_out.pack(side="left", fill="both", expand=True, padx=3)
        
        self.btn_in = ctk.CTkButton(
            frame_botones_registro, 
            text="➕ INGRESO", 
            fg_color=ACCENT_COLOR, 
            hover_color="#E0B0FF",
            text_color="black", 
            height=38, 
            font=("Segoe UI", 11, "bold"), 
            corner_radius=10,
            command=lambda: self.finalizar("entrada")
        )
        self.btn_in.pack(side="left", fill="both", expand=True, padx=3)
        
        # Cargar inventario en la UI al inicio
        self.filtrar_tabla_global()

    def estilizar_tablas(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=FRAME_BG, foreground="#E0E0E0", fieldbackground=FRAME_BG, borderwidth=0, font=("Segoe UI", 11), rowheight=40)
        style.configure("Treeview.Heading", background="#151515", foreground=ACCENT_COLOR, borderwidth=0, font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[('selected', ACCENT_COLOR)], foreground=[('selected', 'black')])

    def crear_tabla(self, parent, cols):
        t = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            t.heading(c, text=c)
            t.column(c, anchor="center", stretch=True)
        return t

    def cargar_datos(self):
        try:
            if os.path.exists(self.ruta_json):
                with open(self.ruta_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "_mapeo_barras" not in data: data["_mapeo_barras"] = {}
                    return data
            return {"_mapeo_barras": {}}
        except: return {"_mapeo_barras": {}}

    def guardar_datos(self):
        with open(self.ruta_json, 'w', encoding='utf-8') as f:
            json.dump(self.inventario, f, indent=4, ensure_ascii=False)
        self.filtrar_tabla_global()

    def bucle_video(self):
        ret, frame = self.cap.read()
        if ret:
            ahora = datetime.now().timestamp()
            if ahora - self.ultimo_scan_time > 1.8:
                for obj in decode(frame):
                    barcode = obj.data.decode('utf-8')
                    self.procesar_barcode(barcode)
                    self.ultimo_scan_time = ahora
                    break
            frame_disp = cv2.resize(frame, (480, 270))
            img = Image.fromarray(cv2.cvtColor(frame_disp, cv2.COLOR_BGR2RGB))
            ctk_img = ctk.CTkImage(img, size=(480, 270))
            self.lbl_camara.configure(image=ctk_img, text="")
        self.after(10, self.bucle_video)

    def procesar_barcode(self, barcode):
        mapeo = self.inventario.get("_mapeo_barras", {})
        
        if barcode in mapeo:
            vinculo = mapeo[barcode]
            id_int = vinculo["id_interno"]
            factor = vinculo["factor"]
            
            nombre = self.inventario[id_int]['nombre']
            if id_int in self.carrito: self.carrito[id_int]['cant'] += factor
            else: self.carrito[id_int] = {'nombre': nombre, 'cant': factor}
            self.actualizar_carrito_visual()
        else:
            self.gestionar_nuevo_desconocido(barcode)

    def gestionar_nuevo_desconocido(self, barcode):
        # Opción 1: Vincular a existente o crear nuevo item
        opcion = ctk.CTkInputDialog(text=f"Código desconocido: {barcode}\n1. Vincular a ID existente\n2. Crear PRODUCTO NUEVO desde cero\n(Escriba 1 o 2):", title="Nuevo Registro").get_input()
        
        if opcion == "1":
            id_int = ctk.CTkInputDialog(text="Ingrese el ID Interno existente:", title="Vincular").get_input()
            if id_int in self.inventario:
                self.vincular_barras_a_id(barcode, id_int)
            else:
                print("ID no encontrado.")
        
        elif opcion == "2":
            id_int = ctk.CTkInputDialog(text="Cree un nuevo ID Interno para este producto:", title="ID Nuevo").get_input()
            if id_int:
                nombre = ctk.CTkInputDialog(text="Nombre del nuevo producto:", title="Nombre").get_input()
                if nombre:
                    self.inventario[id_int] = {"nombre": nombre, "stock": 0}
                    self.vincular_barras_a_id(barcode, id_int)

    def vincular_barras_a_id(self, barcode, id_int):
        factor = ctk.CTkInputDialog(text=f"¿Cuántas unidades representa este código de barras para el ID {id_int}?\n(Ej: 1 unidad, 50 para caja, 1000 para bulto):", title="Factor").get_input()
        if factor and factor.isdigit():
            self.inventario["_mapeo_barras"][barcode] = {"id_interno": id_int, "factor": int(factor)}
            self.guardar_datos()
            self.procesar_barcode(barcode)

    def actualizar_carrito_visual(self):
        for i in self.tabla_carrito.get_children(): self.tabla_carrito.delete(i)
        for id_int, info in self.carrito.items():
            self.tabla_carrito.insert("", "end", values=(id_int, info['nombre'], info['cant']))

    def eliminar_del_carrito(self):
        """Elimina el item seleccionado del carrito sin afectar el inventario"""
        seleccion = self.tabla_carrito.selection()
        if not seleccion:
            print("Selecciona un item para eliminar del carrito")
            return
        
        # Obtener el item seleccionado
        item = seleccion[0]
        valores = self.tabla_carrito.item(item, 'values')
        if not valores:
            return
        id_int = valores[0]
        
        # Eliminar del diccionario del carrito
        if id_int in self.carrito:
            del self.carrito[id_int]
            self.actualizar_carrito_visual()
            print(f"Eliminado '{valores[1]}' del carrito")

    def eliminar_del_carrito_click_derecho(self, event):
        """Permite eliminar un item con click derecho"""
        item = self.tabla_carrito.identify('item', event.x, event.y)
        if item:
            self.tabla_carrito.selection_set(item)
            self.after(50, self.eliminar_del_carrito)  # Pequeño delay para asegurar la selección

    def limpiar_carrito(self):
        """Limpia todos los items del carrito sin afectar el inventario"""
        if not self.carrito:
            print("El carrito ya está vacío")
            return
        self.carrito = {}
        self.actualizar_carrito_visual()

    def editar_cantidad_carrito(self, event):
        """Permite editar la cantidad haciendo doble clic en la columna 'Cant.'"""
        item = self.tabla_carrito.identify('item', event.x, event.y)
        columna = self.tabla_carrito.identify_column(event.x)
        
        # Columna 3 es "Cant." (índice 2, pero en identify_column es #3)
        if item and columna == "#3":
            valores = self.tabla_carrito.item(item, 'values')
            id_int = valores[0]
            cant_actual = valores[2]
            
            # Crear diálogo para editar cantidad
            nueva_cant = ctk.CTkInputDialog(
                text=f"Editar cantidad para {valores[1]}\nCantidad actual: {cant_actual}", 
                title="Editar Cantidad"
            ).get_input()
            
            if nueva_cant and nueva_cant.isdigit():
                nueva_cant = int(nueva_cant)
                if id_int in self.carrito:
                    self.carrito[id_int]['cant'] = nueva_cant
                    self.actualizar_carrito_visual()
                    print(f"Cantidad actualizada a {nueva_cant} para {valores[1]}")

    def filtrar_tabla_global(self, *args):
        query = self.busqueda_var.get().lower()
        for i in self.tabla_global.get_children(): self.tabla_global.delete(i)
        for id_int, data in self.inventario.items():
            if id_int.startswith("_"): continue
            if query in id_int.lower() or query in data.get('nombre', '').lower():
                self.tabla_global.insert("", "end", values=(id_int, data['nombre'], data.get('stock', 0)))

    def finalizar(self, modo):
        if not self.carrito: return
        for id_int, info in self.carrito.items():
            stock_actual = self.inventario[id_int].get('stock', 0)
            if modo == "venta": self.inventario[id_int]['stock'] = stock_actual - info['cant']
            else: self.inventario[id_int]['stock'] = stock_actual + info['cant']
        self.guardar_datos()
        self.carrito = {}; self.actualizar_carrito_visual()

if __name__ == "__main__":
    app = BodegaStorageMap()
    app.mainloop()