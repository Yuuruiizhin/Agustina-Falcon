import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import sys
import shutil
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None
import pandas as pd
import json
import threading
from pathlib import Path

# ============================================
# CONFIGURACIÓN
# ============================================
COLUMNA_ID = 'Código Int.'
COLUMNA_NOMBRE = 'Glosa'
COLUMNA_STOCK = 'Stock'

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLOR_PRIMARY = "#DA9CFF"
COLOR_BG = "#0d0d0d"
COLOR_PANEL = "#1a1a1a"

class InventoryManager(ctk.CTk):
    def __init__(self):
        super().__init__()
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
            # En Windows, generar .ico para que aparezca en la barra de tareas
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

        self.title("Agustina Falcon Inventory Manager")
        
        # 1. CONFIGURACIÓN DE VENTANA (MAXIMIZADA Y CENTRADA)
        self.width = 1400
        self.height = 900
        self.centrar_ventana(self.width, self.height)
        self.after(0, lambda: self.state('zoomed')) # Maximiza en Windows al arrancar
        
        # Datos
        self.inventario_json = {}
        self.items_filtrados = []
        self.pagina_actual = 0
        self.items_por_pagina = 25
        self.after_id = None 
        
        self.ruta_guardado = Path.home() / "Documents" / "Yuuruii" / "AgustinaFalcon"
        self.ruta_guardado.mkdir(parents=True, exist_ok=True)
        self.archivo_json = self.ruta_guardado / "inventario_global.json"
        
        self.crear_interfaz()
        threading.Thread(target=self.cargar_json_inicial, daemon=True).start()

    def centrar_ventana(self, ancho, alto):
        """Calcula la posición para que la ventana esté en el centro de la pantalla"""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        x = (screen_width // 2) - (ancho // 2)
        y = (screen_height // 2) - (alto // 2)
                                                                                                                                                                                                                    
        self.geometry(f'{ancho}x{alto}+{x}+{y}')

    def crear_interfaz(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=280, fg_color=COLOR_PANEL, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Mostrar imagen ysd.png en lugar del texto "AF"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_icon = os.path.join(current_dir, 'ysd.png')
        if ImageTk and os.path.exists(local_icon):
            try:
                img = Image.open(local_icon)
                img = img.resize((80, 80), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                self.sidebar_logo = ctk.CTkLabel(self.sidebar, image=tk_img, text="", width=80, height=80)
                self.sidebar_logo.image = tk_img  # Evitar que se elimine la referencia
                self.sidebar_logo.pack(pady=20)
            except Exception as e:
                print(f"Error loading image: {e}")
        else:
            ctk.CTkLabel(self.sidebar, text="AF", font=("Arial", 32, "bold"), text_color=COLOR_PRIMARY).pack(pady=20)
        
        self.btn_importar = ctk.CTkButton(self.sidebar, text="📁 Importar Excel", command=self.iniciar_importacion, fg_color=COLOR_PRIMARY, text_color="#000")
        self.btn_importar.pack(pady=10, padx=20)
        
        self.btn_guardar = ctk.CTkButton(self.sidebar, text="💾 Guardar Cambios", command=self.guardar_json).pack(pady=10, padx=20)
        
        self.label_stats = ctk.CTkLabel(self.sidebar, text="Sincronizando...", font=("Arial", 13))
        self.label_stats.pack(pady=20)

        # Barra de progreso estilizada
        self.progress_bar = ctk.CTkProgressBar(self.sidebar, mode="determinate", progress_color=COLOR_PRIMARY, height=8)
        self.progress_bar.pack(pady=5, padx=20)
        self.progress_bar.set(0)

        # MAIN
        self.main_frame = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        
        self.top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=20, pady=20)

        # Scanner de salida
        self.entry_scan = ctk.CTkEntry(self.top_bar, placeholder_text="SCANNER (Salida)...", width=250, height=45, border_color=COLOR_PRIMARY, font=("Consolas", 14))
        self.entry_scan.pack(side="left", padx=(0, 20))
        self.entry_scan.bind('<Return>', lambda e: self.escanear_item())

        # Buscador en tiempo real con evento KeyRelease
        self.entry_search = ctk.CTkEntry(self.top_bar, placeholder_text="🔍 Filtrar en tiempo real (Nombre o Código)...", width=500, height=45)
        self.entry_search.pack(side="left")
        self.entry_search.bind('<KeyRelease>', self.on_search_key)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color=COLOR_PANEL, label_text="VISUALIZADOR DE INVENTARIO")
        self.scrollable_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # NAVEGACIÓN
        self.nav_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=50)
        self.nav_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="◀ ANTERIOR", width=120, command=self.pagina_anterior)
        self.btn_prev.pack(side="left", padx=10)
        
        self.label_paginas = ctk.CTkLabel(self.nav_frame, text="Página 1 de 1", font=("Arial", 12, "bold"))
        self.label_paginas.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text="SIGUIENTE ▶", width=120, command=self.pagina_siguiente)
        self.btn_next.pack(side="right", padx=10)

    def on_search_key(self, event):
        """Gestiona el debounce para que la búsqueda sea fluida"""
        if self.after_id:
            self.after_cancel(self.after_id)
        
        # Pequeña animación de la barra para indicar que detectó escritura
        self.progress_bar.set(0.3)
        self.after_id = self.after(300, self.filtrar_busqueda)

    def cargar_json_inicial(self):
        if self.archivo_json.exists():
            try:
                with open(self.archivo_json, 'r', encoding='utf-8') as f:
                    self.inventario_json = json.load(f)
                self.items_filtrados = list(self.inventario_json.items())
                self.after(0, self.actualizar_interfaz)
            except: pass

    def filtrar_busqueda(self):
        query = self.entry_search.get().lower().strip()
        self.progress_bar.set(0.6) # Fase 2 de la barra
        
        if not query:
            self.items_filtrados = list(self.inventario_json.items())
        else:
            # Búsqueda optimizada
            self.items_filtrados = [
                (str(k), v) for k, v in self.inventario_json.items() 
                if query in str(k).lower() or query in str(v.get('nombre', '')).lower()
            ]
        
        self.pagina_actual = 0
        self.actualizar_interfaz()
        self.progress_bar.set(1)
        self.after(500, lambda: self.progress_bar.set(0)) # Reset barra

    def actualizar_interfaz(self):
        for widget in self.scrollable_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame): widget.destroy()
        
        total_items = len(self.items_filtrados)
        total_paginas = max(1, (total_items + self.items_por_pagina - 1) // self.items_por_pagina)
        
        if self.pagina_actual >= total_paginas: self.pagina_actual = total_paginas - 1
        
        start = self.pagina_actual * self.items_por_pagina
        end = min(start + self.items_por_pagina, total_items)
        lote = self.items_filtrados[start:end]
        
        for id_i, d in lote:
            f = ctk.CTkFrame(self.scrollable_frame, fg_color="#1e1e1e", height=45)
            f.pack(fill="x", pady=2, padx=5)
            f.pack_propagate(False)
            
            stk = d.get('stock', 0)
            color_s = COLOR_PRIMARY if stk > 0 else "#FF6B6B"
            
            ctk.CTkLabel(f, text=f"{id_i}", width=130, font=("Consolas", 13, "bold"), text_color="#888").pack(side="left", padx=10)
            ctk.CTkLabel(f, text=f"{str(d.get('nombre', ''))[:80]}", anchor="w", font=("Arial", 12)).pack(side="left", padx=10, expand=True, fill="x")
            
            # Stock con fondo sutil para resaltar
            stk_frame = ctk.CTkFrame(f, fg_color="#282828", width=100, corner_radius=6)
            stk_frame.pack(side="right", padx=15, pady=5)
            ctk.CTkLabel(stk_frame, text=f"{stk}", text_color=color_s, font=("Arial", 13, "bold")).pack(expand=True)

        self.label_paginas.configure(text=f"Viendo {start+1}-{end} de {total_items} resultados")
        self.label_stats.configure(text=f"Base de datos: {len(self.inventario_json)} items")
        
        self.btn_prev.configure(state="normal" if self.pagina_actual > 0 else "disabled")
        self.btn_next.configure(state="normal" if end < total_items else "disabled")

    def pagina_siguiente(self):
        self.pagina_actual += 1
        self.actualizar_interfaz()

    def pagina_anterior(self):
        self.pagina_actual -= 1
        self.actualizar_interfaz()

    def escanear_item(self):
        cod = self.entry_scan.get().strip()
        if cod in self.inventario_json:
            self.inventario_json[cod]['stock'] -= 1
            self.entry_scan.delete(0, 'end')
            
            # Efecto visual de "salida confirmada"
            self.entry_scan.configure(border_color="#4ecb71")
            self.after(500, lambda: self.entry_scan.configure(border_color=COLOR_PRIMARY))
            
            # Actualizar datos sin mover la página
            query = self.entry_search.get().lower().strip()
            if query:
                self.items_filtrados = [(k, v) for k, v in self.inventario_json.items() 
                                       if query in str(k).lower() or query in str(v.get('nombre', '')).lower()]
            else:
                self.items_filtrados = list(self.inventario_json.items())
            
            self.actualizar_interfaz()
        else:
            self.entry_scan.configure(border_color="#ff6b6b")
            self.after(500, lambda: self.entry_scan.configure(border_color=COLOR_PRIMARY))
            messagebox.showwarning("No encontrado", f"El código {cod} no está en la base de datos.")

    def iniciar_importacion(self):
        archivo = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not archivo: return
        self.progress_bar.set(0.1)
        threading.Thread(target=self.proceso_importacion, args=(archivo,), daemon=True).start()

    def proceso_importacion(self, archivo):
        try:
            df_raw = pd.read_excel(archivo, header=None)
            col_id, col_glosa, col_stock, start_row = None, None, None, None
            for i, row in df_raw.iterrows():
                row_list = [str(val).strip() for val in row.values]
                if COLUMNA_ID in row_list:
                    col_id, col_glosa, start_row = row_list.index(COLUMNA_ID), row_list.index(COLUMNA_NOMBRE), i + 1
                if COLUMNA_STOCK in row_list: col_stock = row_list.index(COLUMNA_STOCK)

            if col_id is not None:
                new_data = {}
                for i in range(start_row, len(df_raw)):
                    fila = df_raw.iloc[i]
                    id_v = str(fila[col_id]).split('.')[0].strip()
                    if id_v == 'nan' or id_v == '': continue
                    try: stk = int(float(fila[col_stock])) if pd.notnull(fila[col_stock]) else 0
                    except: stk = 0
                    new_data[id_v] = {"nombre": str(fila[col_glosa]).strip(), "stock": stk}
                
                self.inventario_json = new_data
                self.items_filtrados = list(self.inventario_json.items())
                self.pagina_actual = 0
                self.after(0, self.actualizar_interfaz)
                self.guardar_json(silencioso=True)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def guardar_json(self, silencioso=False):
        try:
            with open(self.archivo_json, 'w', encoding='utf-8') as f:
                json.dump(self.inventario_json, f, indent=4, ensure_ascii=False)
            if not silencioso: messagebox.showinfo("Guardado", "Base de datos sincronizada.")
        except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = InventoryManager()
    app.mainloop()