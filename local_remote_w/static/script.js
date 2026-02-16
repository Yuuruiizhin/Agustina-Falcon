let stage, layer, puntosData = [], currentImg, scale = 1;
const API_BASE = window.location.origin;

// Variables para gestos móviles
let lastTouchDistance = 0;
let lastTapTime = 0;
const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

window.onload = init;
window.onresize = () => { if(stage && currentImg) ajustarMapaAResize(); };

async function init() {
    const res = await fetch(`${API_BASE}/api/bodegas`);
    const bodegas = await res.json();
    const selector = document.getElementById('selector-bodega');
    selector.innerHTML = bodegas.map(b => `<option value="${b}">${b}</option>`).join('');
    selector.onchange = (e) => cargarBodega(e.target.value);
    
    document.getElementById('input-busqueda').oninput = (e) => {
        filtrarPorItem(e.target.value);
        verificarSeleccionSugerencia(e.target.value);
    };
    if(bodegas.length > 0) cargarBodega(bodegas[0]);
}

async function cargarBodega(nombre) {
    if(stage) stage.destroy();
    // Reset globals para forzar recreación de la imagen y limpiar marcadores
    currentImg = null;
    puntosData = [];
    scale = 1;
    document.getElementById('marker-layer').innerHTML = '';
    const container = document.getElementById('canvas-container');
    
    stage = new Konva.Stage({
        container: 'canvas-container',
        width: container.offsetWidth,
        height: container.offsetHeight,
        draggable: true
    });
    
    layer = new Konva.Layer();
    stage.add(layer);

    const img = new Image();
    img.src = `${API_BASE}/api/imagen/${nombre}?t=${Date.now()}`;
    img.onload = () => {
        ajustarMapaAResize(img);
        obtenerPuntos(nombre);
    };
    stage.on('dragmove wheel batchDraw', updateMarkers);
    
    // Gestos móviles: Pinch-to-zoom
    const canvas = document.querySelector('canvas');
    canvas.addEventListener('touchstart', handleTouchStart, { passive: false });
    canvas.addEventListener('touchmove', handleTouchMove, { passive: false });
    canvas.addEventListener('touchend', handleTouchEnd, { passive: false });
    canvas.addEventListener('wheel', handleMouseWheel, { passive: false });
}

function ajustarMapaAResize(nuevaImg) {
    const imgObj = nuevaImg || currentImg.image();
    const container = document.getElementById('canvas-container');
    
    stage.width(container.offsetWidth);
    stage.height(container.offsetHeight);

    const scX = stage.width() / imgObj.width;
    const scY = stage.height() / imgObj.height;
    scale = Math.min(scX, scY) * 0.9;

    if(!currentImg) {
        currentImg = new Konva.Image({ image: imgObj });
        layer.add(currentImg);
    }
    
    currentImg.width(imgObj.width * scale);
    currentImg.height(imgObj.height * scale);

    // Asegurar que el stage está en escala inicial 1:1
    stage.scale({ x: 1, y: 1 });
    
    // Posicionar la imagen centrada en el canvas
    stage.position({
        x: (stage.width() - currentImg.width()) / 2,
        y: (stage.height() - currentImg.height()) / 2
    });
    
    if(puntosData.length > 0) {
        document.querySelectorAll('.dot-marker').forEach((div, i) => {
            div._x = puntosData[i].x * scale;
            div._y = puntosData[i].y * scale;
        });
    }
    updateMarkers();
}

async function obtenerPuntos(nombre) {
    const res = await fetch(`${API_BASE}/api/puntos/${nombre}`);
    puntosData = await res.json();
    const layerHTML = document.getElementById('marker-layer');
    const datalist = document.getElementById('lista-items');
    layerHTML.innerHTML = '';
    let itemsUnificados = new Set();

    puntosData.forEach(p => {
        p.suplementos.forEach(s => itemsUnificados.add(`${(s.nombre || s).toUpperCase()} | #${s.codigo || "S/C"}`));
        const div = document.createElement('div');
        div.className = 'dot-marker';
        div._x = p.x * scale; div._y = p.y * scale;
        div._data = p;
        div.onclick = () => { mostrarDetalles(p); resaltarDot(div); };
        layerHTML.appendChild(div);
    });

    datalist.innerHTML = Array.from(itemsUnificados).sort().map(i => `<option value="${i}">`).join('');
    updateMarkers();
}

function updateMarkers() {
    const transform = stage.getAbsoluteTransform().getMatrix();
    document.querySelectorAll('.dot-marker').forEach(div => {
        div.style.left = (div._x * transform[0] + transform[4]) + 'px';
        div.style.top = (div._y * transform[3] + transform[5]) + 'px';
    });
}

function zoomMap(factor) {
    const oldScale = stage.scaleX();
    const newScale = Math.max(0.5, Math.min(oldScale * factor, 5)); // Límites: 0.5x a 5x
    const viewport = { x: stage.width() / 2, y: stage.height() / 2 };
    
    // Calcular la posición del centro en las coordenadas del stage (sin escala)
    const stagePos = { x: stage.x(), y: stage.y() };
    const pointOnStage = {
        x: (viewport.x - stagePos.x) / oldScale,
        y: (viewport.y - stagePos.y) / oldScale
    };
    
    // Aplicar nueva escala
    stage.scale({ x: newScale, y: newScale });
    
    // Reposicionar para que el punto siga siendo el mismo en la pantalla
    stage.position({
        x: viewport.x - pointOnStage.x * newScale,
        y: viewport.y - pointOnStage.y * newScale
    });
    
    updateZoomDisplay();
    updateMarkers();
}

function resetZoom() {
    stage.scale({ x: 1, y: 1 });
    stage.position({ x: (stage.width() - currentImg.width())/2, y: (stage.height() - currentImg.height())/2 });
    updateZoomDisplay();
    updateMarkers();
}

function updateZoomDisplay() {
    const zoomPercent = Math.round(stage.scaleX() * 100);
    const display = document.getElementById('zoom-display');
    if (display) {
        display.textContent = zoomPercent + '%';
    }
}

function filtrarPorItem(val) {
    const q = val.split(' | #')[0].toLowerCase();
    document.querySelectorAll('.dot-marker').forEach(div => {
        const match = div._data.suplementos.some(s => (s.nombre || s).toLowerCase().includes(q) || (s.codigo || "").toLowerCase().includes(q));
        div.style.display = (match || !val) ? 'block' : 'none';
        div.style.opacity = val && match ? "1" : (val ? "0.2" : "1");
    });
}

function verificarSeleccionSugerencia(val) {
    if (!val.includes(' | #')) return;
    const partes = val.split(' | #');
    const nom = partes[0].toLowerCase();
    const estante = puntosData.find(p => p.suplementos.some(s => (s.nombre || s).toLowerCase() === nom));
    if(estante) {
        mostrarDetalles(estante);
        document.querySelectorAll('.dot-marker').forEach(m => { if(m._data.nombre === estante.nombre) resaltarDot(m); });
    }
}

function resaltarDot(el) {
    document.querySelectorAll('.dot-marker').forEach(d => d.classList.remove('active'));
    el.classList.add('active');
}

function mostrarDetalles(p) {
    document.getElementById('inventory-title').textContent = p.nombre.toUpperCase();
    document.getElementById('panel-inventario').classList.add('active');
    document.getElementById('lista-suplementos').innerHTML = p.suplementos.map(s => `
        <div class="item-card">
            <span class="item-name">${s.nombre || s}</span>
            <span class="item-code">ID: ${s.codigo || 'S/C'}</span>
            ${s.gaveta ? `<span class="item-code" style="color: #00d4ff;">Gaveta: ${s.gaveta}</span>` : ''}
            ${s.stock ? `<span class="item-code" style="color: #00ff00;">Stock: ${s.stock}</span>` : ''}
        </div>
    `).join('');
}

function cerrarInventario() { document.getElementById('panel-inventario').classList.remove('active'); }

// ========== GESTOS MÓVILES ==========

// Distancia entre dos puntos touch
function getTouchDistance(t1, t2) {
    const dx = t1.clientX - t2.clientX;
    const dy = t1.clientY - t2.clientY;
    return Math.sqrt(dx * dx + dy * dy);
}

// Punto central entre dos toques
function getTouchCenter(t1, t2) {
    return {
        x: (t1.clientX + t2.clientX) / 2,
        y: (t1.clientY + t2.clientY) / 2
    };
}

function handleTouchStart(e) {
    if (e.touches.length === 2) {
        // Pinch-to-zoom: dos dedos
        lastTouchDistance = getTouchDistance(e.touches[0], e.touches[1]);
        e.preventDefault();
    } else if (e.touches.length === 1) {
        // Double-tap para zoom
        const now = Date.now();
        if (now - lastTapTime < 300) {
            // Double-tap detectado
            zoomMap(1.5);
            lastTapTime = 0;
        } else {
            lastTapTime = now;
        }
    }
}

function handleTouchMove(e) {
    if (e.touches.length === 2) {
        // Pinch-to-zoom activo
        const currentDistance = getTouchDistance(e.touches[0], e.touches[1]);
        
        if (lastTouchDistance > 0) {
            const factor = currentDistance / lastTouchDistance;
            
            // Solo aplicar zoom si el cambio es significativo (>5%)
            if (Math.abs(factor - 1) > 0.05) {
                const center = getTouchCenter(e.touches[0], e.touches[1]);
                const canvas = document.querySelector('canvas');
                const rect = canvas.getBoundingClientRect();
                
                // Convertir posición pantalla a posición canvas
                const viewport = {
                    x: center.x - rect.left,
                    y: center.y - rect.top
                };
                
                const oldScale = stage.scaleX();
                const newScale = Math.max(0.5, Math.min(oldScale * factor, 5));
                const actualFactor = newScale / oldScale;
                
                const stagePos = { x: stage.x(), y: stage.y() };
                const pointOnStage = {
                    x: (viewport.x - stagePos.x) / oldScale,
                    y: (viewport.y - stagePos.y) / oldScale
                };
                
                stage.scale({ x: newScale, y: newScale });
                stage.position({
                    x: viewport.x - pointOnStage.x * newScale,
                    y: viewport.y - pointOnStage.y * newScale
                });
                
                updateZoomDisplay();
                updateMarkers();
                lastTouchDistance = currentDistance;
            }
        }
        e.preventDefault();
    }
}

function handleTouchEnd(e) {
    lastTouchDistance = 0;
}

function handleMouseWheel(e) {
    // Scroll con rueda para zoom en desktop
    if (!isMobile) {
        const factor = e.deltaY > 0 ? 0.9 : 1.1;
        
        const rect = document.querySelector('canvas').getBoundingClientRect();
        const viewport = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
        
        const oldScale = stage.scaleX();
        const newScale = Math.max(0.5, Math.min(oldScale * factor, 5));
        
        const stagePos = { x: stage.x(), y: stage.y() };
        const pointOnStage = {
            x: (viewport.x - stagePos.x) / oldScale,
            y: (viewport.y - stagePos.y) / oldScale
        };
        
        stage.scale({ x: newScale, y: newScale });
        stage.position({
            x: viewport.x - pointOnStage.x * newScale,
            y: viewport.y - pointOnStage.y * newScale
        });
        
        updateZoomDisplay();
        updateMarkers();
        e.preventDefault();
    }
}