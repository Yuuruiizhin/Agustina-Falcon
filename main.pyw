import customtkinter as ctk
from tkinter import messagebox
import json
import hashlib
from pathlib import Path
import subprocess  # Necesario para abrir los otros archivos
import sys
import os
import shutil
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

# ============================================
# CONFIGURACIÓN
# ============================================
ADMIN_PASSWORD = "226000771"
# ============================================

# Configuración de tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Colores personalizados (centralizados en common_theme)
try:
    import common_theme as theme
    COLOR_PRIMARY = theme.COLOR_PRIMARY
    COLOR_BG = theme.COLOR_BG
    COLOR_PANEL = theme.COLOR_PANEL
    COLOR_HOVER = theme.COLOR_HOVER
except Exception:
    # Fallback si common_theme no está disponible
    COLOR_PRIMARY = "#DA9CFF"
    COLOR_BG = "#0d0d0d"
    COLOR_PANEL = "#1a1a1a"
    COLOR_HOVER = "#2d2d2d"

class LoginSystem(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Establecer icono YSD local (copia si es necesario)
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            local_icon = os.path.join(current_dir, 'ysd.png')
            if not os.path.exists(local_icon):
                # buscar en static o en recurso pyinstaller
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
            # aplicar icono si PIL disponible
            if Image and ImageTk and os.path.exists(local_icon):
                try:
                    img = Image.open(local_icon)
                    tk_img = ImageTk.PhotoImage(img)
                    self.iconphoto(False, tk_img)
                    self._icon_img = tk_img
                except Exception:
                    pass
        except Exception:
            pass
        
        # Configuración de ventana
        self.title("YSD - Sistema de Login")
        self.geometry("500x700")
        self.resizable(False, False)
        
        # Centrar ventana en la pantalla
        self.centrar_ventana()
        
        # Variables
        self.ruta_credenciales = self.obtener_ruta_credenciales()
        self.archivo_credenciales = self.ruta_credenciales / "credenciales.json"
        self.usuario_actual = None
        
        # Crear archivo de credenciales si no existe
        self.inicializar_credenciales()
        
        # Crear interfaz de login con animación
        self.after(100, self.crear_interfaz_login)

    # --- NUEVA FUNCIÓN PARA EJECUTAR ARCHIVOS ---
    def ejecutar_script(self, ruta_relativa):
        """Lanza un script de python externo"""
        ruta_completa = Path.cwd() / ruta_relativa
        if not ruta_completa.exists():
            messagebox.showerror("Error", f"No se encontró el archivo en:\n{ruta_relativa}")
            return
        
        try:
            # Ejecuta usando el intérprete de python actual para evitar conflictos
            subprocess.Popen([sys.executable, str(ruta_completa)])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el software: {e}")
    
    def centrar_ventana(self):
        """Centra la ventana en la pantalla"""
        self.update_idletasks()
        ancho_ventana = 500
        alto_ventana = 700
        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla = self.winfo_screenheight()
        
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2) - 30
        
        self.geometry(f"500x700+{x}+{y}")
        
    def obtener_ruta_credenciales(self):
        """Obtiene la ruta en Documents/yuuruii/StorageMap"""
        documentos = Path.home() / "Documents"
        ruta = documentos / "Yuuruii" / "AgustinaFalcon"
        ruta.mkdir(parents=True, exist_ok=True)
        return ruta
    
    def inicializar_credenciales(self):
        """Crea el archivo de credenciales si no existe"""
        if not self.archivo_credenciales.exists():
            credenciales_vacias = {}
            with open(self.archivo_credenciales, 'w', encoding='utf-8') as f:
                json.dump(credenciales_vacias, f, indent=4, ensure_ascii=False)
    
    def hash_texto(self, texto):
        """Genera hash SHA256 de un texto"""
        return hashlib.sha256(texto.encode('utf-8')).hexdigest()
    
    def cargar_credenciales(self):
        """Carga las credenciales del archivo JSON"""
        try:
            with open(self.archivo_credenciales, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def guardar_credenciales(self, credenciales):
        """Guarda las credenciales en el archivo JSON"""
        with open(self.archivo_credenciales, 'w', encoding='utf-8') as f:
            json.dump(credenciales, f, indent=4, ensure_ascii=False)
    
    def crear_interfaz_login(self):
        """Crea la interfaz de inicio de sesión"""
        # Limpiar ventana
        for widget in self.winfo_children():
            widget.destroy()
        
        # Frame principal
        self.main_frame = ctk.CTkFrame(self, fg_color=COLOR_BG)
        self.main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Container para animación
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_BG)
        self.content_frame.pack(fill="both", expand=True)
        self.content_frame.pack_propagate(False)
        
        # Inicialmente oculto (arriba)
        self.content_frame.place(x=30, y=-700, relwidth=1, relheight=1)
        
        # Logo
        logo_label = ctk.CTkLabel(
            self.content_frame,
            text="YSD",
            font=ctk.CTkFont(family="Times New Roman", size=42, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        logo_label.pack(pady=(20, 5))
        
        subtitle_label = ctk.CTkLabel(
            self.content_frame,
            text="Sistema de Autenticación",
            font=ctk.CTkFont(size=14),
            text_color="#888888"
        )
        subtitle_label.pack(pady=(0, 25))
        
        # Panel de login
        login_panel = ctk.CTkFrame(self.content_frame, fg_color=COLOR_PANEL, corner_radius=15)
        login_panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title = ctk.CTkLabel(
            login_panel,
            text="Iniciar Sesión",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        title.pack(pady=(20, 20))
        
        # Campo Nombre
        label_nombre = ctk.CTkLabel(
            login_panel,
            text="Nombre:",
            font=ctk.CTkFont(size=14),
            text_color="#ffffff"
        )
        label_nombre.pack(pady=(0, 5))
        
        self.entry_nombre = ctk.CTkEntry(
            login_panel,
            placeholder_text="Ingrese su nombre",
            font=ctk.CTkFont(size=14),
            height=45,
            width=350,
            border_color=COLOR_PRIMARY,
            fg_color=COLOR_HOVER
        )
        self.entry_nombre.pack(pady=(0, 15))
        
        # Campo RUT
        label_rut = ctk.CTkLabel(
            login_panel,
            text="RUT:",
            font=ctk.CTkFont(size=14),
            text_color="#ffffff"
        )
        label_rut.pack(pady=(0, 5))
        
        self.entry_rut = ctk.CTkEntry(
            login_panel,
            placeholder_text="Ingrese su RUT",
            font=ctk.CTkFont(size=14),
            height=45,
            width=350,
            border_color=COLOR_PRIMARY,
            fg_color=COLOR_HOVER,
            show="*"
        )
        self.entry_rut.pack(pady=(0, 20))
        self.entry_rut.bind('<Return>', lambda e: self.verificar_login())
        
        # Botón de login
        btn_login = ctk.CTkButton(
            login_panel,
            text="INICIAR SESIÓN",
            command=self.verificar_login,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            width=350,
            fg_color=COLOR_PRIMARY,
            hover_color="#c088e6",
            text_color="#000000"
        )
        btn_login.pack(pady=(0, 15))
        
        # Separador
        separador = ctk.CTkLabel(
            login_panel,
            text="──────────  o  ──────────",
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        separador.pack(pady=(10, 10))
        
        # Texto explicativo
        texto_crear = ctk.CTkLabel(
            login_panel,
            text="¿No tienes cuenta?",
            font=ctk.CTkFont(size=13),
            text_color="#888888"
        )
        texto_crear.pack(pady=(0, 10))
        
        # Botón crear usuario
        btn_crear = ctk.CTkButton(
            login_panel,
            text="🔓 CREAR NUEVA CUENTA",
            command=self.abrir_ventana_admin,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=45,
            width=350,
            fg_color=COLOR_HOVER,
            hover_color="#3d3d3d",
            text_color=COLOR_PRIMARY,
            border_width=2,
            border_color=COLOR_PRIMARY
        )
        btn_crear.pack(pady=(0, 30))
        
        # Iniciar animación de barrido
        self.animar_barrido()
    
    def animar_barrido(self):
        """Anima la entrada con efecto de barrido hacia abajo"""
        posicion_inicial = -700
        posicion_final = 0
        duracion = 500  # ms
        pasos = 30
        delay = duracion // pasos
        incremento = (posicion_final - posicion_inicial) / pasos
        
        def animar_paso(paso):
            if paso <= pasos:
                nueva_y = posicion_inicial + (incremento * paso)
                progreso = paso / pasos
                ease = 1 - (1 - progreso) ** 3
                nueva_y = posicion_inicial + ((posicion_final - posicion_inicial) * ease)
                
                self.content_frame.place(x=0, y=nueva_y, relwidth=1, relheight=1)
                self.after(delay, lambda: animar_paso(paso + 1))
            else:
                self.content_frame.place(x=0, y=0, relwidth=1, relheight=1)
        
        animar_paso(0)
    
    def verificar_login(self):
        """Verifica las credenciales de login"""
        nombre = self.entry_nombre.get().strip()
        rut = self.entry_rut.get().strip()
        
        if not nombre or not rut:
            messagebox.showwarning("Advertencia", "⚠️ Complete todos los campos")
            return
        
        nombre_hash = self.hash_texto(nombre)
        rut_hash = self.hash_texto(rut)
        credenciales = self.cargar_credenciales()
        
        if nombre_hash in credenciales:
            if credenciales[nombre_hash] == rut_hash:
                self.usuario_actual = nombre
                # QUITAMOS EL MESSAGEBOX PARA IR DIRECTO A LAS OPCIONES
                self.crear_interfaz_principal()
            else:
                messagebox.showerror("Error", "❌ RUT incorrecto")
                self.entry_rut.delete(0, 'end')
        else:
            messagebox.showerror("Error", "❌ Usuario no encontrado")
            self.entry_nombre.delete(0, 'end')
            self.entry_rut.delete(0, 'end')
    
    def abrir_ventana_admin(self):
        """Abre ventana para solicitar contraseña de administrador"""
        ventana_admin = ctk.CTkToplevel(self)
        ventana_admin.title("Verificación de Administrador")
        ventana_admin.geometry("400x500")
        ventana_admin.resizable(False, False)
        ventana_admin.grab_set()
        
        # Centrar ventana admin
        ventana_admin.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 200
        y = (self.winfo_screenheight() // 2) - 150
        ventana_admin.geometry(f"400x500+{x}+{y}")
        
        frame = ctk.CTkFrame(ventana_admin, fg_color=COLOR_BG)
        frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        icono = ctk.CTkLabel(frame, text="🔐", font=ctk.CTkFont(size=48))
        icono.pack(pady=(20, 10))
        
        title = ctk.CTkLabel(frame, text="Acceso Administrativo", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_PRIMARY)
        title.pack(pady=(0, 30))
        
        entry_admin_pass = ctk.CTkEntry(frame, placeholder_text="Ingrese contraseña", font=ctk.CTkFont(size=14), height=45, width=300, border_color=COLOR_PRIMARY, fg_color=COLOR_HOVER, show="*")
        entry_admin_pass.pack(pady=(0, 25))
        entry_admin_pass.focus()
        
        def verificar_admin():
            if entry_admin_pass.get().strip() == ADMIN_PASSWORD:
                ventana_admin.destroy()
                self.abrir_ventana_crear_usuario()
            else:
                messagebox.showerror("Error", "❌ Contraseña de administrador incorrecta")
                entry_admin_pass.delete(0, 'end')
        
        entry_admin_pass.bind('<Return>', lambda e: verificar_admin())
        
        btn_continuar = ctk.CTkButton(frame, text="CONTINUAR", command=verificar_admin, font=ctk.CTkFont(size=14, weight="bold"), height=45, width=300, fg_color=COLOR_PRIMARY, hover_color="#c088e6", text_color="#000000")
        btn_continuar.pack()
    
    def abrir_ventana_crear_usuario(self):
        """Abre ventana para crear nuevo usuario"""
        ventana_crear = ctk.CTkToplevel(self)
        ventana_crear.title("Crear Nueva Cuenta")
        ventana_crear.geometry("450x400")
        ventana_crear.resizable(False, False)
        ventana_crear.grab_set()
        
        ventana_crear.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 225
        y = (self.winfo_screenheight() // 2) - 200
        ventana_crear.geometry(f"450x400+{x}+{y}")
        
        frame = ctk.CTkFrame(ventana_crear, fg_color=COLOR_BG)
        frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        title = ctk.CTkLabel(frame, text="Crear Nuevo Usuario", font=ctk.CTkFont(size=20, weight="bold"), text_color=COLOR_PRIMARY)
        title.pack(pady=(20, 40))
        
        entry_nombre_nuevo = ctk.CTkEntry(frame, placeholder_text="Nombre y Apellido", height=45, width=350, border_color=COLOR_PRIMARY, fg_color=COLOR_HOVER)
        entry_nombre_nuevo.pack(pady=(0, 25))
        
        entry_rut_nuevo = ctk.CTkEntry(frame, placeholder_text="RUT", height=45, width=350, border_color=COLOR_PRIMARY, fg_color=COLOR_HOVER, show="*")
        entry_rut_nuevo.pack(pady=(0, 35))
        
        def crear_usuario():
            nombre_nuevo = entry_nombre_nuevo.get().strip()
            rut_nuevo = entry_rut_nuevo.get().strip()
            if not nombre_nuevo or not rut_nuevo:
                messagebox.showwarning("Advertencia", "⚠️ Complete todos los campos")
                return
            
            nombre_hash = self.hash_texto(nombre_nuevo)
            rut_hash = self.hash_texto(rut_nuevo)
            credenciales = self.cargar_credenciales()
            
            if nombre_hash in credenciales:
                messagebox.showwarning("Advertencia", "⚠️ El usuario ya existe")
                return
            
            credenciales[nombre_hash] = rut_hash
            self.guardar_credenciales(credenciales)
            messagebox.showinfo("Éxito", f"✓ Usuario '{nombre_nuevo}' creado correctamente")
            ventana_crear.destroy()
        
        btn_crear = ctk.CTkButton(frame, text="CREAR USUARIO", command=crear_usuario, font=ctk.CTkFont(size=14, weight="bold"), height=50, width=350, fg_color=COLOR_PRIMARY, hover_color="#c088e6", text_color="#000000")
        btn_crear.pack()

    # ============================================
    # INTERFAZ PRINCIPAL CON LOS BOTONES PEDIDOS
    # ============================================
    def crear_interfaz_principal(self):
        """Crea la interfaz con las 3 opciones después del login"""
        # Limpiar ventana
        for widget in self.winfo_children():
            widget.destroy()
        
        self.geometry("600x650")
        self.centrar_ventana_principal()
        
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color=COLOR_BG)
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Header
        header = ctk.CTkFrame(main_frame, fg_color=COLOR_PANEL, corner_radius=15)
        header.pack(fill="x", pady=(0, 20))
        
        logo = ctk.CTkLabel(header, text="PANEL DE CONTROL YSD", font=ctk.CTkFont(size=24, weight="bold"), text_color=COLOR_PRIMARY)
        logo.pack(pady=20)
        
        # Panel de bienvenida
        welcome_panel = ctk.CTkFrame(main_frame, fg_color=COLOR_PANEL, corner_radius=15)
        welcome_panel.pack(fill="both", expand=True)
        
        welcome_label = ctk.CTkLabel(welcome_panel, text=f"Hola, {self.usuario_actual}", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFFFFF")
        welcome_label.pack(pady=(20, 10))
        
        instr_label = ctk.CTkLabel(welcome_panel, text="Seleccione el sistema que desea iniciar:", font=ctk.CTkFont(size=13), text_color="#888888")
        instr_label.pack(pady=(0, 20))

        # --- BOTONES DE ACCESO ---
        
        # 1. Software de bodega
        btn_bodega = ctk.CTkButton(
            welcome_panel,
            text="📦 ABRIR SOFTWARE DE BODEGA",
            command=lambda: self.ejecutar_script("local_desktop_s/bodega.py"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=55,
            width=400,
            fg_color=COLOR_HOVER,
            hover_color="#3d3d3d",
            text_color=COLOR_PRIMARY,
            border_width=1,
            border_color=COLOR_PRIMARY
        )
        btn_bodega.pack(pady=10)

        # 2. Panel servidor web
        btn_web = ctk.CTkButton(
            welcome_panel,
            text="🌐 PANEL CONTROL SERVIDOR WEB LOCAL",
            command=lambda: self.ejecutar_script("local_remote_w/app.py"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=55,
            width=400,
            fg_color=COLOR_HOVER,
            hover_color="#3d3d3d",
            text_color=COLOR_PRIMARY,
            border_width=1,
            border_color=COLOR_PRIMARY
        )
        btn_web.pack(pady=10)

        # 3. Transformación excel
        btn_excel = ctk.CTkButton(
            welcome_panel,
            text="📊 PANEL TRANSFORMACIÓN DATOS EXCEL",
            command=lambda: self.ejecutar_script("local_InventoryExel_s/inventory_manager.pyw"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=55,
            width=400,
            fg_color=COLOR_HOVER,
            hover_color="#3d3d3d",
            text_color=COLOR_PRIMARY,
            border_width=1,
            border_color=COLOR_PRIMARY
        )
        btn_excel.pack(pady=10)

        # Botón cerrar sesión
        btn_logout = ctk.CTkButton(
            welcome_panel,
            text="Cerrar Sesión",
            command=self.cerrar_sesion,
            font=ctk.CTkFont(size=12),
            height=35,
            width=150,
            fg_color="transparent",
            text_color="#ff5555",
            hover_color=COLOR_BG
        )
        btn_logout.pack(pady=(30, 10))
    
    def centrar_ventana_principal(self):
        """Centra la ventana principal"""
        self.update_idletasks()
        ancho_ventana = 600
        alto_ventana = 650
        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla = self.winfo_screenheight()
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2) - 30
        self.geometry(f"600x650+{x}+{y}")
    
    def cerrar_sesion(self):
        """Cierra la sesión y vuelve al login"""
        self.usuario_actual = None
        self.geometry("500x700")
        self.centrar_ventana()
        self.crear_interfaz_login()

if __name__ == "__main__":
    app = LoginSystem()
    app.mainloop()