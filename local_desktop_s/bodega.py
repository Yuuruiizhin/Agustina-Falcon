import sys
import json
import os
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsEllipseItem, QVBoxLayout, QHBoxLayout, QWidget, 
                             QPushButton, QInputDialog, QLineEdit, QLabel, QListWidget, 
                             QMessageBox, QCompleter, QFileDialog, QSpinBox, QComboBox,
                             QDialog, QFormLayout, QTabWidget, QListWidgetItem)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QWheelEvent, QIcon
from PyQt6.QtCore import Qt, QRectF, QStringListModel, QPoint, QPointF
from datetime import datetime

# --- CONFIGURACIÓN DE RUTAS ---
DOCS_PATH = os.path.join(os.path.expanduser("~"), "Documents", "Yuuruii", "AgustinaFalcon")
GRAPHICS_PATH = os.path.join(DOCS_PATH, "graphics")

if not os.path.exists(DOCS_PATH):
    os.makedirs(DOCS_PATH, exist_ok=True)
if not os.path.exists(GRAPHICS_PATH):
    os.makedirs(GRAPHICS_PATH, exist_ok=True)

CARPETA_IMAGENES = "bodegas"
ICONO_APP = "ysd.png"

# Diccionario dinámico de bodegas (se cargará desde archivo)
ARCHIVOS_BODEGA = {}

class EstantePoint(QGraphicsEllipseItem):
    def __init__(self, x, y, nivel, nombre_estante, radio=15, suplementos=None, encargado="", codigo=""):
        super().__init__(-radio, -radio, radio*2, radio*2)
        self.setPos(x, y)
        self.nivel = nivel
        self.nombre_estante = nombre_estante
        self.radio = radio
        # Normalizar suplementos: mantener lista de dicts {'nombre','codigo','gaveta'}
        normalized = []
        if suplementos:
            for s in suplementos:
                if isinstance(s, dict):
                    normalized.append({
                        'nombre': s.get('nombre', '') if s.get('nombre', '') is not None else '',
                        'codigo': s.get('codigo', '') if s.get('codigo', '') is not None else '',
                        'gaveta': s.get('gaveta', None) if s.get('gaveta') is not None else None
                    })
                else:
                    # si viene como string antiguo, convertir
                    try:
                        normalized.append({'nombre': str(s), 'codigo': '', 'gaveta': None})
                    except Exception:
                        pass
        self.suplementos = normalized
        self.encargado = encargado
        self.codigo = codigo
        self.setBrush(QColor("#27F5DA"))
        self.setOpacity(0.7)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)

    def actualizar_tamano(self, nuevo_radio):
        self.radio = nuevo_radio
        self.setRect(-nuevo_radio, -nuevo_radio, nuevo_radio*2, nuevo_radio*2)

class MapaView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Zoom mínimo se calculará tras el fitInView para que no se pueda hacer "zoom out"
        # más allá del tamaño de la imagen. Inicialmente None hasta que se fije.
        self.min_zoom_scale = 0.8

    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        current_scale = self.transform().m11()
        new_scale = current_scale * zoom_factor
        # Si se definió un zoom mínimo (por ejemplo tras fitInView), evitar hacer
        # zoom out por debajo de ese valor para que la vista no muestre más área
        # que la imagen.
        if zoom_factor < 1:  # Zoom out
            if self.min_zoom_scale is None or new_scale >= self.min_zoom_scale:
                self.scale(zoom_factor, zoom_factor)
        else:  # Zoom in
            self.scale(zoom_factor, zoom_factor)

        # Mostrar valor real de zoom en consola para depuración
        try:
            print(f"[MapaView] Zoom actual: {self.transform().m11():.3f}  (min: {self.min_zoom_scale})")
        except Exception:
            pass

class VentanaBodega(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agustina Falcon | Planogram System")
        
        if os.path.exists(ICONO_APP):
            self.setWindowIcon(QIcon(ICONO_APP))

        self.nivel_actual = None
        self.puntos_graficos = []
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.pixel_step = 1  # Control de movimiento de píxeles
        
        # --- Inventario Global ---
        self.inventario_global = {}  # {codigo: {'nombre': ..., 'stock': ...}, ...}
        
        # --- Changelog: crear carpeta y archivo de sesión ---
        try:
            self.changelog_dir = os.path.join(DOCS_PATH, "Changelog")
            os.makedirs(self.changelog_dir, exist_ok=True)
            self.session_start = datetime.now()
            fname = self.session_start.strftime("changelog_%Y%m%d_%H%M%S.log")
            self.changelog_path = os.path.join(self.changelog_dir, fname)
            with open(self.changelog_path, "a", encoding="utf-8") as f:
                f.write(f"Session started: {self.session_start.isoformat(sep=' ')}\n")
        except Exception as e:
            print(f"[Changelog] No se pudo crear Changelog: {e}")

        self.cargar_bodegas()
        self.cargar_inventario_global()
        self.init_ui()
        
        # Cargar la primera bodega disponible
        if ARCHIVOS_BODEGA:
            self.cargar_nivel(list(ARCHIVOS_BODEGA.keys())[0])

    def cargar_bodegas(self):
        """Carga la lista de bodegas desde el archivo de configuración"""
        config_path = os.path.join(DOCS_PATH, "bodegas_config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding='utf-8') as f:
                    bodegas_dict = json.load(f)
                    ARCHIVOS_BODEGA.clear()
                    ARCHIVOS_BODEGA.update(bodegas_dict)
                    return
            except:
                pass
        
        # Configuración por defecto si no existe
        ARCHIVOS_BODEGA.clear()
        #ARCHIVOS_BODEGA.update({
        #    "Bodega": "yrz_bodega.json",
        #    "Bodega Nivel II": "yrz_bodega_nivel_ii.json",
        #    "Bodega Nutricion": "yrz_bodega_nutricion.json"
        #})
        self.guardar_config_bodegas()

    def guardar_config_bodegas(self):
        """Guarda la configuración de bodegas"""
        config_path = os.path.join(DOCS_PATH, "bodegas_config.json")
        try:
            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(ARCHIVOS_BODEGA, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar configuración: {e}")

    def cargar_inventario_global(self):
        """Carga el inventario global de items desde archivo."""
        inventario_path = os.path.join(DOCS_PATH, "inventario_global.json")
        self.inventario_global = {}
        
        if os.path.exists(inventario_path):
            try:
                with open(inventario_path, "r", encoding='utf-8') as f:
                    self.inventario_global = json.load(f)
            except Exception as e:
                print(f"[Inventario] Error al cargar: {e}")
                self.inventario_global = {}
        try:
            self.log_action(f"Inventario global cargado: {len(self.inventario_global)} items")
        except Exception:
            pass

    def guardar_inventario_global(self):
        """Guarda el inventario global de items."""
        inventario_path = os.path.join(DOCS_PATH, "inventario_global.json")
        try:
            with open(inventario_path, "w", encoding='utf-8') as f:
                json.dump(self.inventario_global, f, indent=4, ensure_ascii=False)
            try:
                self.log_action(f"Inventario global guardado: {len(self.inventario_global)} items")
            except Exception:
                pass
        except Exception as e:
            print(f"[Inventario] Error al guardar: {e}")

    def log_action(self, message: str):
        """Registra una acción en el archivo de changelog con timestamp."""
        try:
            ts = datetime.now().isoformat(sep=' ')
            entry = f"[{ts}] {message}\n"
            # Append to changelog file if path exists
            if hasattr(self, 'changelog_path'):
                try:
                    with open(self.changelog_path, 'a', encoding='utf-8') as f:
                        f.write(entry)
                except Exception as e:
                    print(f"[Changelog] Error al escribir: {e}")
            # Also print to console for quick feedback
            print(entry.strip())
        except Exception:
            pass

    def init_ui(self):
        main_layout = QHBoxLayout()
        map_layout = QVBoxLayout()
        
        # --- CONTROLES DE BODEGAS ---
        bodega_ctrl_layout = QHBoxLayout()
        
        self.combo_bodegas = QComboBox()
        self.combo_bodegas.addItems(ARCHIVOS_BODEGA.keys())
        self.combo_bodegas.currentTextChanged.connect(self.cambiar_bodega_combo)
        bodega_ctrl_layout.addWidget(QLabel("Bodega:"))
        bodega_ctrl_layout.addWidget(self.combo_bodegas)
        
        btn_add_bodega = QPushButton("➕ Agregar")
        btn_add_bodega.clicked.connect(self.agregar_bodega)
        bodega_ctrl_layout.addWidget(btn_add_bodega)
        
        btn_del_bodega = QPushButton("❌ Eliminar")
        btn_del_bodega.clicked.connect(self.eliminar_bodega)
        bodega_ctrl_layout.addWidget(btn_del_bodega)
        
        # --- CONTROLES DE ZOOM (UI) ---
        # Añadir botones visuales para zoom in / zoom out / reset
        btn_zoom_out = QPushButton("➖")
        btn_zoom_out.setFixedSize(34, 34)
        btn_zoom_out.setToolTip("Zoom out")
        btn_zoom_out.clicked.connect(self.zoom_out)

        btn_zoom_reset = QPushButton("⤢")
        btn_zoom_reset.setFixedSize(34, 34)
        btn_zoom_reset.setToolTip("Ajustar al tamaño de la imagen")
        btn_zoom_reset.clicked.connect(self.zoom_reset)

        btn_zoom_in = QPushButton("➕")
        btn_zoom_in.setFixedSize(34, 34)
        btn_zoom_in.setToolTip("Zoom in")
        btn_zoom_in.clicked.connect(self.zoom_in)

        # Agrupar a la derecha del control de bodegas
        bodega_ctrl_layout.addStretch()
        bodega_ctrl_layout.addWidget(btn_zoom_out)
        bodega_ctrl_layout.addWidget(btn_zoom_reset)
        bodega_ctrl_layout.addWidget(btn_zoom_in)

        map_layout.addLayout(bodega_ctrl_layout)

        # --- BÚSQUEDA DE SUPLEMENTOS ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar suplemento...")
        self.search_input.setCompleter(self.completer)
        self.search_input.returnPressed.connect(self.buscar_suplemento)
        search_layout.addWidget(self.search_input)
        
        btn_search = QPushButton("🔍")
        btn_search.clicked.connect(self.buscar_suplemento)
        search_layout.addWidget(btn_search)
        # Campo para buscar por código
        self.search_code_input = QLineEdit()
        self.search_code_input.setPlaceholderText("Buscar código (ej. 0000821)")
        btn_search_code = QPushButton("🔎 Código")
        btn_search_code.clicked.connect(self.buscar_por_codigo)
        search_layout.addWidget(self.search_code_input)
        search_layout.addWidget(btn_search_code)
        map_layout.addLayout(search_layout)

        # --- VISTA GRÁFICA ---
        self.scene = QGraphicsScene()
        self.view = MapaView(self.scene)
        map_layout.addWidget(self.view)
        
        # --- PANEL LATERAL CON PESTAÑAS ---
        self.tab_widget = QTabWidget()
        
        # TAB 1: ESTANTE
        tab_estante = QWidget()
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(5, 5, 5, 5)  # Márgenes más pequeños para aprovechar espacio
        self.lbl_estante = QLabel("Seleccione un estante")
        self.lbl_estante.setStyleSheet("font-weight: bold; font-size: 14px;")
        # Botón de configuración (ruedita) para abrir modal de edición del estante
        btn_config = QPushButton("⚙️")
        btn_config.setFixedSize(34, 34)
        btn_config.clicked.connect(self.abrir_config_estante)
        header_row = QHBoxLayout()
        header_row.addWidget(self.lbl_estante)
        header_row.addStretch()
        header_row.addWidget(btn_config)
        detail_layout.addLayout(header_row)

        self.lista_suplementos = QListWidget()
        self.lista_suplementos.setMinimumHeight(150)
        self.lista_suplementos.setMaximumHeight(280)  # Limitar expansión máxima
        
        btn_add_sup = QPushButton("+ Suplemento")
        btn_add_sup.clicked.connect(self.agregar_suplemento)
        
        btn_edit_sup = QPushButton("✏️ Editar Item")
        btn_edit_sup.clicked.connect(self.editar_suplemento)
        
        btn_move_sup = QPushButton("➡️ Mover Item")
        btn_move_sup.clicked.connect(self.mover_suplemento)
        
        btn_del_sup = QPushButton("🗑️ Eliminar Item")
        btn_del_sup.clicked.connect(self.eliminar_suplemento)
        
        detail_layout.addWidget(self.lista_suplementos)
        detail_layout.addWidget(btn_add_sup)
        
        sup_buttons_layout = QHBoxLayout()
        sup_buttons_layout.addWidget(btn_edit_sup)
        sup_buttons_layout.addWidget(btn_move_sup)
        sup_buttons_layout.addWidget(btn_del_sup)
        detail_layout.addLayout(sup_buttons_layout)
        detail_layout.addSpacing(8)  # Reducido de 15
        
        # --- CONTROL DE MOVIMIENTO DE ESTANTES ---
        detail_layout.addWidget(QLabel("<b>Control de movimientos | Estantes</b>"))

        # Paso selector (combo) y d-pad (control direccional)
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("Pasos (px):"))
        self.combo_steps = QComboBox()
        self.combo_steps.addItems(["1px", "2px", "4px", "8px", "10px"])
        self.combo_steps.currentTextChanged.connect(self.cambiar_paso)
        step_layout.addWidget(self.combo_steps)
        detail_layout.addLayout(step_layout)

        # D-Pad widget (3x3 grid) con estilo circular para botones direccionales
        dpad = QWidget()
        dpad_layout = QHBoxLayout()
        dpad.setLayout(dpad_layout)

        grid = QWidget()
        from PyQt6.QtWidgets import QGridLayout
        grid_layout = QGridLayout()
        grid.setLayout(grid_layout)
        grid_layout.setSpacing(6)

        # Crear botones direccionales y etiqueta central
        btn_up = QPushButton("🡩")
        btn_left = QPushButton("🡨")
        btn_right = QPushButton(" 🡪 ")
        btn_down = QPushButton(" 🡫 ")
        # Central button: al pulsarla cambia el valor de paso
        self.step_display = QPushButton(f"{self.pixel_step}px")
        self.step_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.step_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Estilos para que se vean como en el diseño (anillo rosa) - tamaños reducidos
        btn_style = (
            "QPushButton{"
            "width:36px; height:36px; font-size:14px; border-radius:8px; "
            "border:2px solid #A110B5; background: #2A2A2B; color: #A110B5; }"
            "QPushButton:hover{ border-color: #A110B5; background-color: #2A2A2B; transition: 0.3s ease-in-out; transform: scale(1.1);}"
        )
        center_style = (
            "QPushButton{ width:44px; height:44px; font-weight:bold; border-radius:8px; "
            "border:2px solid #A110B5; background: #2A2A2B; color: #A110B5; font-size:14px; }"
        )

        for btn in (btn_up, btn_left, btn_right, btn_down):
            btn.setStyleSheet(btn_style)

        self.step_display.setStyleSheet(center_style)
        self.step_display.clicked.connect(self.cycle_step)

        # Conectar acciones
        btn_up.clicked.connect(lambda: self.mover_estante(0, -self.pixel_step))
        btn_down.clicked.connect(lambda: self.mover_estante(0, self.pixel_step))
        btn_left.clicked.connect(lambda: self.mover_estante(-self.pixel_step, 0))
        btn_right.clicked.connect(lambda: self.mover_estante(self.pixel_step, 0))

        # Colocar en grid 3x3 (posiciones vacías se rellenan con spacers)
        grid_layout.addWidget(QWidget(), 0, 0)
        grid_layout.addWidget(btn_up, 0, 1)
        grid_layout.addWidget(QWidget(), 0, 2)
        grid_layout.addWidget(btn_left, 1, 0)
        grid_layout.addWidget(self.step_display, 1, 1)
        grid_layout.addWidget(btn_right, 1, 2)
        grid_layout.addWidget(QWidget(), 2, 0)
        grid_layout.addWidget(btn_down, 2, 1)
        grid_layout.addWidget(QWidget(), 2, 2)

        dpad_layout.addWidget(grid)
        detail_layout.addWidget(dpad)
        detail_layout.addSpacing(8)  # Reducido de 15
        
        line = QWidget(); line.setFixedHeight(1); line.setStyleSheet("background-color: #ccc;")  # Reducido de 2
        detail_layout.addWidget(line)
        
        detail_layout.addWidget(QLabel("<b>Herramientas de Datos</b>"))
        
        btn_export = QPushButton("📤 Exportar JSON...")
        btn_export.clicked.connect(self.exportar_datos)
        detail_layout.addWidget(btn_export)
        
        btn_import = QPushButton("📥 Importar JSON...")
        btn_import.clicked.connect(self.importar_datos)
        detail_layout.addWidget(btn_import)
        
        detail_layout.addStretch()
        
        btn_del = QPushButton("Eliminar Estante")
        btn_del.setStyleSheet("background-color: #A110B5;")
        btn_del.clicked.connect(self.eliminar_estante)
        detail_layout.addWidget(btn_del)
        
        tab_estante.setLayout(detail_layout)
        self.tab_widget.addTab(tab_estante, "📍 Estante")
        
        # TAB 2: INVENTARIO GENERAL
        tab_inventario = QWidget()
        inv_layout = QVBoxLayout()
        inv_layout.setContentsMargins(5, 5, 5, 5)  # Márgenes más pequeños para aprovechar espacio
        
        inv_layout.addWidget(QLabel("<b>Inventario General</b>"))
        inv_layout.addWidget(QLabel("Items disponibles para asignar a repisas"))
        
        self.lista_inventario = QListWidget()
        self.lista_inventario.setMinimumHeight(150)
        self.lista_inventario.setMaximumHeight(300)  # Limitar expansión máxima
        inv_layout.addWidget(self.lista_inventario)
        
        btn_inv_add = QPushButton("+ Nuevo Item")
        btn_inv_add.clicked.connect(self.agregar_item_inventario)
        inv_layout.addWidget(btn_inv_add)
        
        btn_inv_edit = QPushButton("✏️ Editar Item")
        btn_inv_edit.clicked.connect(self.editar_item_inventario)
        inv_layout.addWidget(btn_inv_edit)
        
        btn_inv_del = QPushButton("🗑️ Eliminar Item")
        btn_inv_del.setStyleSheet("background-color: #A110B5;")
        btn_inv_del.clicked.connect(self.eliminar_item_inventario)
        inv_layout.addWidget(btn_inv_del)
        
        inv_layout.addSpacing(10)
        
        btn_inv_refresh = QPushButton("🔄 Actualizar")
        btn_inv_refresh.setStyleSheet("background-color: #1a7a5a;")
        btn_inv_refresh.clicked.connect(self.actualizar_lista_inventario)
        inv_layout.addWidget(btn_inv_refresh)
        
        tab_inventario.setLayout(inv_layout)
        self.tab_widget.addTab(tab_inventario, "📦 Inventario")
        
        # Agregar tab widget al layout principal
        container_map = QWidget(); container_map.setLayout(map_layout)
        container_map.setMinimumWidth(800)
        
        main_layout.addWidget(container_map, 1)
        main_layout.addWidget(self.tab_widget, 0)
        self.tab_widget.setFixedWidth(280)
        self.tab_widget.setMinimumHeight(400)  # Altura mínima para evitar que se comprima
        
        cw = QWidget(); cw.setLayout(main_layout)
        self.setCentralWidget(cw)
        self.setMinimumSize(1200, 700)  # Tamaño mínimo para que no se comprima
        self.scene.mousePressEvent = self.evento_click_escena
        
        # Cargar inventario en la UI al inicio
        self.actualizar_lista_inventario()

    def obtener_ruta_archivo(self, nivel):
        """Obtiene la ruta completa del archivo JSON"""
        if nivel and nivel in ARCHIVOS_BODEGA:
            return os.path.join(DOCS_PATH, ARCHIVOS_BODEGA[nivel])
        return ""

    def obtener_ruta_imagen(self, nivel):
        """Obtiene la ruta de la imagen de la bodega"""
        return os.path.join(GRAPHICS_PATH, f"{nivel}.png")

    def cambiar_bodega_combo(self, nombre_bodega):
        """Cambia de bodega desde el combo box"""
        if nombre_bodega and nombre_bodega != self.nivel_actual:
            self.cargar_nivel(nombre_bodega)

    def cambiar_paso(self, valor):
        """Cambia el paso de movimiento en píxeles"""
        self.pixel_step = int(valor.replace("px", ""))
        # Actualizar la etiqueta central del d-pad si existe
        try:
            self.step_display.setText(f"{self.pixel_step}px")
        except Exception:
            pass

    def cycle_step(self):
        """Cicla al siguiente valor de paso en el combo cuando se pulsa el botón central."""
        try:
            # Obtener lista de opciones del combo
            items = [self.combo_steps.itemText(i) for i in range(self.combo_steps.count())]
            current_text = f"{self.pixel_step}px"
            if current_text in items:
                idx = items.index(current_text)
                next_idx = (idx + 1) % len(items)
            else:
                next_idx = 0
            # Cambiar el combo (esto disparará cambiar_paso automáticamente)
            self.combo_steps.setCurrentIndex(next_idx)
        except Exception:
            pass

    def cargar_nivel(self, nivel):
        """Carga el nivel/bodega especificado"""
        # Guardar datos de la bodega actual antes de cambiar
        if self.puntos_graficos and self.nivel_actual and self.nivel_actual in ARCHIVOS_BODEGA:
            try:
                self.guardar_datos_a_disco(self.nivel_actual)
            except Exception as e:
                print(f"Error al guardar datos del nivel anterior: {e}")

        self.nivel_actual = nivel
        self.scene.clear()
        self.puntos_graficos = []
        
        # Actualizar combo box
        if self.combo_bodegas.currentText() != nivel:
            self.combo_bodegas.blockSignals(True)
            self.combo_bodegas.setCurrentText(nivel)
            self.combo_bodegas.blockSignals(False)
        
        # Cargar imagen
        ruta_img = self.obtener_ruta_imagen(nivel)
        if os.path.exists(ruta_img):
            pixmap = QPixmap(ruta_img)
            if not pixmap.isNull():
                self.scene.addPixmap(pixmap)
                rect = QRectF(pixmap.rect())
                self.scene.setSceneRect(rect)
                self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
                # Después de ajustar la vista al rectángulo de la imagen, fijar
                # el zoom mínimo para evitar hacer zoom out por debajo del
                # tamaño mostrado por la imagen.
                try:
                    current_scale = self.view.transform().m11()
                    self.view.min_zoom_scale = current_scale
                except Exception:
                    # En caso de que algo falle, dejar min_zoom_scale como None
                    self.view.min_zoom_scale = None
        else:
            self.scene.addText(f"Imagen no encontrada:\n{ruta_img}")

        # Cargar datos
        ruta_json = self.obtener_ruta_archivo(nivel)
        datos = []
        if os.path.exists(ruta_json):
            try:
                with open(ruta_json, "r", encoding='utf-8') as f:
                    datos = json.load(f)
            except Exception as e:
                print(f"Error al cargar {nivel}: {e}")

        if isinstance(datos, list):
            for p_data in datos:
                self.crear_punto_visual(
                    p_data.get('x', 0),
                    p_data.get('y', 0),
                    p_data.get('nombre', ''),
                    p_data.get('radio', 15),
                    p_data.get('suplementos', []),
                    p_data.get('encargado', ''),
                    p_data.get('codigo', '')
                )
        
        self.actualizar_sugerencias_globales()
        self.lbl_estante.setText("Seleccione un estante")
        self.actualizar_lista_inventario()

    def guardar_datos_a_disco(self, nivel):
        """Guarda los datos en disco"""
        if not nivel or nivel not in ARCHIVOS_BODEGA:
            print(f"Error: Nivel '{nivel}' no válido para guardar")
            return
            
        ruta_json = self.obtener_ruta_archivo(nivel)
        if not ruta_json:
            print(f"Error: No se pudo obtener ruta para el nivel '{nivel}'")
            return
            
        lista_puntos = [
            {
                'x': p.pos().x(),
                'y': p.pos().y(),
                'nombre': p.nombre_estante,
                'radio': p.radio,
                'suplementos': p.suplementos,
                'encargado': getattr(p, 'encargado', ''),
                'codigo': getattr(p, 'codigo', '')
            }
            for p in self.puntos_graficos
        ]
        try:
            with open(ruta_json, "w", encoding='utf-8') as f:
                json.dump(lista_puntos, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar: {e}")

    def generar_codigo(self):
        """Genera un código numérico único de 7 dígitos para un estante."""
        max_val = 0
        # revisar puntos actuales
        for p in self.puntos_graficos:
            try:
                c = int(str(getattr(p, 'codigo', '')).lstrip('0') or 0)
                if c > max_val:
                    max_val = c
            except Exception:
                pass
        # revisar datos en disco para este nivel
        ruta_json = self.obtener_ruta_archivo(self.nivel_actual)
        if os.path.exists(ruta_json):
            try:
                with open(ruta_json, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    if isinstance(datos, list):
                        for item in datos:
                            try:
                                c = int(str(item.get('codigo', '')).lstrip('0') or 0)
                                if c > max_val:
                                    max_val = c
                            except Exception:
                                pass
            except Exception:
                pass
        nuevo = max_val + 1
        codigo = f"{nuevo:07d}"
        try:
            # registrar generación de código
            self.log_action(f"Generado código {codigo} para nuevo estante")
        except Exception:
            pass
        return codigo

    def agregar_bodega(self):
        """Agrega una nueva bodega"""
        nombre, ok = QInputDialog.getText(self, "Nueva Bodega", "Nombre de la bodega:")
        if not ok or not nombre:
            return
        
        if nombre in ARCHIVOS_BODEGA:
            QMessageBox.warning(self, "Error", "Esta bodega ya existe")
            return
        
        # Seleccionar imagen
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen del plano", "", "PNG Files (*.png)"
        )
        if not file_path:
            return
        
        # Copiar imagen a graphics
        nombre_img = f"{nombre}.png"
        ruta_dest = os.path.join(GRAPHICS_PATH, nombre_img)
        
        try:
            shutil.copy2(file_path, ruta_dest)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo copiar la imagen: {e}")
            return
        
        # Agregar a configuración
        nombre_json = f"yrz_{nombre.lower().replace(' ', '_')}.json"
        ARCHIVOS_BODEGA[nombre] = nombre_json
        self.guardar_config_bodegas()
        
        # Actualizar combo
        self.combo_bodegas.blockSignals(True)
        self.combo_bodegas.addItem(nombre)
        self.combo_bodegas.setCurrentText(nombre)
        self.combo_bodegas.blockSignals(False)
        
        # Cargar la nueva bodega
        self.cargar_nivel(nombre)
        QMessageBox.information(self, "Éxito", f"Bodega '{nombre}' creada")
        try:
            self.log_action(f"Agregada bodega '{nombre}' con imagen {nombre_img} y json {nombre_json}")
        except Exception:
            pass

    def eliminar_bodega(self):
        """Elimina una bodega"""
        if not ARCHIVOS_BODEGA:
            QMessageBox.warning(self, "Error", "No hay bodegas para eliminar")
            return
        
        nombre = self.combo_bodegas.currentText()
        if not nombre:
            return
        
        respuesta = QMessageBox.question(
            self, "Confirmar", 
            f"¿Eliminar bodega '{nombre}' (se mantenienen los datos)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            # Guardar datos antes de eliminar la referencia
            if self.puntos_graficos and self.nivel_actual == nombre:
                try:
                    self.guardar_datos_a_disco(self.nivel_actual)
                except Exception as e:
                    print(f"Error al guardar datos antes de eliminar bodega: {e}")
            
            # Eliminar de configuración
            del ARCHIVOS_BODEGA[nombre]
            self.guardar_config_bodegas()
            
            # Actualizar combo
            self.combo_bodegas.blockSignals(True)
            self.combo_bodegas.removeItem(self.combo_bodegas.currentIndex())
            self.combo_bodegas.blockSignals(False)
            
            # Cargar otra bodega o limpiar vista
            if ARCHIVOS_BODEGA:
                self.cargar_nivel(list(ARCHIVOS_BODEGA.keys())[0])
            else:
                # Si no hay más bodegas, limpiar la vista
                self.nivel_actual = None
                self.scene.clear()
                self.puntos_graficos = []
                self.lbl_estante.setText("No hay bodegas disponibles")
                self.lista_suplementos.clear()
            
            QMessageBox.information(self, "Éxito", f"Bodega '{nombre}' eliminada")
            try:
                self.log_action(f"Eliminada bodega '{nombre}' de la configuración")
            except Exception:
                pass

    def exportar_datos(self):
        """Exporta los datos de la bodega actual"""
        self.guardar_datos_a_disco(self.nivel_actual)
        ruta_json_origen = self.obtener_ruta_archivo(self.nivel_actual)
        
        if not os.path.exists(ruta_json_origen):
            QMessageBox.warning(self, "Exportar", "No hay datos grabados")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Bodega como...", f"Copia_{ARCHIVOS_BODEGA[self.nivel_actual]}", "JSON Files (*.json)")
        if file_path:
            shutil.copy2(ruta_json_origen, file_path)
            QMessageBox.information(self, "Exportar", "Archivo exportado con éxito.")
            try:
                self.log_action(f"Exportado JSON de '{self.nivel_actual}' a '{file_path}'")
            except Exception:
                pass

    def importar_datos(self):
        """Importa datos de un archivo JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar JSON para importar", "", "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding='utf-8') as f:
                contenido = json.load(f)
            
            datos_finales = []
            
            if isinstance(contenido, dict):
                opciones_en_json = [k for k in contenido.keys() if k in ARCHIVOS_BODEGA]
                if opciones_en_json:
                    selecc, ok = QInputDialog.getItem(
                        self, "Importar", 
                        "Se detectó un archivo múltiple. ¿Qué bodega extraer?", 
                        opciones_en_json, 0, False
                    )
                    if ok:
                        datos_finales = contenido[selecc]
                    else:
                        return
                else:
                    QMessageBox.warning(self, "Error", "Claves JSON no válidas")
                    return
            
            elif isinstance(contenido, list):
                datos_finales = contenido
            
            opciones = list(ARCHIVOS_BODEGA.keys())
            destino, ok = QInputDialog.getItem(
                self, "Importar", 
                "¿En qué bodega guardar estos datos?", 
                opciones, 0, False
            )
            
            if ok and destino:
                ruta_destino = self.obtener_ruta_archivo(destino)
                with open(ruta_destino, "w", encoding='utf-8') as f:
                    json.dump(datos_finales, f, indent=4, ensure_ascii=False)
                
                if destino == self.nivel_actual:
                    self.cargar_nivel(destino)
                QMessageBox.information(self, "Éxito", f"Datos importados en {destino}")
                try:
                    self.log_action(f"Importados datos en bodega '{destino}' desde '{file_path}'")
                except Exception:
                    pass

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar: {str(e)}")
    def evento_click_escena(self, event):
        """Maneja eventos de clic en la escena"""
        pos = event.scenePos()
        item = self.scene.itemAt(pos, self.view.transform())
        
        if event.button() == Qt.MouseButton.RightButton:
            if isinstance(item, EstantePoint):
                nom, ok = QInputDialog.getText(
                    self, "Editar", "Nombre:", text=item.nombre_estante
                )
                if ok: 
                    item.nombre_estante = nom
                    self.lbl_estante.setText(f"Estante: {nom}")
                    self.guardar_datos_a_disco(self.nivel_actual)
            else:
                if self.scene.sceneRect().contains(pos):
                    nom, ok = QInputDialog.getText(self, "Nuevo", "Nombre Estante:")
                    if ok and nom:
                        encargado, ok2 = QInputDialog.getText(self, "Encargado", "Nombre encargado (opcional):")
                        if not ok2:
                            encargado = ""
                        codigo, ok3 = QInputDialog.getText(self, "Código (opcional)", "Código numérico (dejar vacío para autogenerar):")
                        if not ok3:
                            codigo = ""
                        if not codigo:
                            codigo = self.generar_codigo()
                        self.crear_punto_visual(pos.x(), pos.y(), nom, 15, [], encargado, codigo)
                        try:
                            self.log_action(f"Creado estante '{nom}' en ({pos.x():.1f},{pos.y():.1f}) codigo={codigo} encargado='{encargado}' nivel={self.nivel_actual}")
                        except Exception:
                            pass
                        self.guardar_datos_a_disco(self.nivel_actual)
        
        elif event.button() == Qt.MouseButton.LeftButton:
            if isinstance(item, EstantePoint):
                self.mostrar_detalles(item)

    def crear_punto_visual(self, x, y, nombre, radio, suplementos, encargado="", codigo=""):
        """Crea un punto visual en la escena. """
        punto = EstantePoint(x, y, self.nivel_actual, nombre, radio, suplementos, encargado, codigo)
        self.scene.addItem(punto)
        self.puntos_graficos.append(punto)
        try:
            print(f"[CrearPunto] '{nombre}' creado en ({float(x):.1f}, {float(y):.1f}) codigo={codigo} encargado='{encargado}' nivel={self.nivel_actual}")
        except Exception:
            pass
        try:
            self.log_action(f"CrearPunto: '{nombre}' en ({float(x):.1f},{float(y):.1f}) codigo={codigo} encargado='{encargado}'")
        except Exception:
            pass

    def mostrar_detalles(self, punto):
        """Muestra los detalles del estante seleccionado"""
        self.estante_seleccionado = punto
        detalles = f"Estante: {punto.nombre_estante}"
        if getattr(punto, 'encargado', ''):
            detalles += f"\nEncargado: {punto.encargado}"
        self.lbl_estante.setText(detalles)
        # Mostrar items con formato: Codigo | Nombre | Gaveta | Stock
        self.lista_suplementos.clear()
        for s in getattr(punto, 'suplementos', []):
            if isinstance(s, dict):
                code = s.get('codigo', '')
                gaveta = s.get('gaveta', None)
                # Buscar en inventario global
                if code in self.inventario_global:
                    nombre = self.inventario_global[code]['nombre']
                    stock = self.inventario_global[code]['stock']
                    gaveta_str = f"Gaveta {gaveta}" if gaveta is not None else "Sin gaveta"
                    display = f"{code} | {nombre} | {gaveta_str} | {stock}"
                else:
                    # Item no existe en inventario global (posible dato antiguo)
                    nombre = s.get('nombre', '')
                    gaveta_str = f"Gaveta {gaveta}" if gaveta is not None else "Sin gaveta"
                    display = f"{code} | {nombre} | {gaveta_str} | 0"
            else:
                # Formato antiguo (string)
                display = str(s)
            self.lista_suplementos.addItem(display)
        try:
            self.log_action(f"Seleccionado estante '{punto.nombre_estante}' encargado={getattr(punto,'encargado','')}")
        except Exception:
            pass
        # Actualizar lista de inventario automáticamente
        self.actualizar_lista_inventario()

    def agregar_suplemento(self):
        """Agrega un suplemento al estante seleccionado con búsqueda de sugerencias y gaveta."""
        if not hasattr(self, 'estante_seleccionado'):
            QMessageBox.warning(self, "Error", "Selecciona un estante primero")
            return
        
        # Crear diálogo personalizado con búsqueda y sugerencias
        dlg = QDialog(self)
        dlg.setWindowTitle("Agregar Item a Estante")
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout(dlg)
        
        # --- Campo de búsqueda ---
        layout.addWidget(QLabel("Buscar o crear item:"))
        search_input = QLineEdit()
        search_input.setPlaceholderText("Escribe para buscar entre items existentes...")
        layout.addWidget(search_input)
        
        # --- Lista de sugerencias ---
        layout.addWidget(QLabel("Sugerencias:"))
        lista_items = QListWidget()
        lista_items.setMaximumHeight(200)
        layout.addWidget(lista_items)
        
        # --- Campo de gaveta ---
        layout.addWidget(QLabel("Número de gaveta (opcional):"))
        gaveta_input = QSpinBox()
        gaveta_input.setMinimum(0)
        gaveta_input.setMaximum(999)
        gaveta_input.setValue(0)
        gaveta_input.setToolTip("0 = sin gaveta asignada")
        layout.addWidget(gaveta_input)
        
        # --- Botones ---
        btn_layout = QHBoxLayout()
        btn_agregar = QPushButton("Agregar")
        btn_cancelar = QPushButton("Cancelar")
        btn_layout.addWidget(btn_agregar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        # Variables locales
        items_dict = {}  # {display: (codigo, nombre)}
        
        def actualizar_sugerencias(text):
            """Actualiza la lista de sugerencias según el texto ingresado"""
            items_dict.clear()
            lista_items.clear()
            
            text_lower = text.lower().strip()
            
            # Opción para crear nuevo item
            if text and not any(c in self.inventario_global for c, _ in items_dict.values()):
                lista_items.addItem("[NUEVO ITEM]")
            
            # Buscar en inventario global
            for cod in sorted(self.inventario_global.keys()):
                data = self.inventario_global[cod]
                nombre = data.get('nombre', '')
                stock = data.get('stock', 0)
                
                # Mostrar todos si está vacío, o filtrar por nombre/código
                if not text_lower or cod.startswith(text_lower) or nombre.lower().startswith(text_lower) or text_lower in nombre.lower():
                    display = f"{cod} | {nombre} | Stock: {stock}"
                    items_dict[display] = (cod, nombre)
                    lista_items.addItem(display)
        
        def agregar_item():
            """Agrega el item seleccionado al estante"""
            row = lista_items.currentRow()
            if row < 0:
                QMessageBox.warning(dlg, "Error", "Selecciona un item de la lista")
                return
            
            item_text = lista_items.item(row).text()
            gaveta_val = gaveta_input.value()
            
            if item_text == "[NUEVO ITEM]":
                # Crear nuevo item
                nombre, ok1 = QInputDialog.getText(dlg, "Nuevo Item", "Nombre del item:")
                if not ok1 or not nombre:
                    return
                
                while True:
                    codigo, ok2 = QInputDialog.getText(dlg, "Nuevo Item", "Código numérico:")
                    if not ok2:
                        return
                    if codigo.isdigit():
                        break
                    else:
                        QMessageBox.warning(dlg, "Código inválido", "El código debe contener solo dígitos.")
                
                if codigo in self.inventario_global:
                    QMessageBox.warning(dlg, "Error", f"El código {codigo} ya existe")
                    return
                
                while True:
                    stock_str, ok3 = QInputDialog.getText(dlg, "Nuevo Item", "Stock inicial:")
                    if not ok3:
                        return
                    if stock_str.isdigit():
                        break
                    else:
                        QMessageBox.warning(dlg, "Stock inválido", "El stock debe ser un número.")
                
                self.inventario_global[codigo] = {
                    'nombre': nombre.strip(),
                    'stock': int(stock_str)
                }
                self.guardar_inventario_global()
                sup_code = codigo
                
                try:
                    self.log_action(f"Nuevo item en inventario: {codigo} | {nombre} | Stock: {stock_str}")
                except Exception:
                    pass
            else:
                # Usar item existente
                sup_code = items_dict[item_text][0]
            
            # Verificar que no esté duplicado (por código)
            codigos_existentes = [s.get('codigo', '') if isinstance(s, dict) else '' for s in self.estante_seleccionado.suplementos]
            if sup_code in codigos_existentes:
                QMessageBox.information(dlg, "Info", f"El item {sup_code} ya está en este estante")
                return
            
            # Agregar al estante con gaveta
            nuevo = {
                'nombre': self.inventario_global[sup_code]['nombre'],
                'codigo': sup_code,
                'gaveta': gaveta_val if gaveta_val > 0 else None
            }
            self.estante_seleccionado.suplementos.append(nuevo)
            self.guardar_datos_a_disco(self.nivel_actual)
            self.mostrar_detalles(self.estante_seleccionado)
            
            try:
                gaveta_info = f"gaveta={gaveta_val}" if gaveta_val > 0 else "sin gaveta"
                self.log_action(f"Agregado item '{nuevo['nombre']}' (código {sup_code}) {gaveta_info} a estante '{self.estante_seleccionado.nombre_estante}'")
            except Exception:
                pass
            
            dlg.accept()
        
        # Conectar eventos
        search_input.textChanged.connect(actualizar_sugerencias)
        btn_agregar.clicked.connect(agregar_item)
        btn_cancelar.clicked.connect(dlg.reject)
        
        # Mostrar sugerencias iniciales
        actualizar_sugerencias("")
        
        dlg.exec()

    def editar_suplemento(self):
        """Edita nombre, stock y gaveta del item."""
        if not hasattr(self, 'estante_seleccionado'):
            QMessageBox.warning(self, "Error", "Selecciona un estante primero")
            return
        row = self.lista_suplementos.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un item para editar")
            return
        try:
            sup_obj = self.estante_seleccionado.suplementos[row]
            if not isinstance(sup_obj, dict):
                QMessageBox.warning(self, "Error", "Formato antiguo no editable")
                return
            code = sup_obj.get('codigo', '')
            if code not in self.inventario_global:
                QMessageBox.warning(self, "Error", f"Item {code} no existe en inventario global")
                return
        except Exception:
            QMessageBox.warning(self, "Error", "No se pudo leer el item seleccionado")
            return

        item_data = self.inventario_global[code]
        
        # Diálogo de edición
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Editar Item - {code}")
        form = QFormLayout(dlg)
        
        name_input = QLineEdit(item_data.get('nombre', ''))
        stock_input = QSpinBox()
        stock_input.setMinimum(0)
        stock_input.setValue(item_data.get('stock', 0))
        gaveta_input = QSpinBox()
        gaveta_input.setMinimum(0)
        gaveta_input.setMaximum(999)
        gaveta_input.setValue(sup_obj.get('gaveta', 0) if sup_obj.get('gaveta') is not None else 0)
        gaveta_input.setToolTip("0 = sin gaveta asignada")
        
        form.addRow("Nombre del item:", name_input)
        form.addRow("Stock:", stock_input)
        form.addRow("Gaveta:", gaveta_input)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Aplicar")
        cancel_btn = QPushButton("Cancelar")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        form.addRow(btn_layout)
        
        def aplicar():
            new_name = name_input.text().strip()
            new_stock = stock_input.value()
            new_gaveta = gaveta_input.value() if gaveta_input.value() > 0 else None
            
            self.inventario_global[code]['nombre'] = new_name
            self.inventario_global[code]['stock'] = new_stock
            sup_obj['nombre'] = new_name
            sup_obj['gaveta'] = new_gaveta
            
            self.guardar_inventario_global()
            self.guardar_datos_a_disco(self.nivel_actual)
            self.mostrar_detalles(self.estante_seleccionado)
            
            try:
                gaveta_info = f"gaveta={new_gaveta}" if new_gaveta else "sin gaveta"
                self.log_action(f"Editado item {code}: '{new_name}' | Stock: {new_stock} | {gaveta_info}")
            except Exception:
                pass
            
            dlg.accept()
        
        ok_btn.clicked.connect(aplicar)
        cancel_btn.clicked.connect(dlg.reject)
        
        dlg.exec()

    def abrir_config_estante(self):
        """Abre un modal con opciones: tamaño del radio, cambiar nombre y encargado."""
        if not hasattr(self, 'estante_seleccionado'):
            QMessageBox.warning(self, "Error", "Selecciona un estante primero")
            return

        punto = self.estante_seleccionado
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Configuración - {punto.nombre_estante}")
        form = QFormLayout(dlg)

        name_input = QLineEdit(punto.nombre_estante)
        encargado_input = QLineEdit(getattr(punto, 'encargado', ''))
        radius_input = QSpinBox()
        radius_input.setRange(5, 200)
        radius_input.setValue(int(punto.radio))

        form.addRow("Nombre:", name_input)
        form.addRow("Encargado:", encargado_input)
        form.addRow("Radio (px):", radius_input)

        btns = QHBoxLayout()
        ok = QPushButton("Aplicar")
        cancel = QPushButton("Cancelar")
        btns.addWidget(ok)
        btns.addWidget(cancel)
        form.addRow(btns)

        def aplicar():
            nuevo_nombre = name_input.text().strip()
            nuevo_enc = encargado_input.text().strip()
            nuevo_radio = int(radius_input.value())
            if nuevo_nombre:
                punto.nombre_estante = nuevo_nombre
            punto.encargado = nuevo_enc
            punto.actualizar_tamano(nuevo_radio)
            self.guardar_datos_a_disco(self.nivel_actual)
            self.mostrar_detalles(punto)
            dlg.accept()
            try:
                self.log_action(f"Config estante: '{punto.nombre_estante}' encargado='{punto.encargado}' radio={punto.radio}")
            except Exception:
                pass

        ok.clicked.connect(aplicar)
        cancel.clicked.connect(dlg.reject)

        dlg.exec()

    def mover_suplemento(self):
        """Mueve un item a otro estante"""
        if not hasattr(self, 'estante_seleccionado'):
            QMessageBox.warning(self, "Error", "Selecciona un estante primero")
            return
        # Usar la fila seleccionada para identificar el item
        row = self.lista_suplementos.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un item para mover")
            return
        try:
            item_obj = self.estante_seleccionado.suplementos[row]
            if not isinstance(item_obj, dict):
                QMessageBox.warning(self, "Error", "Formato antiguo no movible")
                return
            code = item_obj.get('codigo', '')
            sup_display_name = self.inventario_global[code]['nombre'] if code in self.inventario_global else code
        except Exception:
            QMessageBox.warning(self, "Error", "No se pudo leer el item seleccionado")
            return
        estantes_disponibles = [
            p.nombre_estante for p in self.puntos_graficos 
            if p != self.estante_seleccionado
        ]
        
        if not estantes_disponibles:
            QMessageBox.warning(self, "Error", "No hay otros estantes disponibles")
            return
        
        # Diálogo con búsqueda
        estante_destino, ok = QInputDialog.getItem(
            self, "Mover Item",
            f"¿A qué estante mover '{sup_display_name}'?\n(Puedes escribir para buscar)",
            estantes_disponibles, 0, True
        )

        if ok and estante_destino:
            # remover por índice
            try:
                removed = self.estante_seleccionado.suplementos.pop(row)
            except Exception:
                QMessageBox.warning(self, "Error", "No se pudo remover el item")
                return

            for punto in self.puntos_graficos:
                if punto.nombre_estante == estante_destino:
                    # evitar duplicados por código
                    exists = False
                    for s in punto.suplementos:
                        if isinstance(s, dict) and isinstance(removed, dict) and s.get('codigo','') == removed.get('codigo',''):
                            exists = True
                            break
                    if not exists:
                        punto.suplementos.append(removed)
                    break

            self.guardar_datos_a_disco(self.nivel_actual)
            self.mostrar_detalles(self.estante_seleccionado)
            QMessageBox.information(self, "Éxito", f"'{sup_display_name}' movido a '{estante_destino}'")
            try:
                self.log_action(f"Movido item '{sup_display_name}' ({code}) de '{self.estante_seleccionado.nombre_estante}' a '{estante_destino}'")
            except Exception:
                pass

    def eliminar_suplemento(self):
        """Elimina un item del estante seleccionado (el item sigue existiendo en el inventario global)"""
        if not hasattr(self, 'estante_seleccionado'):
            QMessageBox.warning(self, "Error", "Selecciona un estante primero")
            return
        
        row = self.lista_suplementos.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un item para eliminar")
            return
        
        try:
            item_obj = self.estante_seleccionado.suplementos[row]
            if not isinstance(item_obj, dict):
                QMessageBox.warning(self, "Error", "Formato antiguo no eliminable")
                return
            
            code = item_obj.get('codigo', '')
            sup_display_name = self.inventario_global[code]['nombre'] if code in self.inventario_global else code
            
            # Confirmar eliminación
            reply = QMessageBox.question(
                self, "Confirmar eliminación",
                f"¿Desasignar '{sup_display_name}' de este estante?\n\n(El item seguirá existiendo en el inventario global)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.estante_seleccionado.suplementos.pop(row)
                self.guardar_datos_a_disco(self.nivel_actual)
                self.mostrar_detalles(self.estante_seleccionado)
                try:
                    self.log_action(f"Desasignado item '{sup_display_name}' ({code}) de estante '{self.estante_seleccionado.nombre_estante}'")
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo eliminar el item: {str(e)}")

    def mover_estante(self, dx, dy):
        """Mueve el estante seleccionado"""
        if not hasattr(self, 'estante_seleccionado'):
            QMessageBox.warning(self, "Error", "Selecciona un estante primero")
            return
        
        pos_actual = self.estante_seleccionado.pos()
        # Crear QPointF (o pasar floats) para setPos en lugar de QPoint
        nueva_x = float(pos_actual.x() + dx)
        nueva_y = float(pos_actual.y() + dy)
        try:
            print(f"[MoverEstante] '{getattr(self.estante_seleccionado, 'nombre_estante', '')}' de ({pos_actual.x():.1f},{pos_actual.y():.1f}) a ({nueva_x:.1f},{nueva_y:.1f})")
        except Exception:
            pass
        nueva_pos = QPointF(nueva_x, nueva_y)
        self.estante_seleccionado.setPos(nueva_pos)
        self.guardar_datos_a_disco(self.nivel_actual)
        try:
            self.log_action(f"MoverEstante: '{getattr(self.estante_seleccionado, 'nombre_estante', '')}' de ({pos_actual.x():.1f},{pos_actual.y():.1f}) a ({nueva_x:.1f},{nueva_y:.1f})")
        except Exception:
            pass

    def ajustar_tamano_seleccionado(self):
        """Ajusta el tamaño del estante seleccionado"""
        if not hasattr(self, 'estante_seleccionado'):
            QMessageBox.warning(self, "Error", "Selecciona un estante primero")
            return
        
        r, ok = QInputDialog.getInt(
            self, "Tamaño", "Radio (px):", 
            value=self.estante_seleccionado.radio, min=5
        )
        if ok:
            self.estante_seleccionado.actualizar_tamano(r)
            self.guardar_datos_a_disco(self.nivel_actual)

    def eliminar_estante(self):
        """Elimina el estante seleccionado y desasigna sus items (no los elimina del inventario)"""
        if not hasattr(self, 'estante_seleccionado'):
            QMessageBox.warning(self, "Error", "Selecciona un estante primero")
            return
        
        nombre_estante = getattr(self.estante_seleccionado, 'nombre_estante', 'desconocido')
        
        # Los items del estante se desasignan (se ponen en inventario libre)
        items_desasignados = []
        for s in self.estante_seleccionado.suplementos:
            if isinstance(s, dict):
                code = s.get('codigo', '')
                if code in self.inventario_global:
                    items_desasignados.append(self.inventario_global[code].get('nombre', code))
        
        # Eliminar el estante de la escena y de la lista
        self.scene.removeItem(self.estante_seleccionado)
        if self.estante_seleccionado in self.puntos_graficos:
            self.puntos_graficos.remove(self.estante_seleccionado)
        
        # Guardar cambios
        self.guardar_datos_a_disco(self.nivel_actual)
        self.lista_suplementos.clear()
        self.lbl_estante.setText("Estante eliminado")
        
        # Actualizar vistas
        self.actualizar_lista_inventario()
        
        try:
            items_str = ", ".join(items_desasignados) if items_desasignados else "ninguno"
            self.log_action(f"Eliminado estante '{nombre_estante}' - Items desasignados: {items_str}")
        except Exception:
            pass
        
        QMessageBox.information(
            self, "Éxito", 
            f"Estante '{nombre_estante}' eliminado.\n"
            f"{len(items_desasignados)} item/s desasignado/s al inventario general."
        )

    def actualizar_sugerencias_globales(self):
        """Actualiza las sugerencias de autocompletado"""
        sups = set()
        for nivel in ARCHIVOS_BODEGA.keys():
            ruta = self.obtener_ruta_archivo(nivel)
            if os.path.exists(ruta):
                try:
                    with open(ruta, "r", encoding='utf-8') as f:
                        datos = json.load(f)
                        if isinstance(datos, list):
                            for est in datos:
                                for s in est.get('suplementos', []):
                                    if isinstance(s, dict):
                                        sups.add(s.get('nombre', ''))
                                    else:
                                        sups.add(str(s))
                except:
                    pass
        self.completer.setModel(QStringListModel(sorted(list(sups))))

    # ==================== GESTIÓN DE INVENTARIO GENERAL ====================
    
    def actualizar_lista_inventario(self):
        """Actualiza la lista visual del inventario mostrando TODOS los items con su estado de asignación"""
        self.lista_inventario.clear()
        
        # Crear un set de todos los códigos que están en alguna repisa
        codigos_asignados = set()
        for nivel in ARCHIVOS_BODEGA.keys():
            ruta = self.obtener_ruta_archivo(nivel)
            if os.path.exists(ruta):
                try:
                    with open(ruta, "r", encoding='utf-8') as f:
                        estantes = json.load(f)
                        for est in estantes:
                            for s in est.get('suplementos', []):
                                if isinstance(s, dict):
                                    codigos_asignados.add(s.get('codigo', ''))
                except Exception:
                    pass
        
        # Mostrar todos los items del inventario
        for code in sorted(self.inventario_global.keys()):
            data = self.inventario_global[code]
            nombre = data.get('nombre', '')
            stock = data.get('stock', 0)
            
            # Verificar si está asignado
            if code in codigos_asignados:
                # Contar cuántas repisas lo tienen
                asignaciones = 0
                repisas_info = []
                for nivel in ARCHIVOS_BODEGA.keys():
                    ruta = self.obtener_ruta_archivo(nivel)
                    if os.path.exists(ruta):
                        try:
                            with open(ruta, "r", encoding='utf-8') as f:
                                estantes = json.load(f)
                                for est in estantes:
                                    for s in est.get('suplementos', []):
                                        if isinstance(s, dict) and s.get('codigo', '') == code:
                                            asignaciones += 1
                                            repisas_info.append(f"{est.get('nombre', 'desconocida')}")
                        except Exception:
                            pass
                
                estado = f"✓ Asignado ({asignaciones} repisa/s)"
                tooltip_text = f"{code} | {nombre} | Stock: {stock}\nAsignado a: {', '.join(repisas_info)}"
            else:
                estado = "⊘ Por asignar"
                tooltip_text = f"{code} | {nombre} | Stock: {stock}\nNo asignado a ninguna repisa"
            
            display = f"{code} | {nombre} | {stock} | {estado}"
            item_widget = QListWidgetItem(display)
            item_widget.setToolTip(tooltip_text)
            self.lista_inventario.addItem(item_widget)
        
        try:
            self.log_action(f"Lista de inventario actualizada: {len(self.inventario_global)} items")
        except Exception:
            pass
    
    def agregar_item_inventario(self):
        """Agrega un nuevo item al inventario global (asignable = True)"""
        # Pedir nombre del item
        nombre, ok1 = QInputDialog.getText(self, "Nuevo Item", "Nombre del item:")
        if not ok1 or not nombre:
            return
        
        # Pedir código numérico
        while True:
            codigo, ok2 = QInputDialog.getText(self, "Nuevo Item", "Código numérico:")
            if not ok2:
                return
            if codigo.isdigit():
                break
            else:
                QMessageBox.warning(self, "Código inválido", "El código debe contener solo dígitos.")
        
        # Verificar que no exista
        if codigo in self.inventario_global:
            QMessageBox.warning(self, "Error", f"El código {codigo} ya existe en el inventario")
            return
        
        # Pedir stock inicial
        while True:
            stock_str, ok3 = QInputDialog.getText(self, "Nuevo Item", "Stock inicial:")
            if not ok3:
                return
            if stock_str.isdigit():
                break
            else:
                QMessageBox.warning(self, "Stock inválido", "El stock debe ser un número.")
        
        # Agregar al inventario
        self.inventario_global[codigo] = {
            'nombre': nombre.strip(),
            'stock': int(stock_str),
            'asignable': True  # True = sin repisa, False = en una repisa
        }
        self.guardar_inventario_global()
        self.actualizar_lista_inventario()
        
        try:
            self.log_action(f"Nuevo item en inventario: {codigo} | {nombre} | Stock: {stock_str}")
        except Exception:
            pass
        
        QMessageBox.information(self, "Éxito", f"Item '{nombre}' agregado al inventario")
    
    def editar_item_inventario(self):
        """Edita nombre y stock de un item del inventario"""
        row = self.lista_inventario.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un item para editar")
            return
        
        # Obtener código del item seleccionado
        codigos = sorted(self.inventario_global.keys())
        codigo = codigos[row]
        item_data = self.inventario_global[codigo]
        
        # Editar nombre
        new_nombre, ok1 = QInputDialog.getText(
            self, "Editar Item", "Nombre:", 
            text=item_data.get('nombre', '')
        )
        if not ok1:
            return
        
        # Editar stock
        while True:
            new_stock, ok2 = QInputDialog.getText(
                self, "Editar Item", "Stock:", 
                text=str(item_data.get('stock', 0))
            )
            if not ok2:
                return
            if new_stock.isdigit():
                break
            else:
                QMessageBox.warning(self, "Stock inválido", "El stock debe ser un número.")
        
        # Actualizar
        self.inventario_global[codigo]['nombre'] = new_nombre.strip()
        self.inventario_global[codigo]['stock'] = int(new_stock)
        self.guardar_inventario_global()
        self.actualizar_lista_inventario()
        self.mostrar_detalles(self.estante_seleccionado) if hasattr(self, 'estante_seleccionado') else None
        
        try:
            self.log_action(f"Editado item {codigo}: '{new_nombre}' | Stock: {new_stock}")
        except Exception:
            pass
    
    def eliminar_item_inventario(self):
        """Elimina un item del inventario (solo si asignable=True, es decir, sin repisa)"""
        row = self.lista_inventario.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un item para eliminar")
            return
        
        # Obtener código del item seleccionado
        codigos = sorted(self.inventario_global.keys())
        codigo = codigos[row]
        item_data = self.inventario_global[codigo]
        nombre = item_data.get('nombre', '')
        
        # Verificar que esté asignable (no esté en ninguna repisa)
        esta_en_repisa = False
        for nivel in ARCHIVOS_BODEGA.keys():
            ruta = self.obtener_ruta_archivo(nivel)
            if os.path.exists(ruta):
                try:
                    with open(ruta, "r", encoding='utf-8') as f:
                        estantes = json.load(f)
                        for est in estantes:
                            for s in est.get('suplementos', []):
                                if isinstance(s, dict) and s.get('codigo', '') == codigo:
                                    esta_en_repisa = True
                                    break
                except Exception:
                    pass
        
        if esta_en_repisa:
            QMessageBox.warning(
                self, "Error", 
                f"No se puede eliminar '{nombre}' porque está asignado a una o más repisas.\n"
                f"Retíralo de todas las repisas primero."
            )
            return
        
        # Confirmar eliminación
        res = QMessageBox.question(
            self, "Confirmar", 
            f"¿Eliminar item '{nombre}'?\nEsto no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if res == QMessageBox.StandardButton.Yes:
            del self.inventario_global[codigo]
            self.guardar_inventario_global()
            self.actualizar_lista_inventario()
            
            try:
                self.log_action(f"Eliminado item {codigo} del inventario")
            except Exception:
                pass
            
            QMessageBox.information(self, "Éxito", f"Item '{nombre}' eliminado del inventario")

    def buscar_suplemento(self):
        """Busca un suplemento en todas las bodegas"""
        t = self.search_input.text().strip().lower()
        if not t:
            return
        for p in self.puntos_graficos:
            p.setBrush(QColor("red"))

        found_any = False
        for nivel in ARCHIVOS_BODEGA.keys():
            ruta = self.obtener_ruta_archivo(nivel)
            if os.path.exists(ruta):
                try:
                    with open(ruta, "r", encoding='utf-8') as f:
                        estantes = json.load(f)
                        for est in estantes:
                            # soportar formatos antiguos (strings) y nuevos (dicts)
                            found = False
                            for s in est.get('suplementos', []):
                                name = s.get('nombre','').lower() if isinstance(s, dict) else str(s).lower()
                                if t in name:
                                    found = True
                                    break
                            if found:
                                found_any = True
                                if nivel == self.nivel_actual:
                                    for p in self.puntos_graficos:
                                        if p.nombre_estante == est['nombre']:
                                            p.setBrush(QColor("#DA9CFF"))
                                            self.view.centerOn(p)
                                            try:
                                                self.log_action(f"Buscar suplemento: encontrado '{t}' en estante '{p.nombre_estante}' nivel='{nivel}'")
                                            except Exception:
                                                pass
                                            return
                                else:
                                    res = QMessageBox.question(
                                        self, "Ubicación", 
                                        f"Está en: {nivel}. ¿Cambiar de mapa?", 
                                        QMessageBox.StandardButton.Yes | 
                                        QMessageBox.StandardButton.No
                                    )
                                    if res == QMessageBox.StandardButton.Yes:
                                        self.cargar_nivel(nivel)
                                        self.buscar_suplemento()
                                    return
                except:
                    pass

        if not found_any:
            QMessageBox.warning(self, "No encontrado", f"No se encontraron suplementos que coincidan con '{t}'")
            try:
                self.log_action(f"Buscar suplemento: no se encontraron resultados para '{t}'")
            except Exception:
                pass

    def buscar_por_codigo(self):
        """Busca por código de item en el inventario global y resalta la estantería que lo contiene."""
        code = self.search_code_input.text().strip()
        if not code:
            return

        code_raw = code

        # resetear colores
        for p in self.puntos_graficos:
            p.setBrush(QColor("red"))

        found_any = False

        # Buscar en archivos (solo códigos de items en suplementos)
        for nivel in ARCHIVOS_BODEGA.keys():
            ruta = self.obtener_ruta_archivo(nivel)
            if not os.path.exists(ruta):
                continue
            try:
                with open(ruta, "r", encoding='utf-8') as f:
                    estantes = json.load(f)
            except Exception:
                continue

            for est in estantes:
                found = False
                # Buscar en items del estante (solo por código)
                for s in est.get('suplementos', []):
                    if isinstance(s, dict):
                        s_code = str(s.get('codigo', '') or '')
                        if s_code and s_code == code_raw:
                            found = True
                            break

                if found:
                    found_any = True
                    # si está en el nivel cargado, resaltar el estante correspondiente
                    if nivel == self.nivel_actual:
                        for p in self.puntos_graficos:
                            if p.nombre_estante == est.get('nombre'):
                                p.setBrush(QColor("yellow"))
                                self.view.centerOn(p)
                                try:
                                    item_name = self.inventario_global.get(code_raw, {}).get('nombre', code_raw)
                                    self.log_action(f"Buscar código: encontrado item '{item_name}' ({code}) en estante '{p.nombre_estante}' (nivel='{nivel}')")
                                except Exception:
                                    pass
                                return
                        # si no encontramos punto cargado (inconsistencia), informar
                        QMessageBox.information(self, "Encontrado", f"Item '{code}' pertenece a estante '{est.get('nombre')}' pero no está cargado como punto visual.")
                        try:
                            self.log_action(f"Buscar código: encontrado item '{code}' en estante '{est.get('nombre')}' nivel='{nivel}', pero no está en puntos cargados")
                        except Exception:
                            pass
                        return

                    # si pertenece a otra bodega preguntar si cambiar
                    res = QMessageBox.question(
                        self, "Ubicación",
                        f"El item '{code}' está en: {nivel}. ¿Cambiar de mapa?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if res == QMessageBox.StandardButton.Yes:
                        self.cargar_nivel(nivel)
                        # repetir búsqueda en el nuevo nivel (llamada recursiva)
                        self.buscar_por_codigo()
                    return

        if not found_any:
            QMessageBox.warning(self, "No encontrado", f"No se encontraron resultados para el código '{code}'")
            try:
                self.log_action(f"Buscar código: no se encontraron resultados para '{code}'")
            except Exception:
                pass

    # -------------------- Controles de Zoom --------------------
    def zoom_in(self):
        """Aumenta el zoom de la vista (handler del botón)."""
        try:
            factor = 1.15
            self.view.scale(factor, factor)
            try:
                self.log_action("Zoom In ejecutado")
            except Exception:
                pass
        except Exception as e:
            print(f"[Zoom] Error zoom_in: {e}")

    def zoom_out(self):
        """Disminuye el zoom respetando el límite mínimo calculado tras fitInView."""
        try:
            factor = 1 / 1.15
            current_scale = self.view.transform().m11()
            new_scale = current_scale * factor
            if self.view.min_zoom_scale is not None and new_scale < self.view.min_zoom_scale:
                # Escalar exactamente hasta el mínimo permitido
                try:
                    if current_scale != 0:
                        required = self.view.min_zoom_scale / current_scale
                        self.view.scale(required, required)
                except Exception:
                    pass
            else:
                self.view.scale(factor, factor)
            try:
                self.log_action("Zoom Out ejecutado")
            except Exception:
                pass
        except Exception as e:
            print(f"[Zoom] Error zoom_out: {e}")

    def zoom_reset(self):
        """Ajusta la vista para encajar la imagen y recalcula el min_zoom_scale."""
        try:
            # Re-ajustar al rectángulo de la escena (imagen)
            rect = self.scene.sceneRect()
            if rect.isNull():
                return
            self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            try:
                self.view.min_zoom_scale = self.view.transform().m11()
            except Exception:
                self.view.min_zoom_scale = None
            try:
                self.log_action("Zoom Reset (fitInView) ejecutado")
            except Exception:
                pass
        except Exception as e:
            print(f"[Zoom] Error zoom_reset: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Aplicar estilo minimalista oscuro con acento morado (#DA9CFF)
    dark_styles = """
    QWidget { background-color: #0f1113; color: #e8e8e8; }
    QMainWindow { background-color: #0f1113; }
    QPushButton { background-color: #151618; border: 1px solid #222; padding: 6px; border-radius: 6px; }
    QPushButton:hover { border-color: #3b2a66; }
    QLabel { color: #e8e8e8; }
    QListWidget { background-color: #0b0c0d; border: 1px solid #222; color: #e8e8e8; }
    QLineEdit { background-color: #0b0c0d; border: 1px solid #222; color: #e8e8e8; padding: 4px; }
    QComboBox { background-color: #0b0c0d; border: 1px solid #222; color: #e8e8e8; }
    QSpinBox { background-color: #0b0c0d; border: 1px solid #222; color: #e8e8e8; }
    QDialog { background-color: #0f1113; color: #e8e8e8; }
    /* Accent */
    QPushButton#accent { background-color: #DA9CFF; color: #10061a; }
    QHeaderView::section { background-color: #0f1113; }
    """
    app.setStyleSheet(dark_styles)
    v = VentanaBodega()
    v.showMaximized()
    sys.exit(app.exec())