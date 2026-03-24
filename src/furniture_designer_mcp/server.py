from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import TextContent

from .knowledge.ergonomics import ERGONOMIC_STANDARDS
from .knowledge.materials import MATERIALS
from .knowledge.structural_rules import STRUCTURAL_RULES
from .knowledge.hardware import HARDWARE_CATALOG
from .knowledge.assembly_specs import ASSEMBLY_SPECS
from .knowledge.brief_formatters import (
    brief_standards,
    brief_material,
    brief_structural_rules,
    brief_hardware,
    brief_hardware_category,
    brief_assembly_specs,
)
from .engine.designer import generate_furniture_spec
from .engine.cut_optimizer import optimize_cuts as _optimize_cuts
from .engine.structural_validator import validate_structure as _validate
from .engine.bom_generator import generate_bom as _generate_bom
from .engine.freecad_scripts import (
    spec_to_freecad_script,
    exploded_view_script,
    cut_layout_script,
    import_script as _import_script,
    parse_freecad_export as _parse_export,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "FurnitureDesignerMCP",
    instructions=(
        "Professional furniture design server. Provides ergonomic standards, "
        "structural validation, cut optimization (2D bin packing), BOM generation, "
        "and assembly instructions for cabinet-making."
    ),
)


# ---------------------------------------------------------------------------
# Knowledge tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_standards(ctx: Context, furniture_type: str, brief: bool = False) -> list[TextContent]:
    """Get ergonomic standards for a furniture type.

    Args:
        furniture_type: One of: kitchen_base, kitchen_wall, closet, bookshelf,
            desk, vanity, general
        brief: If true, return a compact summary instead of full JSON (saves tokens).

    Returns:
        Ergonomic standards (heights, depths, clearances) for the given type.
    """
    standards = ERGONOMIC_STANDARDS.get(furniture_type)
    if standards is None:
        available = ", ".join(ERGONOMIC_STANDARDS.keys())
        return [TextContent(type="text", text=f"Unknown type '{furniture_type}'. Available: {available}")]
    if brief:
        return [TextContent(type="text", text=brief_standards(standards))]
    return [TextContent(type="text", text=json.dumps(standards, indent=2, ensure_ascii=False))]


@mcp.tool()
def get_material_specs(ctx: Context, material: str, brief: bool = False) -> list[TextContent]:
    """Get technical specifications for a material.

    Args:
        material: One of: mdf_15, mdf_18, melamine_16, melamine_18, plywood_18,
            solid_pine_20
        brief: If true, return a compact summary instead of full JSON (saves tokens).

    Returns:
        Material properties: max unsupported span, available thicknesses,
        standard sheet sizes, edge banding options.
    """
    specs = MATERIALS.get(material)
    if specs is None:
        available = ", ".join(MATERIALS.keys())
        return [TextContent(type="text", text=f"Unknown material '{material}'. Available: {available}")]
    if brief:
        return [TextContent(type="text", text=brief_material(specs))]
    return [TextContent(type="text", text=json.dumps(specs, indent=2, ensure_ascii=False))]


@mcp.tool()
def get_structural_rules(ctx: Context, brief: bool = False) -> list[TextContent]:
    """Get all structural rules for furniture design.

    Args:
        brief: If true, return a compact summary instead of full JSON (saves tokens).

    Returns:
        List of rules covering reinforcement, back panels, kick plates, shelf
        supports, vertical dividers, and load-bearing requirements.
    """
    if brief:
        return [TextContent(type="text", text=brief_structural_rules(STRUCTURAL_RULES))]
    return [TextContent(type="text", text=json.dumps(STRUCTURAL_RULES, indent=2, ensure_ascii=False))]


@mcp.tool()
def get_hardware_catalog(ctx: Context, category: str | None = None, brief: bool = False) -> list[TextContent]:
    """Get hardware catalog with selection rules.

    Args:
        category: Optional filter — one of: hinges, slides, connectors, shelf_pins.
            If omitted, returns the full catalog.
        brief: If true, return a compact summary instead of full JSON (saves tokens).

    Returns:
        Hardware specifications with placement rules and quantities.
    """
    if category is not None:
        data = HARDWARE_CATALOG.get(category)
        if data is None:
            available = ", ".join(HARDWARE_CATALOG.keys())
            return [TextContent(type="text", text=f"Unknown category '{category}'. Available: {available}")]
        if brief:
            return [TextContent(type="text", text=brief_hardware_category(data))]
    else:
        data = HARDWARE_CATALOG
        if brief:
            return [TextContent(type="text", text=brief_hardware(data))]
    return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]


@mcp.tool()
def get_assembly_specs(ctx: Context, topic: str | None = None, brief: bool = False) -> list[TextContent]:
    """Get detailed assembly specifications for furniture construction.

    Covers joint methods, fastener patterns, adhesive usage, pre-drilling
    depths, hinge mounting, drawer slide installation, and shelf pin systems.

    Args:
        topic: Optional filter — one of: panel_to_panel, back_panel,
            hinge_mounting, drawer_slide_mounting, shelf_pins, adhesive_guide,
            pre_drilling. If omitted, returns all topics.
        brief: If true, return a compact summary instead of full JSON (saves tokens).

    Returns:
        Assembly specifications with step-by-step processes, fastener types,
        and material-specific parameters.
    """
    if topic is not None:
        data = ASSEMBLY_SPECS.get(topic)
        if data is None:
            available = ", ".join(ASSEMBLY_SPECS.keys())
            return [TextContent(type="text", text=f"Unknown topic '{topic}'. Available: {available}")]
        if brief:
            return [TextContent(type="text", text=brief_assembly_specs(data))]
        return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]
    else:
        if brief:
            sections = [brief_assembly_specs(v) for v in ASSEMBLY_SPECS.values()]
            return [TextContent(type="text", text="\n\n".join(sections))]
        return [TextContent(type="text", text=json.dumps(ASSEMBLY_SPECS, indent=2, ensure_ascii=False))]


# ---------------------------------------------------------------------------
# Design tools
# ---------------------------------------------------------------------------


@mcp.tool()
def design_furniture(
    ctx: Context,
    furniture_type: str,
    width: float,
    height: float,
    depth: float,
    material: str = "melamine_16",
    options: dict | None = None,
) -> list[TextContent]:
    """Design a complete furniture piece with standards applied.

    Generates a full specification including all panels, reinforcements,
    hardware, and assembly order based on ergonomic standards and structural
    rules.

    Args:
        furniture_type: One of: kitchen_base, kitchen_wall, closet, bookshelf,
            desk, vanity
        width: Total width in cm
        height: Total height in cm
        depth: Total depth in cm
        material: Material key (default: melamine_16)
        options: Optional overrides — e.g. {"num_shelves": 3, "has_drawers": true,
            "door_type": "double", "kickplate_height": 10}

    Returns:
        Complete furniture spec (JSON) with parts list, positions, hardware,
        and structural notes.
    """
    try:
        spec = generate_furniture_spec(
            furniture_type=furniture_type,
            width=width,
            height=height,
            depth=depth,
            material=material,
            options=options or {},
        )
        return [TextContent(type="text", text=json.dumps(spec, indent=2, ensure_ascii=False))]
    except Exception as e:
        logger.exception("design_furniture failed")
        return [TextContent(type="text", text=f"Error designing furniture: {e}")]


# ---------------------------------------------------------------------------
# Validation tools
# ---------------------------------------------------------------------------


@mcp.tool()
def validate_structure(ctx: Context, spec: dict) -> list[TextContent]:
    """Validate a furniture spec against structural rules.

    Checks unsupported spans, required reinforcements, hardware quantities,
    back panel presence, and stability.

    Args:
        spec: A furniture spec as returned by design_furniture.

    Returns:
        Validation report with errors (must fix) and warnings (recommended).
    """
    try:
        report = _validate(spec)
        return [TextContent(type="text", text=json.dumps(report, indent=2, ensure_ascii=False))]
    except Exception as e:
        logger.exception("validate_structure failed")
        return [TextContent(type="text", text=f"Error validating: {e}")]


# ---------------------------------------------------------------------------
# Cut optimization tools
# ---------------------------------------------------------------------------


@mcp.tool()
def optimize_cuts(
    ctx: Context,
    parts: list[dict],
    sheet_width: float = 2440,
    sheet_height: float = 1220,
    blade_kerf: float = 3,
    grain_direction: str = "auto",
) -> list[TextContent]:
    """Optimize panel cuts on standard sheets using guillotine algorithm.

    Args:
        parts: List of parts — each: {"id": "side_left", "width": 580,
            "height": 750, "qty": 1, "can_rotate": true, "grain": "length"}
            Dimensions in mm.
            Grain options per piece: "length" (grain along width — no rotation),
            "width" (grain along height — auto-rotates to match sheet),
            "none" (free rotation).
        sheet_width: Sheet width in mm (default: 2440 — standard 8ft).
            Grain runs along this axis on the sheet.
        sheet_height: Sheet height in mm (default: 1220 — standard 4ft)
        blade_kerf: Saw blade width in mm (default: 3)
        grain_direction: Global default grain for pieces without explicit grain.
            "auto" (default) = use each piece's grain/can_rotate fields.
            "length" = all pieces have grain along their width.
            "none" = ignore grain, free rotation.

    Returns:
        Optimization result: sheets used, piece positions, waste percentage,
        grain arrows, and a text diagram.
    """
    try:
        result = _optimize_cuts(
            parts=parts,
            sheet_width=sheet_width,
            sheet_height=sheet_height,
            blade_kerf=blade_kerf,
            grain_direction=grain_direction,
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
    except Exception as e:
        logger.exception("optimize_cuts failed")
        return [TextContent(type="text", text=f"Error optimizing cuts: {e}")]


# ---------------------------------------------------------------------------
# BOM tools
# ---------------------------------------------------------------------------


@mcp.tool()
def generate_bom(ctx: Context, spec: dict) -> list[TextContent]:
    """Generate a Bill of Materials from a furniture spec.

    Args:
        spec: A furniture spec as returned by design_furniture.

    Returns:
        BOM with: panels (name, dimensions, material, edge banding),
        hardware (type, qty, reference), and summary.
    """
    try:
        bom = _generate_bom(spec)
        return [TextContent(type="text", text=json.dumps(bom, indent=2, ensure_ascii=False))]
    except Exception as e:
        logger.exception("generate_bom failed")
        return [TextContent(type="text", text=f"Error generating BOM: {e}")]


# ---------------------------------------------------------------------------
# Assembly tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_assembly_steps(ctx: Context, spec: dict) -> list[TextContent]:
    """Generate step-by-step assembly instructions for a furniture spec.

    Args:
        spec: A furniture spec as returned by design_furniture.

    Returns:
        Ordered list of assembly steps with part references, hardware needed
        per step, and tips.
    """
    try:
        parts = spec.get("parts", [])
        hardware = spec.get("hardware", [])
        furniture_type = spec.get("furniture_type", "general")

        steps: list[dict] = []
        step_num = 0

        # Group parts by role for assembly order
        panels = [p for p in parts if p.get("role") in ("panel_vertical", "side")]
        bottoms = [p for p in parts if p.get("role") in ("bottom", "floor")]
        tops = [p for p in parts if p.get("role") in ("top", "top_panel")]
        backs = [p for p in parts if p.get("role") == "back"]
        shelves = [p for p in parts if p.get("role") == "shelf"]
        rails = [p for p in parts if p.get("role") == "rail"]
        dividers = [p for p in parts if p.get("role") == "divider"]
        doors = [p for p in parts if p.get("role") == "door"]
        drawers = [p for p in parts if p.get("role") == "drawer_front"]
        kickplates = [p for p in parts if p.get("role") == "kickplate"]

        # Step 1: Bottom to sides
        if bottoms and panels:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": "Fijar piso al lateral izquierdo",
                "parts": [bottoms[0]["id"], panels[0]["id"]],
                "hardware": "Tornillos confirmat 7x50mm (mín. 3)",
                "tip": "Pre-taladrar con broca de 5mm. El piso va entre los laterales."
            })

        if len(panels) > 1 and bottoms:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": "Fijar lateral derecho al piso",
                "parts": [panels[-1]["id"], bottoms[0]["id"]],
                "hardware": "Tornillos confirmat 7x50mm (mín. 3)",
                "tip": "Verificar escuadra con un ángulo de 90°."
            })

        # Step 2: Dividers
        for div in dividers:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": f"Instalar división vertical '{div['id']}'",
                "parts": [div["id"]],
                "hardware": "Tornillos confirmat 7x50mm (2 arriba, 2 abajo)",
                "tip": "Verificar que quede a plomo (vertical)."
            })

        # Step 3: Rails
        for rail in rails:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": f"Fijar travesaño '{rail['id']}'",
                "parts": [rail["id"]],
                "hardware": "Tornillos confirmat 7x50mm (2 por lado)",
                "tip": "Los travesaños dan rigidez al mueble. No omitir."
            })

        # Step 4: Top
        for top in tops:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": f"Fijar tapa superior '{top['id']}'",
                "parts": [top["id"]],
                "hardware": "Tornillos confirmat 7x50mm",
                "tip": "Asegurar que quede al ras con los laterales."
            })

        # Step 5: Back panel
        for back in backs:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": f"Fijar respaldo '{back['id']}'",
                "parts": [back["id"]],
                "hardware": "Clavos de 1\" o grapas cada 15cm",
                "tip": "El respaldo cuadra el mueble. Verificar diagonales antes de fijar."
            })

        # Step 6: Shelves
        for shelf in shelves:
            step_num += 1
            adjustable = shelf.get("adjustable", False)
            steps.append({
                "step": step_num,
                "action": f"Colocar repisa '{shelf['id']}'",
                "parts": [shelf["id"]],
                "hardware": "Pernos de repisa 5mm (4 por repisa)" if adjustable else "Confirmat 7x50mm (2 por lado)",
                "tip": "Repisa ajustable." if adjustable else "Repisa fija."
            })

        # Step 7: Kickplate
        for kp in kickplates:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": f"Instalar zócalo '{kp['id']}'",
                "parts": [kp["id"]],
                "hardware": "Tornillos o clips de zócalo",
                "tip": "El zócalo va retranqueado ~5cm del frente."
            })

        # Step 8: Doors
        for door in doors:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": f"Montar puerta '{door['id']}'",
                "parts": [door["id"]],
                "hardware": "Bisagras de 35mm (cantidad según altura de puerta)",
                "tip": "Perforar copa de 35mm a 2.2cm del borde. Bisagras a 10cm de extremos."
            })

        # Step 9: Drawers
        for drawer in drawers:
            step_num += 1
            steps.append({
                "step": step_num,
                "action": f"Instalar cajón '{drawer['id']}'",
                "parts": [drawer["id"]],
                "hardware": "Correderas telescópicas (par)",
                "tip": "Montar correderas primero en laterales del mueble, luego en cajón."
            })

        result = {
            "furniture_type": furniture_type,
            "total_steps": len(steps),
            "steps": steps,
            "general_tips": [
                "Trabajar sobre superficie plana y limpia.",
                "Pre-taladrar siempre antes de atornillar confirmat.",
                "Verificar escuadra después de cada unión.",
                "El respaldo es el último panel estructural — cuadra todo el mueble.",
                "Las puertas y cajones se montan al final.",
            ]
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
    except Exception as e:
        logger.exception("get_assembly_steps failed")
        return [TextContent(type="text", text=f"Error generating assembly steps: {e}")]


# ---------------------------------------------------------------------------
# FreeCAD bridge tools
# ---------------------------------------------------------------------------


@mcp.tool()
def build_3d_model(
    ctx: Context,
    spec: dict,
    doc_name: str = "Furniture",
) -> list[TextContent]:
    """Generate a FreeCAD Python script that builds the furniture as a 3D model.

    The returned script creates Part::Box objects for each panel, positioned
    and color-coded by role. Execute it via freecad-mcp's execute_code tool.

    Args:
        spec: A furniture spec as returned by design_furniture.
        doc_name: Name for the FreeCAD document (default: "Furniture").

    Returns:
        Python code to execute in FreeCAD.
    """
    try:
        code = spec_to_freecad_script(spec, doc_name=doc_name)
        return [TextContent(type="text", text=code)]
    except Exception as e:
        logger.exception("build_3d_model failed")
        return [TextContent(type="text", text=f"Error generating 3D model script: {e}")]


@mcp.tool()
def build_exploded_view(
    ctx: Context,
    spec: dict,
    gap_mm: float = 50,
    doc_name: str = "Exploded",
) -> list[TextContent]:
    """Generate a FreeCAD Python script for an exploded assembly view.

    Panels are separated along their assembly axis to visualize how the
    furniture comes together. Execute it via freecad-mcp's execute_code tool.

    Args:
        spec: A furniture spec as returned by design_furniture.
        gap_mm: Gap between exploded parts in mm (default: 50).
        doc_name: Name for the FreeCAD document (default: "Exploded").

    Returns:
        Python code to execute in FreeCAD.
    """
    try:
        code = exploded_view_script(spec, gap_mm=gap_mm, doc_name=doc_name)
        return [TextContent(type="text", text=code)]
    except Exception as e:
        logger.exception("build_exploded_view failed")
        return [TextContent(type="text", text=f"Error generating exploded view script: {e}")]


@mcp.tool()
def build_cut_diagram(
    ctx: Context,
    cut_result: dict,
    doc_name: str = "CutLayout",
) -> list[TextContent]:
    """Generate a FreeCAD Python script that visualizes the cut optimization layout.

    Creates a top-down view of each sheet with pieces placed according to the
    cut optimizer output. Execute it via freecad-mcp's execute_code tool.

    Args:
        cut_result: Result from optimize_cuts tool.
        doc_name: Name for the FreeCAD document (default: "CutLayout").

    Returns:
        Python code to execute in FreeCAD.
    """
    try:
        code = cut_layout_script(cut_result, doc_name=doc_name)
        return [TextContent(type="text", text=code)]
    except Exception as e:
        logger.exception("build_cut_diagram failed")
        return [TextContent(type="text", text=f"Error generating cut diagram script: {e}")]


# ---------------------------------------------------------------------------
# FreeCAD import tools
# ---------------------------------------------------------------------------


@mcp.tool()
def build_import_script(
    ctx: Context,
    doc_name: str = "Furniture",
) -> list[TextContent]:
    """Generate a FreeCAD Python script that reads all panels from a document.

    The script extracts every App::Part (with custom properties) and standalone
    Part::Box from the specified document, then prints a JSON representation
    to stdout. Execute the script via freecad-mcp's execute_code, then pass
    the output to parse_freecad_import to get a usable furniture spec.

    Workflow:
    1. Call build_import_script(doc_name) → get Python script
    2. Call mcp__freecad__execute_code(script) → get raw output with JSON
    3. Call parse_freecad_import(raw_output) → get furniture spec
    4. Use the spec with validate_structure, generate_bom, optimize_cuts, etc.

    Args:
        doc_name: Name of the FreeCAD document to read (default: "Furniture").

    Returns:
        Python code to execute in FreeCAD.
    """
    try:
        code = _import_script(doc_name=doc_name)
        return [TextContent(type="text", text=code)]
    except Exception as e:
        logger.exception("build_import_script failed")
        return [TextContent(type="text", text=f"Error generating import script: {e}")]


@mcp.tool()
def parse_freecad_import(
    ctx: Context,
    raw_output: str,
) -> list[TextContent]:
    """Parse the output of the import script into a furniture spec.

    Takes the raw stdout from executing the import script in FreeCAD and
    reconstructs a furniture spec with parts, positions, materials, and roles.

    For panels created by this system (App::Part with custom properties),
    the reconstruction is exact. For manually created Part::Box objects,
    roles are inferred from names and geometry.

    Args:
        raw_output: The stdout text from executing the import script via
            freecad-mcp's execute_code tool.

    Returns:
        A furniture spec (JSON) compatible with validate_structure,
        generate_bom, optimize_cuts, build_exploded_view, etc.
        May include "import_warnings" if any panels needed inference.
    """
    try:
        spec = _parse_export(raw_output)
        return [TextContent(type="text", text=json.dumps(spec, indent=2, ensure_ascii=False))]
    except Exception as e:
        logger.exception("parse_freecad_import failed")
        return [TextContent(type="text", text=f"Error parsing FreeCAD import: {e}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    mcp.run()


if __name__ == "__main__":
    main()
