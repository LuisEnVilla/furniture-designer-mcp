"""Generate interactive HTML design reports with 3D visualization.

Produces a self-contained HTML file with:
- Three.js 3D viewer (orbit/zoom/pan)
- Schematic/blueprint aesthetic
- Iteration history with slider
- Panel inspection on click
- Summary and parts table
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime


def generate_design_report(
    spec: dict,
    comment: str = "",
    iteration_name: str = "",
    output_path: str | None = None,
) -> str:
    """Generate or update an interactive HTML design report.

    If output_path points to an existing report, appends a new iteration.
    Otherwise creates a fresh report.

    Returns the absolute path to the HTML file.
    """
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "design_report.html")

    output_path = os.path.abspath(output_path)

    # Load existing iterations if file exists
    iterations: list[dict] = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = f.read()
            match = re.search(
                r'<script id="iterations-data" type="application/json">(.*?)</script>',
                existing,
                re.DOTALL,
            )
            if match:
                iterations = json.loads(match.group(1))
        except Exception:
            pass  # Start fresh if parsing fails

    # Append new iteration
    iterations.append({
        "name": iteration_name or f"v{len(iterations) + 1}",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "comment": comment,
        "spec": spec,
    })

    # Generate HTML
    iterations_json = json.dumps(iterations, ensure_ascii=False)
    html = _HTML_TEMPLATE.replace("__ITERATIONS_JSON__", iterations_json)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design Report — Furniture Designer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
:root {
    --bg-primary: #0b1120;
    --bg-secondary: #0f172a;
    --bg-panel: #111827;
    --bg-card: #1e293b;
    --grid-color: rgba(0, 200, 180, 0.06);
    --grid-major: rgba(0, 200, 180, 0.12);
    --accent: #22d3ee;
    --accent-dim: rgba(34, 211, 238, 0.3);
    --accent-green: #4ade80;
    --accent-amber: #fbbf24;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-dim: #64748b;
    --border: rgba(34, 211, 238, 0.15);
    --border-strong: rgba(34, 211, 238, 0.3);
    --highlight: #facc15;
    --wireframe: rgba(34, 211, 238, 0.5);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: var(--bg-primary);
    font-family: 'Share Tech Mono', 'Courier New', monospace;
    color: var(--text-primary);
    overflow: hidden;
    height: 100vh;
}

/* Header */
#header {
    height: 48px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 20px;
    gap: 24px;
    z-index: 10;
}
#header h1 {
    font-size: 13px;
    font-weight: 400;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--accent);
    white-space: nowrap;
}
#header h1 span { color: var(--text-primary); }
.iter-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-left: auto;
}
.iter-controls label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
}
#iter-slider {
    -webkit-appearance: none;
    width: 180px;
    height: 3px;
    background: var(--border-strong);
    border-radius: 2px;
    outline: none;
}
#iter-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px; height: 14px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    border: 2px solid var(--bg-primary);
}
#iter-label {
    font-size: 13px;
    color: var(--accent);
    min-width: 40px;
}
#iter-comment {
    font-size: 11px;
    color: var(--text-secondary);
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Main layout */
#main {
    display: flex;
    height: calc(100vh - 48px);
}

/* Viewport */
#viewport {
    flex: 1;
    position: relative;
    background: var(--bg-primary);
    overflow: hidden;
}
#viewport canvas { display: block; }
#dim-overlay {
    position: absolute;
    bottom: 16px;
    left: 16px;
    font-size: 11px;
    color: var(--text-dim);
    line-height: 1.6;
}
#dim-overlay span { color: var(--accent); }
.crosshair {
    position: absolute;
    pointer-events: none;
}
.crosshair-h {
    top: 50%; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--grid-color), transparent);
}
.crosshair-v {
    left: 50%; top: 0; bottom: 0; width: 1px;
    background: linear-gradient(transparent, var(--grid-color), transparent);
}

/* Info Panel */
#info-panel {
    width: 340px;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

/* Tabs */
#tabs {
    display: flex;
    border-bottom: 1px solid var(--border);
}
.tab-btn {
    flex: 1;
    padding: 10px 0;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-dim);
    font-family: inherit;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.2s;
}
.tab-btn:hover { color: var(--text-secondary); }
.tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
}

/* Tab content */
.tab-content {
    display: none;
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}
.tab-content.active { display: block; }
.tab-content::-webkit-scrollbar { width: 4px; }
.tab-content::-webkit-scrollbar-track { background: var(--bg-secondary); }
.tab-content::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 2px; }

/* Summary */
.stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 16px;
}
.stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 10px;
}
.stat-card.wide { grid-column: span 2; }
.stat-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-dim);
    margin-bottom: 4px;
}
.stat-value {
    font-size: 16px;
    color: var(--accent);
}
.stat-value.small { font-size: 13px; }

/* Role breakdown */
.role-list { margin-top: 8px; }
.role-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
}
.role-swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    border: 1px solid rgba(255,255,255,0.1);
}
.role-name { flex: 1; color: var(--text-secondary); }
.role-count { color: var(--accent); }

/* Parts table */
.parts-table {
    width: 100%;
    font-size: 11px;
    border-collapse: collapse;
}
.parts-table th {
    text-align: left;
    padding: 6px 4px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border-strong);
}
.parts-table td {
    padding: 5px 4px;
    border-bottom: 1px solid var(--border);
    color: var(--text-secondary);
}
.parts-table tr { cursor: pointer; transition: background 0.15s; }
.parts-table tr:hover { background: rgba(34, 211, 238, 0.05); }
.parts-table tr.selected { background: rgba(34, 211, 238, 0.1); }
.parts-table tr.selected td { color: var(--accent); }

/* History */
.history-item {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 12px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: border-color 0.2s;
}
.history-item:hover { border-color: var(--accent-dim); }
.history-item.active { border-color: var(--accent); }
.history-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}
.history-name {
    font-size: 13px;
    color: var(--accent);
}
.history-time {
    font-size: 10px;
    color: var(--text-dim);
    margin-left: auto;
}
.history-comment {
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.5;
}
.history-stats {
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 6px;
}

/* Panel tooltip */
#tooltip {
    position: fixed;
    display: none;
    background: var(--bg-card);
    border: 1px solid var(--accent);
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 11px;
    z-index: 100;
    pointer-events: none;
    max-width: 260px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}
#tooltip .tt-title {
    color: var(--accent);
    font-size: 12px;
    margin-bottom: 6px;
}
#tooltip .tt-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 2px 0;
}
#tooltip .tt-label { color: var(--text-dim); }
#tooltip .tt-value { color: var(--text-primary); }

/* Notes */
.notes-list {
    margin-top: 8px;
    padding-left: 0;
    list-style: none;
}
.notes-list li {
    font-size: 11px;
    color: var(--text-secondary);
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
}
.notes-list li::before {
    content: "// ";
    color: var(--text-dim);
}
</style>
</head>
<body>
<!-- Header -->
<header id="header">
    <h1>DESIGN REPORT — <span id="hdr-type"></span></h1>
    <div class="iter-controls">
        <label>ITERATION</label>
        <input type="range" id="iter-slider" min="0" max="0" value="0">
        <span id="iter-label">v1</span>
        <span id="iter-comment"></span>
    </div>
</header>

<!-- Main -->
<div id="main">
    <div id="viewport">
        <div class="crosshair crosshair-h"></div>
        <div class="crosshair crosshair-v"></div>
        <div id="dim-overlay"></div>
    </div>
    <aside id="info-panel">
        <nav id="tabs">
            <button class="tab-btn active" data-tab="summary">Resumen</button>
            <button class="tab-btn" data-tab="parts">Partes</button>
            <button class="tab-btn" data-tab="history">Historial</button>
        </nav>
        <div id="tab-summary" class="tab-content active"></div>
        <div id="tab-parts" class="tab-content"></div>
        <div id="tab-history" class="tab-content"></div>
    </aside>
</div>

<!-- Tooltip -->
<div id="tooltip"></div>

<!-- Data -->
<script id="iterations-data" type="application/json">__ITERATIONS_JSON__</script>

<!-- Three.js -->
<script src="https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.169.0/examples/js/controls/OrbitControls.js"></script>

<script>
// ============================================================
// Data & State
// ============================================================
const iterations = JSON.parse(
    document.getElementById('iterations-data').textContent
);
let currentIdx = iterations.length - 1;
let furnitureGroup = null;
let selectedMesh = null;
let meshes = [];

// ============================================================
// Colors (matches FreeCAD)
// ============================================================
const COLORS = {
    side: [0.90, 0.75, 0.55],
    bottom: [0.85, 0.70, 0.50],
    top_panel: [0.85, 0.70, 0.50],
    floor: [0.85, 0.70, 0.50],
    shelf: [0.70, 0.85, 0.65],
    back: [0.75, 0.75, 0.75],
    door: [0.60, 0.75, 0.90],
    rail: [0.65, 0.55, 0.42],
    kickplate: [0.50, 0.50, 0.50],
    divider: [0.90, 0.72, 0.40],
    drawer_front: [0.60, 0.75, 0.90],
    drawer_side: [0.50, 0.65, 0.85],
    drawer_back: [0.45, 0.60, 0.80],
    drawer_bottom: [0.55, 0.70, 0.88],
};
const DEFAULT_COLOR = [0.80, 0.70, 0.55];

const ROLE_LABELS = {
    side: "Lateral", bottom: "Piso", top_panel: "Tapa",
    floor: "Piso int.", shelf: "Repisa", back: "Respaldo",
    door: "Puerta", rail: "Travesaño", kickplate: "Zócalo",
    divider: "División", drawer_front: "Frente cajón",
    drawer_side: "Lat. cajón", drawer_back: "Tras. cajón",
    drawer_bottom: "Fondo cajón",
};

// ============================================================
// Box dimension mapping (matches _box_dims in freecad_scripts.py)
// Returns [FreeCAD_X, FreeCAD_Y, FreeCAD_Z]
// ============================================================
function boxDims(part) {
    const w = part.width_mm, h = part.height_mm, t = part.thickness_mm;
    const role = part.role;
    if (role === 'side' || role === 'divider') return [t, w, h];
    if (['bottom','top_panel','shelf','floor'].includes(role)) return [w, h, t];
    if (role === 'back') return [w, t, h];
    if (role === 'door' || role === 'drawer_front') return [w, t, h];
    if (role === 'drawer_side') return [t, w, h];
    if (role === 'drawer_back') return [w, t, h];
    if (role === 'drawer_bottom') return [w, h, t];
    if (role === 'rail' || role === 'kickplate') return [w, t, h];
    return [w, h, t];
}

// ============================================================
// Three.js Scene
// ============================================================
const viewport = document.getElementById('viewport');
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(0x0b1120);
viewport.insertBefore(renderer.domElement, viewport.firstChild);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 1, 100000);
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.rotateSpeed = 0.6;

// Lights
scene.add(new THREE.AmbientLight(0x445566, 0.6));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(1, 1.5, 1);
scene.add(dirLight);
const fillLight = new THREE.DirectionalLight(0x8899aa, 0.3);
fillLight.position.set(-1, 0.5, -1);
scene.add(fillLight);

// Grid
function createGrid(maxDim) {
    if (scene.getObjectByName('gridHelper')) {
        scene.remove(scene.getObjectByName('gridHelper'));
    }
    const size = Math.ceil(maxDim / 500) * 500 + 500;
    const divs = Math.round(size / 100);
    const grid = new THREE.GridHelper(size, divs, 0x004d47, 0x002a27);
    grid.material.transparent = true;
    grid.material.opacity = 0.4;
    grid.name = 'gridHelper';
    scene.add(grid);
}

// Raycaster
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

// ============================================================
// Build furniture from spec
// ============================================================
function buildFurniture(spec) {
    // Remove previous
    if (furnitureGroup) scene.remove(furnitureGroup);
    furnitureGroup = new THREE.Group();
    meshes = [];

    const parts = spec.parts || [];
    parts.forEach(part => {
        const [fcX, fcY, fcZ] = boxDims(part);
        // Three.js: X=FreeCAD_X, Y=FreeCAD_Z(height), Z=FreeCAD_Y(depth)
        const geom = new THREE.BoxGeometry(fcX, fcZ, fcY);

        const rgb = COLORS[part.role] || DEFAULT_COLOR;
        const color = new THREE.Color(rgb[0], rgb[1], rgb[2]);

        // Translucent solid
        const mat = new THREE.MeshPhysicalMaterial({
            color: color,
            transparent: true,
            opacity: 0.55,
            roughness: 0.4,
            metalness: 0.05,
            side: THREE.DoubleSide,
        });
        const mesh = new THREE.Mesh(geom, mat);

        // Wireframe edges
        const edges = new THREE.EdgesGeometry(geom);
        const lineMat = new THREE.LineBasicMaterial({
            color: 0x22d3ee,
            transparent: true,
            opacity: 0.35,
        });
        const wireframe = new THREE.LineSegments(edges, lineMat);
        mesh.add(wireframe);

        // Position: spec position is corner, Three.js geometry centers at origin
        const pos = part.position_mm || { x: 0, y: 0, z: 0 };
        mesh.position.set(
            pos.x + fcX / 2,
            pos.z + fcZ / 2,
            pos.y + fcY / 2
        );

        mesh.userData = {
            partId: part.id,
            role: part.role,
            width_mm: part.width_mm,
            height_mm: part.height_mm,
            thickness_mm: part.thickness_mm,
            edge_banding: part.edge_banding || [],
            position_mm: pos,
        };

        furnitureGroup.add(mesh);
        meshes.push(mesh);
    });

    scene.add(furnitureGroup);

    // Center camera
    const box = new THREE.Box3().setFromObject(furnitureGroup);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);

    controls.target.copy(center);
    camera.position.set(
        center.x + maxDim * 0.9,
        center.y + maxDim * 0.7,
        center.z + maxDim * 0.9
    );
    controls.update();
    createGrid(maxDim);
}

// ============================================================
// Selection / Tooltip
// ============================================================
const tooltip = document.getElementById('tooltip');

function selectPart(mesh) {
    // Deselect previous
    if (selectedMesh) {
        selectedMesh.material.emissive.setHex(0x000000);
        selectedMesh.material.opacity = 0.55;
        selectedMesh.children[0].material.opacity = 0.35;
        selectedMesh.children[0].material.color.setHex(0x22d3ee);
    }
    selectedMesh = mesh;
    if (!mesh) {
        tooltip.style.display = 'none';
        document.querySelectorAll('.parts-table tr.selected').forEach(r => r.classList.remove('selected'));
        return;
    }
    // Highlight
    mesh.material.emissive.setHex(0x332200);
    mesh.material.opacity = 0.85;
    mesh.children[0].material.opacity = 0.8;
    mesh.children[0].material.color.setHex(0xfacc15);

    // Highlight in parts table
    document.querySelectorAll('.parts-table tr').forEach(r => {
        r.classList.toggle('selected', r.dataset.id === mesh.userData.partId);
    });
}

function showTooltip(mesh, event) {
    const d = mesh.userData;
    const label = ROLE_LABELS[d.role] || d.role;
    tooltip.innerHTML = `
        <div class="tt-title">${label} — ${d.partId}</div>
        <div class="tt-row"><span class="tt-label">Dimensiones</span><span class="tt-value">${d.width_mm} × ${d.height_mm} × ${d.thickness_mm} mm</span></div>
        <div class="tt-row"><span class="tt-label">Posición</span><span class="tt-value">(${d.position_mm.x}, ${d.position_mm.y}, ${d.position_mm.z})</span></div>
        <div class="tt-row"><span class="tt-label">Canteado</span><span class="tt-value">${Array.isArray(d.edge_banding) ? d.edge_banding.join(', ') || '—' : d.edge_banding || '—'}</span></div>
    `;
    tooltip.style.display = 'block';
    const x = Math.min(event.clientX + 16, window.innerWidth - 280);
    const y = Math.min(event.clientY + 16, window.innerHeight - 120);
    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
}

renderer.domElement.addEventListener('click', e => {
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(meshes);
    if (hits.length > 0) {
        selectPart(hits[0].object);
        showTooltip(hits[0].object, e);
    } else {
        selectPart(null);
    }
});

renderer.domElement.addEventListener('mousemove', () => {
    tooltip.style.display = 'none';
});

// ============================================================
// UI: Tabs
// ============================================================
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
});

// ============================================================
// UI: Update panels from iteration
// ============================================================
function updateUI(idx) {
    currentIdx = idx;
    const iter = iterations[idx];
    const spec = iter.spec;

    // Header
    document.getElementById('hdr-type').textContent =
        (spec.furniture_type || '?').toUpperCase().replace(/_/g, ' ');
    document.getElementById('iter-label').textContent = iter.name;
    document.getElementById('iter-comment').textContent = iter.comment || '';

    // Slider
    const slider = document.getElementById('iter-slider');
    slider.max = iterations.length - 1;
    slider.value = idx;

    // Build 3D
    buildFurniture(spec);

    // Dimension overlay
    const dims = spec.dimensions_cm || {};
    document.getElementById('dim-overlay').innerHTML =
        `<span>${dims.width || '?'}</span> × <span>${dims.height || '?'}</span> × <span>${dims.depth || '?'}</span> cm` +
        ` · ${spec.material || '?'} · ${(spec.parts || []).length} partes`;

    // Summary tab
    updateSummary(spec);
    // Parts tab
    updateParts(spec);
    // History tab
    updateHistory(idx);
}

function updateSummary(spec) {
    const parts = spec.parts || [];
    const dims = spec.dimensions_cm || {};
    const hw = spec.hardware || [];
    const notes = spec.notes || [];

    // Count by role
    const roleCounts = {};
    parts.forEach(p => { roleCounts[p.role] = (roleCounts[p.role] || 0) + 1; });

    let roleHTML = '';
    Object.entries(roleCounts).sort((a, b) => b[1] - a[1]).forEach(([role, count]) => {
        const rgb = COLORS[role] || DEFAULT_COLOR;
        const hex = `rgb(${Math.round(rgb[0]*255)},${Math.round(rgb[1]*255)},${Math.round(rgb[2]*255)})`;
        const label = ROLE_LABELS[role] || role;
        roleHTML += `<div class="role-row">
            <div class="role-swatch" style="background:${hex}"></div>
            <div class="role-name">${label}</div>
            <div class="role-count">${count}</div>
        </div>`;
    });

    let notesHTML = '';
    if (notes.length) {
        notesHTML = '<ul class="notes-list">' + notes.map(n => `<li>${n}</li>`).join('') + '</ul>';
    }

    document.getElementById('tab-summary').innerHTML = `
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-label">Tipo</div>
                <div class="stat-value small">${(spec.furniture_type || '?').replace(/_/g, ' ')}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Material</div>
                <div class="stat-value small">${spec.material || '?'}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Dimensiones</div>
                <div class="stat-value small">${dims.width || '?'}×${dims.height || '?'}×${dims.depth || '?'} cm</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Partes</div>
                <div class="stat-value">${parts.length}</div>
            </div>
        </div>
        <div class="stat-card wide" style="margin-bottom:12px">
            <div class="stat-label">Desglose por rol</div>
            <div class="role-list">${roleHTML}</div>
        </div>
        ${hw.length ? `<div class="stat-card wide" style="margin-bottom:12px">
            <div class="stat-label">Hardware</div>
            <div class="stat-value small">${hw.length} items</div>
        </div>` : ''}
        ${notesHTML ? `<div class="stat-card wide">
            <div class="stat-label">Notas</div>
            ${notesHTML}
        </div>` : ''}
    `;
}

function updateParts(spec) {
    const parts = spec.parts || [];
    let rows = parts.map(p => {
        return `<tr data-id="${p.id}">
            <td>${p.id}</td>
            <td>${ROLE_LABELS[p.role] || p.role}</td>
            <td>${p.width_mm}×${p.height_mm}×${p.thickness_mm}</td>
        </tr>`;
    }).join('');

    document.getElementById('tab-parts').innerHTML = `
        <table class="parts-table">
            <thead><tr><th>ID</th><th>Rol</th><th>Dimensiones (mm)</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;

    // Click on table row → select in 3D
    document.querySelectorAll('.parts-table tr[data-id]').forEach(row => {
        row.addEventListener('click', () => {
            const mesh = meshes.find(m => m.userData.partId === row.dataset.id);
            if (mesh) {
                selectPart(mesh);
                // Center camera on part
                const pos = mesh.position.clone();
                controls.target.lerp(pos, 0.5);
                controls.update();
            }
        });
    });
}

function updateHistory(activeIdx) {
    let html = '';
    iterations.forEach((iter, i) => {
        const spec = iter.spec;
        const nParts = (spec.parts || []).length;
        const dims = spec.dimensions_cm || {};
        html += `<div class="history-item${i === activeIdx ? ' active' : ''}" data-idx="${i}">
            <div class="history-header">
                <span class="history-name">${iter.name}</span>
                <span class="history-time">${iter.timestamp.replace('T', ' ')}</span>
            </div>
            ${iter.comment ? `<div class="history-comment">${iter.comment}</div>` : ''}
            <div class="history-stats">${nParts} partes · ${dims.width||'?'}×${dims.height||'?'}×${dims.depth||'?'}cm · ${spec.material||'?'}</div>
        </div>`;
    });
    document.getElementById('tab-history').innerHTML = html;

    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            updateUI(parseInt(item.dataset.idx));
        });
    });
}

// ============================================================
// Iteration slider
// ============================================================
document.getElementById('iter-slider').addEventListener('input', e => {
    updateUI(parseInt(e.target.value));
});

// ============================================================
// Resize
// ============================================================
function onResize() {
    const w = viewport.clientWidth;
    const h = viewport.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
}
window.addEventListener('resize', onResize);

// ============================================================
// Render loop
// ============================================================
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// ============================================================
// Init
// ============================================================
onResize();
updateUI(currentIdx);
animate();
</script>
</body>
</html>
"""
