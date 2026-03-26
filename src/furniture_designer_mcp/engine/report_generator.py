"""Generate interactive HTML design reports with 3D visualization.

Produces a self-contained HTML file with:
- Three.js 3D viewer (orbit/zoom/pan) using ES Modules
- Light minimal aesthetic (DM Sans, product-card style)
- 4 pages: Diseno, Partes, Cortes, Historial
- Iteration history with slider
- Panel inspection on click
- Summary sidebar, parts table, cut optimization, assembly guide
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
    cut_data: dict | None = None,
) -> str:
    """Generate or update an interactive HTML design report.

    If output_path points to an existing report, appends a new iteration.
    Otherwise creates a fresh report.

    Extra data (cut_data, bom_data, assembly_data) can be passed either
    as explicit parameters or embedded inside the spec dict.  When embedded,
    they are extracted automatically so the spec stays clean.

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

    # Extract extra data from spec if embedded
    effective_cut_data = cut_data
    if effective_cut_data is None and "cut_data" in spec:
        effective_cut_data = spec.pop("cut_data")

    bom_data = spec.pop("bom_data", None)
    assembly_data = spec.pop("assembly_data", None)

    # Append new iteration
    iteration_entry = {
        "name": iteration_name or f"v{len(iterations) + 1}",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "comment": comment,
        "spec": spec,
    }
    if effective_cut_data is not None:
        iteration_entry["cut_data"] = effective_cut_data
    if bom_data is not None:
        iteration_entry["bom_data"] = bom_data
    if assembly_data is not None:
        iteration_entry["assembly_data"] = assembly_data
    iterations.append(iteration_entry)

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
<script id="iterations-data" type="application/json">__ITERATIONS_JSON__</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
/* ============================================================
   DESIGN TOKENS - Light Minimal
   ============================================================ */
:root {
    --bg-base: #f8f9fb;
    --bg-white: #ffffff;
    --bg-card: #ffffff;
    --bg-card-hover: #f3f4f6;
    --bg-subtle: #f1f3f5;
    --bg-input: #f8f9fb;
    --bg-viewport: #f0f2f5;

    --accent: #2563eb;
    --accent-light: rgba(37, 99, 235, 0.08);
    --accent-medium: rgba(37, 99, 235, 0.15);
    --accent-green: #059669;
    --accent-amber: #d97706;
    --accent-red: #dc2626;

    --text-primary: #111827;
    --text-secondary: #4b5563;
    --text-dim: #9ca3af;
    --text-muted: #d1d5db;

    --border: #e5e7eb;
    --border-strong: #d1d5db;
    --border-focus: var(--accent);

    --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
    --shadow-lg: 0 8px 24px rgba(0,0,0,0.08);

    --radius: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;
}

/* ============================================================
   RESET & BASE
   ============================================================ */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: var(--bg-base);
    font-family: 'DM Sans', -apple-system, sans-serif;
    color: var(--text-primary);
    height: 100vh;
    overflow: hidden;
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}
code, .mono {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
}

/* ============================================================
   SCROLLBAR
   ============================================================ */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-strong); }

/* ============================================================
   LAYOUT
   ============================================================ */
#app {
    display: grid;
    grid-template-rows: 56px 1fr;
    grid-template-columns: 1fr;
    height: 100vh;
}

/* ============================================================
   HEADER
   ============================================================ */
#header {
    background: var(--bg-white);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 24px;
    gap: 16px;
    z-index: 20;
    box-shadow: var(--shadow-sm);
}
.header-brand {
    display: flex;
    align-items: center;
    gap: 10px;
}
.header-logo {
    width: 32px;
    height: 32px;
    border-radius: var(--radius);
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 15px;
    font-weight: 600;
}
.header-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.01em;
}
.header-sep {
    width: 1px;
    height: 24px;
    background: var(--border);
}
.header-design-name {
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary);
}
.header-design-meta {
    font-size: 12px;
    color: var(--text-dim);
    font-family: 'JetBrains Mono', monospace;
    font-weight: 400;
}

/* Nav tabs in header */
.header-nav {
    display: flex;
    gap: 2px;
    margin-left: 32px;
    background: var(--bg-subtle);
    padding: 3px;
    border-radius: var(--radius);
}
.nav-btn {
    padding: 6px 16px;
    border: none;
    background: none;
    border-radius: 6px;
    font-family: inherit;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s;
}
.nav-btn:hover { color: var(--text-primary); }
.nav-btn.active {
    background: var(--bg-white);
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
}

/* Version pill */
.version-pill {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 10px;
}
.version-pill label {
    font-size: 12px;
    color: var(--text-dim);
    font-weight: 500;
}
#iter-slider {
    -webkit-appearance: none;
    width: 100px;
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    outline: none;
}
#iter-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    border: 2px solid var(--bg-white);
    box-shadow: 0 0 0 1px var(--accent), var(--shadow-sm);
}
#iter-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
    min-width: 24px;
}

/* Status dot */
.status-live {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--accent-green);
    font-weight: 500;
}
.status-live::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent-green);
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ============================================================
   MAIN CONTENT AREA
   ============================================================ */
#main-content {
    overflow: hidden;
    position: relative;
}

/* ============================================================
   PAGE: DESIGN (3D assembled view)
   ============================================================ */
.page { display: none; height: 100%; }
.page.active { display: flex; }

#page-design {
    flex-direction: row;
}
.viewport-area {
    flex: 1;
    position: relative;
    background: var(--bg-viewport);
    overflow: hidden;
}
.viewport-area canvas {
    display: block;
    width: 100%;
    height: 100%;
}

/* Viewport overlay badges */
.viewport-badge {
    position: absolute;
    bottom: 16px;
    left: 16px;
    display: flex;
    gap: 6px;
}
.badge {
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 5px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--text-secondary);
    box-shadow: var(--shadow-sm);
}
.badge strong { color: var(--text-primary); font-weight: 600; }

/* Section labels */
.section-labels-container {
    position: absolute;
    bottom: 54px;
    left: 16px;
    display: flex;
    gap: 8px;
}
.section-label {
    padding: 4px 12px;
    background: rgba(255,255,255,0.9);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--accent);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    box-shadow: var(--shadow-sm);
}
.section-label:hover {
    border-color: var(--accent);
    background: var(--accent-light);
}

/* -- Summary sidebar -- */
.summary-panel {
    width: 340px;
    background: var(--bg-white);
    border-left: 1px solid var(--border);
    overflow-y: auto;
    padding: 24px;
}
.summary-section {
    margin-bottom: 24px;
}
.summary-section:last-child { margin-bottom: 0; }
.section-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

/* Spec grid */
.spec-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}
.spec-item {
    background: var(--bg-subtle);
    border-radius: var(--radius);
    padding: 12px;
}
.spec-item.wide { grid-column: span 2; }
.spec-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.spec-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 500;
    color: var(--text-primary);
    line-height: 1.2;
}
.spec-value.sm { font-size: 14px; }
.spec-value.xs { font-size: 12px; color: var(--text-secondary); }
.spec-unit {
    font-size: 12px;
    color: var(--text-dim);
    font-weight: 400;
}

/* Role breakdown */
.role-list { list-style: none; }
.role-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid var(--bg-subtle);
    font-size: 13px;
    cursor: pointer;
    transition: background 0.1s;
}
.role-row:hover { background: var(--bg-subtle); margin: 0 -12px; padding: 8px 12px; border-radius: 6px; }
.role-row:last-child { border-bottom: none; }
.role-swatch {
    width: 10px;
    height: 10px;
    border-radius: 3px;
    flex-shrink: 0;
}
.role-name {
    flex: 1;
    color: var(--text-secondary);
}
.role-count {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
    color: var(--text-primary);
    font-size: 13px;
}

/* Hardware list */
.hw-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 13px;
    border-bottom: 1px solid var(--bg-subtle);
}
.hw-row:last-child { border-bottom: none; }
.hw-name { color: var(--text-secondary); }
.hw-qty { font-family: 'JetBrains Mono', monospace; font-weight: 500; color: var(--text-primary); }

/* Notes */
.note-item {
    font-size: 13px;
    color: var(--text-secondary);
    padding: 6px 0;
    border-bottom: 1px solid var(--bg-subtle);
    line-height: 1.6;
}
.note-item:last-child { border-bottom: none; }
.note-icon {
    display: inline-block;
    width: 16px;
    height: 16px;
    text-align: center;
    margin-right: 6px;
    font-size: 12px;
}

/* ============================================================
   PAGE: PARTS (Exploded 3D + parts table + assembly)
   ============================================================ */
#page-parts {
    flex-direction: row;
}
.parts-sidebar {
    width: 420px;
    background: var(--bg-white);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.parts-sidebar-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
}

/* Parts search */
.parts-search {
    width: 100%;
    background: var(--bg-subtle);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 14px;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 13px;
    outline: none;
    margin-bottom: 16px;
    transition: border-color 0.15s;
}
.parts-search:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-light); }
.parts-search::placeholder { color: var(--text-muted); }

/* Parts table */
.parts-table {
    width: 100%;
    font-size: 13px;
    border-collapse: collapse;
    margin-bottom: 32px;
}
.parts-table th {
    text-align: left;
    padding: 8px 8px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-dim);
    border-bottom: 2px solid var(--border);
    position: sticky;
    top: 0;
    background: var(--bg-white);
}
.parts-table td {
    padding: 8px 8px;
    border-bottom: 1px solid var(--bg-subtle);
    color: var(--text-secondary);
}
.parts-table tr[data-id] {
    cursor: pointer;
    transition: background 0.1s;
}
.parts-table tr[data-id]:hover { background: var(--bg-subtle); }
.parts-table tr.selected {
    background: var(--accent-light);
}
.parts-table tr.selected td { color: var(--accent); font-weight: 500; }
.part-role-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 3px;
    margin-right: 6px;
    vertical-align: middle;
}

/* Exploded view label */
.viewport-label {
    position: absolute;
    top: 16px;
    left: 16px;
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
}
.viewport-label .label-tag {
    display: inline-block;
    background: var(--accent-light);
    color: var(--accent);
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 8px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ============================================================
   ASSEMBLY GUIDE
   ============================================================ */
.assembly-section {
    border-top: 2px solid var(--border);
    padding-top: 20px;
}
.assembly-step {
    display: flex;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid var(--bg-subtle);
}
.assembly-step:last-child { border-bottom: none; }
.step-number {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--accent-light);
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 13px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.step-content {
    flex: 1;
}
.step-title {
    font-weight: 500;
    color: var(--text-primary);
    font-size: 13px;
    margin-bottom: 3px;
}
.step-detail {
    font-size: 12px;
    color: var(--text-dim);
    line-height: 1.5;
}
.step-hardware {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--bg-subtle);
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 4px;
}

/* ============================================================
   PAGE: CUTS (full-width, no 3D)
   ============================================================ */
#page-cuts {
    flex-direction: column;
    overflow-y: auto;
    padding: 32px 48px;
    background: var(--bg-base);
}

.cuts-header {
    display: flex;
    align-items: center;
    gap: 24px;
    margin-bottom: 28px;
}
.cuts-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
}
.cuts-stats {
    display: flex;
    gap: 8px;
    margin-left: auto;
}
.cut-stat-pill {
    background: var(--bg-white);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 20px;
    text-align: center;
    box-shadow: var(--shadow-sm);
}
.cut-stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: var(--text-primary);
}
.cut-stat-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-dim);
    font-weight: 500;
    margin-top: 2px;
}

.sheets-list {
    display: flex;
    flex-direction: column;
    gap: 24px;
}
.sheet-card {
    background: var(--bg-white);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
}
.sheet-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-subtle);
}
.sheet-card-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
}
.sheet-card-meta {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: var(--text-dim);
}
.sheet-card-meta strong { color: var(--text-primary); font-weight: 600; }
.sheet-card-body {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
}
.sheet-visual {
    padding: 20px;
    border-right: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
}
.sheet-svg {
    width: 100%;
    border-radius: var(--radius);
    overflow: hidden;
}
.sheet-details {
    padding: 0;
    display: flex;
    flex-direction: column;
}

/* Piece colors for SVGs */
.piece-side { fill: rgba(180,140,100,0.25); stroke: rgb(180,140,100); }
.piece-bottom { fill: rgba(160,130,100,0.25); stroke: rgb(160,130,100); }
.piece-top_panel { fill: rgba(160,130,100,0.25); stroke: rgb(160,130,100); }
.piece-divider { fill: rgba(200,160,80,0.25); stroke: rgb(200,160,80); }
.piece-shelf { fill: rgba(80,160,100,0.25); stroke: rgb(80,160,100); }
.piece-back { fill: rgba(160,160,160,0.2); stroke: rgb(160,160,160); }
.piece-door { fill: rgba(80,130,200,0.25); stroke: rgb(80,130,200); }
.piece-rail { fill: rgba(140,115,85,0.25); stroke: rgb(140,115,85); }
.piece-kickplate { fill: rgba(120,120,120,0.2); stroke: rgb(120,120,120); }
.piece-drawer { fill: rgba(80,130,200,0.25); stroke: rgb(80,130,200); }
.piece-drawer_front { fill: rgba(80,130,200,0.25); stroke: rgb(80,130,200); }
.piece-drawer_side { fill: rgba(180,155,120,0.25); stroke: rgb(180,155,120); }
.piece-drawer_back { fill: rgba(160,140,110,0.25); stroke: rgb(160,140,110); }
.piece-drawer_bottom { fill: rgba(190,180,160,0.25); stroke: rgb(190,180,160); }
.piece-back_rail { fill: rgba(140,115,85,0.25); stroke: rgb(140,115,85); }

/* Sheet pieces table */
.sheet-pieces-table {
    width: 100%;
    font-size: 12px;
    border-collapse: collapse;
    flex: 1;
}
.sheet-pieces-table th {
    text-align: left;
    padding: 8px 12px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    background: var(--bg-subtle);
    position: sticky;
    top: 0;
}
.sheet-pieces-table td {
    padding: 7px 12px;
    border-bottom: 1px solid var(--bg-subtle);
    color: var(--text-secondary);
}
.sheet-pieces-table tr:last-child td { border-bottom: none; }
.sheet-pieces-table .mono {
    font-size: 11px;
}

/* Edge banding indicator */
.edge-band {
    display: inline-flex;
    gap: 3px;
}
.edge-indicator {
    width: 18px;
    height: 18px;
    position: relative;
    display: inline-block;
}
.edge-indicator svg {
    width: 18px;
    height: 18px;
}

/* Usage bar */
.sheet-usage-bar {
    padding: 12px 20px;
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--bg-subtle);
}
.usage-track {
    flex: 1;
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    overflow: hidden;
}
.usage-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s;
}
.usage-fill.good { background: var(--accent-green); }
.usage-fill.ok { background: var(--accent-amber); }
.usage-fill.bad { background: var(--accent-red); }
.usage-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    white-space: nowrap;
}

/* Legend */
.cuts-legend {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-secondary);
}
.legend-swatch {
    width: 12px;
    height: 12px;
    border-radius: 3px;
}
/* Edge banding legend */
.edge-legend {
    display: flex;
    gap: 20px;
    margin-top: 12px;
    font-size: 12px;
    color: var(--text-dim);
}
.edge-legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
}
.edge-legend-line {
    width: 16px;
    height: 3px;
    border-radius: 1px;
}
.edge-legend-line.active { background: var(--accent); }
.edge-legend-line.inactive { background: var(--border); }

/* No data placeholder */
.no-data {
    text-align: center;
    padding: 48px 24px;
    color: var(--text-dim);
    font-size: 14px;
}
.no-data-icon { font-size: 32px; margin-bottom: 12px; }

/* ============================================================
   PAGE: HISTORY
   ============================================================ */
#page-history {
    flex-direction: column;
    overflow-y: auto;
    padding: 32px 48px;
    max-width: 720px;
    margin: 0 auto;
    width: 100%;
}
.history-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 24px;
}
.timeline {
    position: relative;
    padding-left: 28px;
}
.timeline::before {
    content: '';
    position: absolute;
    left: 8px;
    top: 8px;
    bottom: 8px;
    width: 2px;
    background: var(--border);
    border-radius: 1px;
}
.history-item {
    position: relative;
    background: var(--bg-white);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 18px 20px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.15s;
    box-shadow: var(--shadow-sm);
}
.history-item:hover { border-color: var(--border-strong); box-shadow: var(--shadow-md); }
.history-item.active {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-light);
}
.history-item::before {
    content: '';
    position: absolute;
    left: -24px;
    top: 22px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--border);
    border: 2px solid var(--bg-base);
}
.history-item.active::before {
    background: var(--accent);
}
.history-header {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 6px;
}
.history-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}
.history-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--text-muted);
    margin-left: auto;
}
.history-comment {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
}
.history-changes {
    margin-top: 8px;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}
.change-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 500;
}
.change-badge.added {
    background: rgba(5, 150, 105, 0.08);
    color: var(--accent-green);
    border: 1px solid rgba(5, 150, 105, 0.2);
}
.change-badge.removed {
    background: rgba(220, 38, 38, 0.06);
    color: var(--accent-red);
    border: 1px solid rgba(220, 38, 38, 0.15);
}
.change-badge.modified {
    background: rgba(217, 119, 6, 0.08);
    color: var(--accent-amber);
    border: 1px solid rgba(217, 119, 6, 0.15);
}
.history-stats {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 8px;
}

/* ============================================================
   TOOLTIP
   ============================================================ */
#tooltip {
    position: fixed;
    display: none;
    background: var(--bg-white);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 14px 18px;
    font-size: 13px;
    z-index: 100;
    pointer-events: none;
    max-width: 280px;
    box-shadow: var(--shadow-lg);
}
.tt-title {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 13px;
    margin-bottom: 8px;
}
.tt-row {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 3px 0;
}
.tt-label { color: var(--text-dim); font-size: 12px; }
.tt-value {
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 500;
}
</style>
</head>
<body>
<div id="app">
    <!-- HEADER -->
    <header id="header">
        <div class="header-brand">
            <div class="header-logo">FD</div>
            <div>
                <div class="header-title" id="hdr-title">Design Report</div>
                <div class="header-design-meta" id="hdr-meta"></div>
            </div>
        </div>

        <nav class="header-nav">
            <button class="nav-btn active" data-page="design">Dise&#241;o</button>
            <button class="nav-btn" data-page="parts">Partes</button>
            <button class="nav-btn" data-page="cuts">Cortes</button>
            <button class="nav-btn" data-page="history">Historial</button>
        </nav>

        <div class="version-pill">
            <label>Iteraci&#243;n</label>
            <input type="range" id="iter-slider" min="0" max="0" value="0">
            <span id="iter-label">v1</span>
        </div>

        <div class="status-live">Live</div>
    </header>

    <!-- MAIN CONTENT -->
    <div id="main-content">

        <!-- PAGE: DESIGN -->
        <div id="page-design" class="page active">
            <div class="viewport-area" id="viewport-design">
                <div class="section-labels-container" id="section-labels"></div>
                <div class="viewport-badge" id="design-badges"></div>
                <canvas id="canvas-design"></canvas>
            </div>
            <aside class="summary-panel" id="summary-panel"></aside>
        </div>

        <!-- PAGE: PARTS -->
        <div id="page-parts" class="page">
            <div class="viewport-area" id="viewport-parts">
                <div class="viewport-label">Vista explosionada <span class="label-tag">Exploded</span></div>
                <canvas id="canvas-parts"></canvas>
            </div>
            <aside class="parts-sidebar">
                <div class="parts-sidebar-scroll">
                    <input type="text" class="parts-search" id="parts-search" placeholder="Buscar parte...">
                    <table class="parts-table" id="parts-table">
                        <thead><tr><th>Parte</th><th>Rol</th><th>Dimensiones (mm)</th></tr></thead>
                        <tbody id="parts-tbody"></tbody>
                    </table>
                    <div id="assembly-container"></div>
                </div>
            </aside>
        </div>

        <!-- PAGE: CUTS -->
        <div id="page-cuts" class="page">
            <div class="cuts-header">
                <div class="cuts-title">Optimizaci&#243;n de cortes</div>
                <div class="cuts-stats" id="cuts-stats"></div>
            </div>
            <div class="sheets-list" id="sheets-list"></div>
            <div id="cuts-legend-container"></div>
        </div>

        <!-- PAGE: HISTORY -->
        <div id="page-history" class="page">
            <div class="history-title">Historial de iteraciones</div>
            <div class="timeline" id="history-timeline"></div>
        </div>

    </div>
</div>

<!-- Tooltip -->
<div id="tooltip"></div>

<!-- Three.js (ES Modules) -->
<script type="importmap">
{ "imports": {
    "three": "https://unpkg.com/three@0.169.0/build/three.module.js",
    "three/addons/": "https://unpkg.com/three@0.169.0/examples/jsm/"
}}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ============================================================
// Data & State
// ============================================================
var iterations = JSON.parse(
    document.getElementById('iterations-data').textContent
);
var currentIdx = iterations.length - 1;

// ============================================================
// Role colors (hex for 3D)
// ============================================================
var ROLE_COLORS = {
    side: 0xb8860b, top_panel: 0xcd853f, bottom: 0xdeb887,
    shelf: 0xd2b48c, divider: 0xbc8f5f, door: 0x8fbc8f,
    back: 0xa0a0a0, drawer_front: 0x8fbc8f, drawer_side: 0xc4a882,
    drawer_back: 0xb8a080, drawer_bottom: 0xd0c8b8,
    rail: 0x909090, back_rail: 0x909090, kickplate: 0x808080, kickplate_return: 0x808080,
    floor: 0xdeb887,
};
var DEFAULT_ROLE_COLOR = 0xc4a060;

// Role colors as RGB arrays for CSS
var ROLE_RGB = {
    side: [180,140,100], top_panel: [160,130,100], bottom: [160,130,100],
    shelf: [80,160,100], divider: [200,160,80], door: [80,130,200],
    back: [160,160,160], drawer_front: [80,130,200], drawer_side: [180,155,120],
    drawer_back: [160,140,110], drawer_bottom: [190,180,160],
    rail: [140,115,85], back_rail: [140,115,85], kickplate: [120,120,120], kickplate_return: [120,120,120],
    floor: [160,130,100],
};

// SVG piece class map
var ROLE_SVG_CLASS = {
    side: 'piece-side', top_panel: 'piece-top_panel', bottom: 'piece-bottom',
    shelf: 'piece-shelf', divider: 'piece-divider', door: 'piece-door',
    back: 'piece-back', drawer_front: 'piece-drawer_front',
    drawer_side: 'piece-drawer_side', drawer_back: 'piece-drawer_back',
    drawer_bottom: 'piece-drawer_bottom',
    rail: 'piece-rail', back_rail: 'piece-back_rail', kickplate: 'piece-kickplate', kickplate_return: 'piece-kickplate',
    floor: 'piece-bottom',
};

var ROLE_LABELS = {
    side: 'Lateral', bottom: 'Piso', top_panel: 'Tapa',
    floor: 'Piso int.', shelf: 'Repisa', back: 'Respaldo',
    door: 'Puerta', rail: 'Travesa\u00f1o', back_rail: 'Travesa\u00f1o post.',
    kickplate: 'Z\u00f3calo', kickplate_return: 'Retorno z\u00f3calo', divider: 'Divisi\u00f3n',
    drawer_front: 'Frente caj\u00f3n', drawer_side: 'Lat. caj\u00f3n',
    drawer_back: 'Tras. caj\u00f3n', drawer_bottom: 'Fondo caj\u00f3n',
};

var EDGE_COLOR = 0x94a3b8;

// ============================================================
// Box dimension mapping (matches _box_dims in freecad_scripts.py)
// ============================================================
function boxDims(part) {
    var w = part.width_mm, h = part.height_mm, t = part.thickness_mm;
    var role = part.role;
    if (role === 'side' || role === 'divider') return [t, w, h];
    if (['bottom','top_panel','shelf','floor'].indexOf(role) >= 0) return [w, h, t];
    if (role === 'back') return [w, t, h];
    if (role === 'door' || role === 'drawer_front') return [w, t, h];
    if (role === 'drawer_side') return [t, w, h];
    if (role === 'drawer_back') return [w, t, h];
    if (role === 'drawer_bottom') return [w, h, t];
    if (role === 'rail' || role === 'back_rail' || role === 'kickplate') return [w, t, h];
    if (role === 'kickplate_return') return [t, w, h];
    return [w, h, t];
}

// Explosion offsets by role
var EXPLOSION_OFFSET = {
    side: {x:0,y:0,z:0}, bottom: {x:0,y:-120,z:0}, top_panel: {x:0,y:120,z:0},
    divider: {x:0,y:60,z:0}, shelf: {x:0,y:40,z:0}, back: {x:0,y:0,z:200},
    door: {x:0,y:0,z:-250}, rail: {x:0,y:100,z:0}, back_rail: {x:0,y:100,z:0},
    kickplate: {x:0,y:-180,z:0}, kickplate_return: {x:0,y:-180,z:0}, drawer_front: {x:0,y:0,z:-300},
    drawer_side: {x:0,y:0,z:-150}, drawer_back: {x:0,y:0,z:-100},
    drawer_bottom: {x:0,y:-60,z:-150}, floor: {x:0,y:-120,z:0},
};

// ============================================================
// Build 3D scene helper
// ============================================================
function buildScene(canvasId, containerId, exploded) {
    var container = document.getElementById(containerId);
    var canvas = document.getElementById(canvasId);
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0xf0f2f5);

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(35, 1, 1, 100000);
    var controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.5;

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    var dLight = new THREE.DirectionalLight(0xffffff, 0.6);
    dLight.position.set(1, 1.5, 1);
    scene.add(dLight);
    var bLight = new THREE.DirectionalLight(0xddeeff, 0.2);
    bLight.position.set(-1, 0.5, -1);
    scene.add(bLight);

    var group = null;
    var meshes = [];
    var selected = null;
    var raycaster = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
    var gridHelper = null;

    function buildFromParts(parts) {
        // Clear previous
        if (group) scene.remove(group);
        if (gridHelper) scene.remove(gridHelper);
        group = new THREE.Group();
        meshes = [];
        selected = null;

        parts.forEach(function(part) {
            var dims = boxDims(part);
            var fcX = dims[0], fcY = dims[1], fcZ = dims[2];
            // Three.js: X=fcX, Y=fcZ(height), Z=fcY(depth)
            var geom = new THREE.BoxGeometry(fcX, fcZ, fcY);
            var hex = ROLE_COLORS[part.role] || DEFAULT_ROLE_COLOR;
            var mat = new THREE.MeshPhysicalMaterial({
                color: hex,
                transparent: true,
                opacity: 0.7,
                roughness: 0.5,
                metalness: 0.02,
            });
            var mesh = new THREE.Mesh(geom, mat);

            // Edge lines
            var edges = new THREE.EdgesGeometry(geom);
            var lineMat = new THREE.LineBasicMaterial({
                color: EDGE_COLOR,
                transparent: true,
                opacity: 0.35,
            });
            mesh.add(new THREE.LineSegments(edges, lineMat));

            // Position
            var pos = part.position_mm || {x:0, y:0, z:0};
            var px = pos.x + fcX / 2;
            var py = pos.z + fcZ / 2;
            var pz = pos.y + fcY / 2;

            if (exploded) {
                var off = EXPLOSION_OFFSET[part.role] || {x:0,y:0,z:0};
                px += off.x;
                py += off.y;
                pz += off.z;
            }

            mesh.position.set(px, py, pz);
            mesh.userData = {
                partId: part.id,
                role: part.role,
                width_mm: part.width_mm,
                height_mm: part.height_mm,
                thickness_mm: part.thickness_mm,
                edge_banding: part.edge_banding || [],
                position_mm: pos,
            };

            group.add(mesh);
            meshes.push(mesh);
        });

        scene.add(group);

        // Camera
        var box = new THREE.Box3().setFromObject(group);
        var center = box.getCenter(new THREE.Vector3());
        var size = box.getSize(new THREE.Vector3());
        var maxDim = Math.max(size.x, size.y, size.z);
        controls.target.copy(center);
        camera.position.set(
            center.x + maxDim * 0.8,
            center.y + maxDim * 0.5,
            center.z + maxDim * 1.0
        );
        controls.update();

        // Grid
        var gridSize = Math.ceil(maxDim / 500) * 500 + 500;
        var divs = Math.round(gridSize / 100);
        gridHelper = new THREE.GridHelper(gridSize, divs, 0xdee2e6, 0xeceff2);
        gridHelper.material.transparent = true;
        gridHelper.material.opacity = 0.5;
        scene.add(gridHelper);
    }

    // Click interaction
    canvas.addEventListener('click', function(e) {
        var rect = canvas.getBoundingClientRect();
        mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        var hits = raycaster.intersectObjects(meshes);

        if (selected) {
            selected.material.emissive.setHex(0x000000);
            selected.material.opacity = 0.7;
            selected.children[0].material.color.setHex(EDGE_COLOR);
            selected.children[0].material.opacity = 0.35;
        }

        var tooltip = document.getElementById('tooltip');
        if (hits.length > 0) {
            selected = hits[0].object;
            selected.material.emissive.setHex(0x111111);
            selected.material.opacity = 0.9;
            selected.children[0].material.color.setHex(0x2563eb);
            selected.children[0].material.opacity = 0.6;

            var d = selected.userData;
            var label = ROLE_LABELS[d.role] || d.role;
            var edgeStr = Array.isArray(d.edge_banding) ? (d.edge_banding.join(', ') || '\u2014') : (d.edge_banding || '\u2014');
            tooltip.innerHTML =
                '<div class="tt-title">' + label + ' \u2014 ' + d.partId + '</div>' +
                '<div class="tt-row"><span class="tt-label">Dimensiones</span><span class="tt-value">' + d.width_mm + ' \u00d7 ' + d.height_mm + ' \u00d7 ' + d.thickness_mm + ' mm</span></div>' +
                '<div class="tt-row"><span class="tt-label">Posici\u00f3n</span><span class="tt-value">(' + d.position_mm.x + ', ' + d.position_mm.y + ', ' + d.position_mm.z + ')</span></div>' +
                '<div class="tt-row"><span class="tt-label">Canteado</span><span class="tt-value">' + edgeStr + '</span></div>';
            tooltip.style.display = 'block';
            var tx = Math.min(e.clientX + 16, window.innerWidth - 300);
            var ty = Math.min(e.clientY + 16, window.innerHeight - 140);
            tooltip.style.left = tx + 'px';
            tooltip.style.top = ty + 'px';

            // Highlight in parts table
            document.querySelectorAll('.parts-table tr[data-id]').forEach(function(r) {
                r.classList.toggle('selected', r.dataset.id === d.partId);
            });
        } else {
            selected = null;
            tooltip.style.display = 'none';
            document.querySelectorAll('.parts-table tr.selected').forEach(function(r) {
                r.classList.remove('selected');
            });
        }
    });

    canvas.addEventListener('mousemove', function() {
        document.getElementById('tooltip').style.display = 'none';
    });

    // Resize
    function resize() {
        var w = container.clientWidth;
        var h = container.clientHeight;
        if (w === 0 || h === 0) return;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    }

    // Animate
    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();

    return {
        resize: resize,
        buildFromParts: buildFromParts,
        getMeshes: function() { return meshes; },
        getControls: function() { return controls; },
    };
}

// ============================================================
// Initialize scenes
// ============================================================
var designScene = buildScene('canvas-design', 'viewport-design', false);
var partsScene = buildScene('canvas-parts', 'viewport-parts', true);

// ============================================================
// Navigation
// ============================================================
var navBtns = document.querySelectorAll('.nav-btn');
var pages = document.querySelectorAll('.page');

navBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
        navBtns.forEach(function(b) { b.classList.remove('active'); });
        pages.forEach(function(p) { p.classList.remove('active'); });
        btn.classList.add('active');
        var page = document.getElementById('page-' + btn.dataset.page);
        page.classList.add('active');
        setTimeout(function() {
            if (btn.dataset.page === 'design') designScene.resize();
            if (btn.dataset.page === 'parts') partsScene.resize();
        }, 10);
    });
});

// ============================================================
// Edge banding SVG helper
// ============================================================
function edgeBandingSvg(edgeList) {
    if (!edgeList || !Array.isArray(edgeList) || edgeList.length === 0) {
        return '<svg width="20" height="20" viewBox="0 0 20 20" style="vertical-align:middle">' +
            '<rect x="2" y="2" width="16" height="16" fill="none" stroke="#e5e7eb" stroke-width="1" rx="1"/>' +
            '</svg><span style="font-size:11px;color:var(--text-muted)">\u2014</span>';
    }

    var edges = edgeList.map(function(e) { return (typeof e === 'string' ? e : '').toLowerCase(); });
    var hasTop = edges.indexOf('top') >= 0;
    var hasBottom = edges.indexOf('bottom') >= 0;
    var hasLeft = edges.indexOf('left') >= 0 || edges.indexOf('front') >= 0;
    var hasRight = edges.indexOf('right') >= 0 || edges.indexOf('back') >= 0;
    var allFour = edgeList.length >= 4;

    if (allFour) {
        return '<svg width="20" height="20" viewBox="0 0 20 20" style="vertical-align:middle">' +
            '<rect x="2" y="2" width="16" height="16" fill="none" stroke="#2563eb" stroke-width="2" rx="1"/>' +
            '</svg><span style="font-size:11px;color:var(--text-dim)">4 lados</span>';
    }

    var svg = '<svg width="20" height="20" viewBox="0 0 20 20" style="vertical-align:middle">' +
        '<rect x="2" y="2" width="16" height="16" fill="none" stroke="#e5e7eb" stroke-width="1" rx="1"/>';
    if (hasTop) svg += '<line x1="2" y1="2" x2="18" y2="2" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>';
    if (hasBottom) svg += '<line x1="2" y1="18" x2="18" y2="18" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>';
    if (hasLeft) svg += '<line x1="2" y1="2" x2="2" y2="18" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>';
    if (hasRight) svg += '<line x1="18" y1="2" x2="18" y2="18" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>';
    svg += '</svg>';

    var label = edgeList.join(', ');
    return svg + '<span style="font-size:11px;color:var(--text-dim)">' + label + '</span>';
}

// ============================================================
// Update UI from iteration
// ============================================================
function updateUI(idx) {
    currentIdx = idx;
    var iter = iterations[idx];
    var spec = iter.spec;
    var parts = spec.parts || [];
    var dims = spec.dimensions_cm || {};
    var dimsMm = spec.dimensions_mm || {};
    var hw = spec.hardware || [];
    var notes = spec.notes || [];

    // Header
    var ftype = (spec.furniture_type || 'Mueble').replace(/_/g, ' ');
    var ftypeCap = ftype.charAt(0).toUpperCase() + ftype.slice(1);
    document.getElementById('hdr-title').textContent = ftypeCap;
    document.getElementById('hdr-meta').textContent =
        ftype + ' \u00b7 ' + (dims.width || '?') + '\u00d7' + (dims.height || '?') + '\u00d7' + (dims.depth || '?') + ' cm \u00b7 ' + (spec.material || '?');

    // Slider
    var slider = document.getElementById('iter-slider');
    slider.max = iterations.length - 1;
    slider.value = idx;
    document.getElementById('iter-label').textContent = iter.name;

    // Build 3D
    designScene.buildFromParts(parts);
    partsScene.buildFromParts(parts);

    // Design page: badges
    document.getElementById('design-badges').innerHTML =
        '<div class="badge"><strong>' + (dims.width || '?') + '</strong> \u00d7 <strong>' + (dims.height || '?') + '</strong> \u00d7 <strong>' + (dims.depth || '?') + '</strong> cm</div>' +
        '<div class="badge"><strong>' + parts.length + '</strong> partes</div>' +
        '<div class="badge">' + (spec.material || '?') + ' <strong>' + (spec.material_thickness_mm || '?') + 'mm</strong></div>';

    // Section labels
    var sectionLabels = spec.section_labels || {};
    var slHtml = '';
    Object.keys(sectionLabels).forEach(function(key) {
        var sl = sectionLabels[key];
        var label = sl.label_es || key;
        slHtml += '<div class="section-label">' + key + ' \u00b7 ' + label + '</div>';
    });
    document.getElementById('section-labels').innerHTML = slHtml;

    // Summary panel
    updateSummary(spec, parts, dims, hw, notes);

    // Parts table
    updatePartsTable(parts);

    // Assembly
    updateAssembly(iter.assembly_data || null);

    // Cuts page
    updateCuts(iter.cut_data || null, parts);

    // History page
    updateHistory(idx);

    // Resize scenes
    setTimeout(function() {
        designScene.resize();
        partsScene.resize();
    }, 50);
}

// ============================================================
// Summary panel
// ============================================================
function updateSummary(spec, parts, dims, hw, notes) {
    var roleCounts = {};
    parts.forEach(function(p) {
        roleCounts[p.role] = (roleCounts[p.role] || 0) + 1;
    });

    var roleHtml = '';
    var sorted = Object.entries(roleCounts).sort(function(a, b) { return b[1] - a[1]; });
    sorted.forEach(function(entry) {
        var role = entry[0], count = entry[1];
        var rgb = ROLE_RGB[role] || [180,150,100];
        var label = ROLE_LABELS[role] || role;
        roleHtml += '<div class="role-row">' +
            '<div class="role-swatch" style="background:rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')"></div>' +
            '<div class="role-name">' + label + '</div>' +
            '<div class="role-count">' + count + '</div></div>';
    });

    var hwHtml = '';
    hw.forEach(function(h) {
        var name = h.type || h.name || '?';
        var qty = h.estimated_qty || h.qty || '?';
        var unit = h.unit || '';
        hwHtml += '<div class="hw-row"><span class="hw-name">' + name + '</span><span class="hw-qty">\u00d7' + qty + (unit ? ' ' + unit : '') + '</span></div>';
    });

    var notesHtml = '';
    notes.forEach(function(n) {
        notesHtml += '<div class="note-item">' + n + '</div>';
    });

    var html = '<div class="summary-section"><div class="section-title">Especificaciones</div>' +
        '<div class="spec-grid">' +
        '<div class="spec-item"><div class="spec-label">Tipo</div><div class="spec-value sm">' + ((spec.furniture_type || '?').replace(/_/g, ' ')) + '</div></div>' +
        '<div class="spec-item"><div class="spec-label">Material</div><div class="spec-value sm">' + (spec.material || '?') + '</div></div>' +
        '<div class="spec-item"><div class="spec-label">Dimensiones</div><div class="spec-value sm">' + (dims.width || '?') + '\u00d7' + (dims.height || '?') + '\u00d7' + (dims.depth || '?') + ' <span class="spec-unit">cm</span></div></div>' +
        '<div class="spec-item"><div class="spec-label">Total partes</div><div class="spec-value">' + parts.length + '</div></div>' +
        '</div></div>';

    html += '<div class="summary-section"><div class="section-title">Desglose por rol</div><div class="role-list">' + roleHtml + '</div></div>';

    if (hw.length) {
        html += '<div class="summary-section"><div class="section-title">Hardware</div>' + hwHtml + '</div>';
    }

    if (notes.length) {
        html += '<div class="summary-section"><div class="section-title">Notas</div>' + notesHtml + '</div>';
    }

    document.getElementById('summary-panel').innerHTML = html;
}

// ============================================================
// Parts table
// ============================================================
function updatePartsTable(parts) {
    var rows = '';
    parts.forEach(function(p) {
        var rgb = ROLE_RGB[p.role] || [180,150,100];
        var label = ROLE_LABELS[p.role] || p.role;
        rows += '<tr data-id="' + p.id + '">' +
            '<td><span class="part-role-dot" style="background:rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')"></span>' + p.id + '</td>' +
            '<td>' + label + '</td>' +
            '<td class="mono">' + p.width_mm + '\u00d7' + p.height_mm + '\u00d7' + p.thickness_mm + '</td></tr>';
    });
    document.getElementById('parts-tbody').innerHTML = rows;

    // Click on row -> select in 3D
    document.querySelectorAll('#parts-tbody tr[data-id]').forEach(function(row) {
        row.addEventListener('click', function() {
            var meshes = partsScene.getMeshes();
            var mesh = meshes.find(function(m) { return m.userData.partId === row.dataset.id; });
            if (mesh) {
                var ctrls = partsScene.getControls();
                ctrls.target.lerp(mesh.position.clone(), 0.5);
                ctrls.update();
            }
        });
    });
}

// ============================================================
// Assembly guide
// ============================================================
function updateAssembly(assemblyData) {
    var el = document.getElementById('assembly-container');
    if (!assemblyData) {
        el.innerHTML = '';
        return;
    }
    var steps = assemblyData.steps || [];
    if (steps.length === 0) {
        el.innerHTML = '';
        return;
    }

    var html = '<div class="assembly-section"><div class="section-title">Gu\u00eda de ensamble</div>';
    steps.forEach(function(s) {
        var partsStr = Array.isArray(s.parts) ? s.parts.join(', ') : '';
        var hwStr = s.hardware || '';
        html += '<div class="assembly-step">' +
            '<div class="step-number">' + s.step + '</div>' +
            '<div class="step-content">' +
            '<div class="step-title">' + (s.action || '') + '</div>' +
            (s.tip ? '<div class="step-detail">' + s.tip + '</div>' : '') +
            (hwStr ? '<div class="step-hardware">' + hwStr + '</div>' : '') +
            '</div></div>';
    });
    html += '</div>';
    el.innerHTML = html;
}

// ============================================================
// Cuts page
// ============================================================
function updateCuts(cutData, allParts) {
    var statsEl = document.getElementById('cuts-stats');
    var sheetsEl = document.getElementById('sheets-list');
    var legendEl = document.getElementById('cuts-legend-container');

    if (!cutData) {
        statsEl.innerHTML = '';
        sheetsEl.innerHTML = '<div class="no-data"><div class="no-data-icon">\u2702\ufe0f</div>Sin datos de optimizaci\u00f3n de corte.<br>Genera el reporte completo para incluir cortes.</div>';
        legendEl.innerHTML = '';
        return;
    }

    var sheets = cutData.sheets || [];
    var totalSheets = cutData.total_sheets || cutData.sheets_needed || sheets.length;
    var sheetSize = cutData.sheet_size_mm || {};
    var globalSheetW = sheetSize.width || 2440;
    var globalSheetH = sheetSize.height || 1220;
    var wastePct = cutData.waste_percent != null ? cutData.waste_percent : (cutData.waste_percentage != null ? cutData.waste_percentage : '?');
    var totalPieces = 0;
    sheets.forEach(function(sh) { totalPieces += (sh.pieces || []).length; });

    statsEl.innerHTML =
        '<div class="cut-stat-pill"><div class="cut-stat-value">' + totalSheets + '</div><div class="cut-stat-label">Tableros</div></div>' +
        '<div class="cut-stat-pill"><div class="cut-stat-value">' + wastePct + '%</div><div class="cut-stat-label">Desperdicio</div></div>' +
        '<div class="cut-stat-pill"><div class="cut-stat-value">' + totalPieces + '</div><div class="cut-stat-label">Piezas</div></div>';

    // Build a lookup from part id to part data
    var partMap = {};
    allParts.forEach(function(p) { partMap[p.id] = p; });

    var sheetsHtml = '';
    sheets.forEach(function(sheet, si) {
        var sheetW = sheet.sheet_width || globalSheetW;
        var sheetH = sheet.sheet_height || globalSheetH;
        var pieces = sheet.pieces || [];
        var material = sheet.material || '';

        // Calculate usage for this sheet
        var usedArea = 0;
        pieces.forEach(function(pc) { usedArea += pc.width * pc.height; });
        var sheetArea = sheetW * sheetH;
        var sheetUsage = sheetArea > 0 ? ((usedArea / sheetArea) * 100).toFixed(1) : 0;
        var sheetWaste = (100 - sheetUsage).toFixed(1);
        var usageClass = sheetUsage >= 75 ? 'good' : (sheetUsage >= 55 ? 'ok' : 'bad');

        // SVG scale factor
        var svgW = 254;
        var svgH = Math.round(svgW * sheetH / sheetW);
        var scale = svgW / sheetW;

        // Build SVG
        var svg = '<svg class="sheet-svg" viewBox="0 0 ' + svgW + ' ' + svgH + '" style="aspect-ratio: ' + svgW + '/' + svgH + ';">';
        svg += '<rect x="0" y="0" width="' + svgW + '" height="' + svgH + '" fill="#f8f9fb" stroke="#d1d5db" stroke-width="0.5" rx="2"/>';
        // Center line
        svg += '<line x1="' + (svgW/2) + '" y1="0" x2="' + (svgW/2) + '" y2="' + svgH + '" stroke="#e5e7eb" stroke-width="0.3" stroke-dasharray="3,3"/>';

        pieces.forEach(function(pc) {
            var sx = pc.x * scale + 2;
            var sy = pc.y * scale + 2;
            var sw = pc.width * scale - 2;
            var sh_val = pc.height * scale - 2;
            var partData = partMap[pc.id] || {};
            var role = partData.role || guessRole(pc.id);
            var cls = ROLE_SVG_CLASS[role] || 'piece-side';

            svg += '<rect x="' + sx + '" y="' + sy + '" width="' + sw + '" height="' + sh_val + '" rx="1" class="' + cls + '" stroke-width="0.6"/>';

            // Label
            var cx = sx + sw / 2;
            var cy = sy + sh_val / 2;
            if (sw > 30 && sh_val > 12) {
                svg += '<text x="' + cx + '" y="' + (cy - 2) + '" text-anchor="middle" fill="var(--text-secondary)" font-size="3.5" font-family="JetBrains Mono">' + pc.id + '</text>';
                svg += '<text x="' + cx + '" y="' + (cy + 4) + '" text-anchor="middle" fill="var(--text-dim)" font-size="2.5" font-family="JetBrains Mono">' + pc.width + '\u00d7' + pc.height + '</text>';
            } else if (sw > 15 && sh_val > 6) {
                svg += '<text x="' + cx + '" y="' + (cy + 1) + '" text-anchor="middle" fill="var(--text-dim)" font-size="2.5" font-family="JetBrains Mono">' + pc.id + '</text>';
            }

            // Edge banding lines on SVG
            var eb = partData.edge_banding || [];
            if (eb.length > 0) {
                var edges = eb.map(function(e) { return (typeof e === 'string' ? e : '').toLowerCase(); });
                if (edges.indexOf('top') >= 0 || edges.indexOf('front') >= 0 || eb.length >= 4)
                    svg += '<line x1="' + sx + '" y1="' + sy + '" x2="' + (sx+sw) + '" y2="' + sy + '" stroke="#2563eb" stroke-width="1.5" opacity="0.7"/>';
                if (edges.indexOf('bottom') >= 0 || eb.length >= 4)
                    svg += '<line x1="' + sx + '" y1="' + (sy+sh_val) + '" x2="' + (sx+sw) + '" y2="' + (sy+sh_val) + '" stroke="#2563eb" stroke-width="1.5" opacity="0.7"/>';
                if (edges.indexOf('left') >= 0 || eb.length >= 4)
                    svg += '<line x1="' + sx + '" y1="' + sy + '" x2="' + sx + '" y2="' + (sy+sh_val) + '" stroke="#2563eb" stroke-width="1.5" opacity="0.7"/>';
                if (edges.indexOf('right') >= 0 || edges.indexOf('back') >= 0 || eb.length >= 4)
                    svg += '<line x1="' + (sx+sw) + '" y1="' + sy + '" x2="' + (sx+sw) + '" y2="' + (sy+sh_val) + '" stroke="#2563eb" stroke-width="1.5" opacity="0.7"/>';
            }
        });
        svg += '</svg>';

        // Build pieces table
        var tableRows = '';
        pieces.forEach(function(pc) {
            var partData = partMap[pc.id] || {};
            var role = partData.role || guessRole(pc.id);
            var rgb = ROLE_RGB[role] || [180,150,100];
            var eb = partData.edge_banding || [];
            tableRows += '<tr>' +
                '<td><span class="part-role-dot" style="background:rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')"></span>' + pc.id + '</td>' +
                '<td class="mono">' + pc.width + ' \u00d7 ' + pc.height + ' mm</td>' +
                '<td>' + edgeBandingSvg(eb) + '</td></tr>';
        });

        sheetsHtml += '<div class="sheet-card">' +
            '<div class="sheet-card-header">' +
            '<div class="sheet-card-title">Tablero ' + (si + 1) + ' \u2014 ' + sheetW + ' \u00d7 ' + sheetH + ' mm</div>' +
            '<div class="sheet-card-meta"><span>' + material + '</span><span><strong>' + pieces.length + '</strong> piezas</span></div></div>' +
            '<div class="sheet-card-body">' +
            '<div class="sheet-visual">' + svg + '</div>' +
            '<div class="sheet-details"><table class="sheet-pieces-table"><thead><tr><th>Pieza</th><th>Dimensiones</th><th>Canteado</th></tr></thead><tbody>' + tableRows + '</tbody></table></div></div>' +
            '<div class="sheet-usage-bar">' +
            '<span class="usage-label">Uso: ' + sheetUsage + '%</span>' +
            '<div class="usage-track"><div class="usage-fill ' + usageClass + '" style="width:' + sheetUsage + '%"></div></div>' +
            '<span class="usage-label" style="color:var(--text-dim)">Desperdicio: ' + sheetWaste + '%</span></div></div>';
    });

    sheetsEl.innerHTML = sheetsHtml;

    // Legend
    var roles = {};
    allParts.forEach(function(p) { roles[p.role] = true; });
    var legendHtml = '<div class="cuts-legend">';
    Object.keys(roles).forEach(function(role) {
        var rgb = ROLE_RGB[role] || [180,150,100];
        var label = ROLE_LABELS[role] || role;
        legendHtml += '<div class="legend-item"><div class="legend-swatch" style="background:rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')"></div>' + label + '</div>';
    });
    legendHtml += '</div>';
    legendHtml += '<div class="edge-legend"><div class="edge-legend-item"><div class="edge-legend-line active"></div>Con canteado</div>' +
        '<div class="edge-legend-item"><div class="edge-legend-line inactive"></div>Sin canteado</div></div>';
    legendEl.innerHTML = legendHtml;
}

function guessRole(id) {
    if (!id) return 'shelf';
    var lower = id.toLowerCase();
    if (lower.indexOf('side') >= 0) return 'side';
    if (lower.indexOf('bottom') >= 0) return 'bottom';
    if (lower.indexOf('top') >= 0) return 'top_panel';
    if (lower.indexOf('divider') >= 0) return 'divider';
    if (lower.indexOf('shelf') >= 0) return 'shelf';
    if (lower.indexOf('back') >= 0 && lower.indexOf('rail') < 0) return 'back';
    if (lower.indexOf('door') >= 0) return 'door';
    if (lower.indexOf('rail') >= 0) return 'rail';
    if (lower.indexOf('kickplate_return') >= 0 || lower.indexOf('kick_return') >= 0) return 'kickplate_return';
    if (lower.indexOf('kick') >= 0) return 'kickplate';
    if (lower.indexOf('drawer') >= 0) return 'drawer_front';
    return 'shelf';
}

// ============================================================
// History page
// ============================================================
function updateHistory(activeIdx) {
    var html = '';
    iterations.forEach(function(iter, i) {
        var spec = iter.spec;
        var nParts = (spec.parts || []).length;
        var dims = spec.dimensions_cm || {};
        var isActive = i === activeIdx;

        html += '<div class="history-item' + (isActive ? ' active' : '') + '" data-idx="' + i + '">' +
            '<div class="history-header"><span class="history-name">' + iter.name + '</span>' +
            '<span class="history-time">' + (iter.timestamp || '').replace('T', ' ') + '</span></div>';

        if (iter.comment) {
            html += '<div class="history-comment">' + iter.comment + '</div>';
        }

        html += '<div class="history-stats">' + nParts + ' partes \u00b7 ' +
            (dims.width || '?') + '\u00d7' + (dims.height || '?') + '\u00d7' + (dims.depth || '?') + 'cm \u00b7 ' +
            (spec.material || '?') + '</div></div>';
    });

    document.getElementById('history-timeline').innerHTML = html;

    document.querySelectorAll('.history-item').forEach(function(item) {
        item.addEventListener('click', function() {
            updateUI(parseInt(item.dataset.idx));
        });
    });
}

// ============================================================
// Iteration slider
// ============================================================
document.getElementById('iter-slider').addEventListener('input', function(e) {
    updateUI(parseInt(e.target.value));
});

// ============================================================
// Parts search
// ============================================================
document.getElementById('parts-search').addEventListener('input', function(e) {
    var q = e.target.value.toLowerCase();
    document.querySelectorAll('#parts-tbody tr').forEach(function(row) {
        row.style.display = row.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
    });
});

// ============================================================
// Resize
// ============================================================
window.addEventListener('resize', function() {
    designScene.resize();
    partsScene.resize();
});

// ============================================================
// Init
// ============================================================
designScene.resize();
updateUI(currentIdx);

// ============================================================
// Live Reload via WebSocket
// ============================================================
(function() {
    var designId = location.pathname.replace(/^\//, '').replace(/\/$/, '');
    if (!designId || location.protocol === 'file:') return;
    var wsUrl = 'ws://' + location.host + '/ws/' + designId;
    var ws, retryDelay = 1000;
    function connect() {
        ws = new WebSocket(wsUrl);
        ws.onopen = function() { retryDelay = 1000; };
        ws.onmessage = function(e) {
            if (e.data === 'reload') location.reload();
        };
        ws.onclose = function() {
            setTimeout(connect, retryDelay);
            retryDelay = Math.min(retryDelay * 1.5, 10000);
        };
    }
    connect();
})();
</script>
</body>
</html>
"""
