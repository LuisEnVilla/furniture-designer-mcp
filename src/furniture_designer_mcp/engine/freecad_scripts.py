"""Generate and read FreeCAD Python scripts from/to furniture specs.

These scripts are meant to be executed via freecad-mcp's execute_code tool.
Each function returns a Python code string ready for FreeCAD's interpreter.

Best practices applied:
- App::Part container per panel (proper component pattern)
- Groups by role for tree organization (Estructura, Puertas, etc.)
- Custom properties for material, thickness, role, edge banding
- Descriptive labels on each component

Import flow (FreeCAD → spec):
- import_script() generates a Python script that reads all App::Part components
- parse_freecad_export() reconstructs a furniture spec from the script output
"""

from __future__ import annotations

import json


# -- Color palette by panel role --
_COLORS = {
    "side": (0.90, 0.75, 0.55, 1.0),
    "bottom": (0.85, 0.70, 0.50, 1.0),
    "top_panel": (0.85, 0.70, 0.50, 1.0),
    "floor": (0.85, 0.70, 0.50, 1.0),
    "shelf": (0.70, 0.85, 0.65, 1.0),
    "back": (0.75, 0.75, 0.75, 1.0),
    "door": (0.60, 0.75, 0.90, 1.0),
    "rail": (0.65, 0.55, 0.42, 1.0),
    "kickplate": (0.50, 0.50, 0.50, 1.0),
    "kickplate_return": (0.50, 0.50, 0.50, 1.0),
    "divider": (0.90, 0.72, 0.40, 1.0),
    "drawer_front": (0.60, 0.75, 0.90, 1.0),
    "drawer_side": (0.50, 0.65, 0.85, 1.0),
    "drawer_back": (0.45, 0.60, 0.80, 1.0),
    "drawer_bottom": (0.55, 0.70, 0.88, 1.0),
    "back_rail": (0.70, 0.70, 0.70, 1.0),
}

_DEFAULT_COLOR = (0.80, 0.70, 0.55, 1.0)

# -- Group classification by role --
_ROLE_GROUPS = {
    "side": "Estructura",
    "bottom": "Estructura",
    "top_panel": "Estructura",
    "floor": "Estructura",
    "divider": "Estructura",
    "rail": "Estructura",
    "kickplate": "Estructura",
    "kickplate_return": "Estructura",
    "back": "Respaldo",
    "back_rail": "Respaldo",
    "shelf": "Repisas",
    "door": "Puertas",
    "drawer_front": "Cajones",
    "drawer_side": "Cajones",
    "drawer_back": "Cajones",
    "drawer_bottom": "Cajones",
}

# -- Descriptive labels by role --
_ROLE_LABELS = {
    "side": "Lateral",
    "bottom": "Piso",
    "top_panel": "Tapa superior",
    "floor": "Piso",
    "shelf": "Repisa",
    "back": "Respaldo",
    "back_rail": "Rail Respaldo",
    "door": "Puerta",
    "rail": "Travesaño",
    "kickplate": "Zócalo",
    "kickplate_return": "Retorno zócalo",
    "divider": "División vertical",
    "drawer_front": "Frente de cajón",
    "drawer_side": "Lateral de cajón",
    "drawer_back": "Trasera de cajón",
    "drawer_bottom": "Fondo de cajón",
}


def _box_dims(part: dict) -> tuple[float, float, float]:
    """Map abstract (width, height, thickness) to FreeCAD (Length, Width, Height).

    In our spec coordinate system:
      X = furniture width axis (left-right)
      Y = furniture depth axis (front-back)
      Z = furniture height axis (bottom-top)

    The mapping depends on the panel role / orientation.
    """
    w = part["width_mm"]
    h = part["height_mm"]
    t = part["thickness_mm"]
    role = part["role"]

    if role in ("side", "divider"):
        # Vertical panel perpendicular to X axis
        # thin in X, depth in Y, tall in Z
        return (t, w, h)
    elif role in ("bottom", "top_panel", "shelf", "floor"):
        # Horizontal panel
        # wide in X, depth in Y, thin in Z
        return (w, h, t)
    elif role in ("back",):
        # Vertical panel perpendicular to Y axis
        # wide in X, thin in Y, tall in Z
        return (w, t, h)
    elif role in ("door", "drawer_front"):
        # Vertical panel at front
        # wide in X, thin in Y, tall in Z
        return (w, t, h)
    elif role == "drawer_side":
        # Vertical panel perpendicular to X (like side but for drawer)
        return (t, w, h)
    elif role == "drawer_back":
        # Vertical panel perpendicular to Y (like back but for drawer)
        return (w, t, h)
    elif role == "drawer_bottom":
        # Horizontal panel (like shelf but for drawer)
        return (w, h, t)
    elif role in ("rail",):
        # Horizontal beam
        # wide in X, thin in Y, height in Z
        return (w, t, h)
    elif role in ("kickplate",):
        # Vertical panel at front-bottom
        # wide in X, thin in Y, height in Z
        return (w, t, h)
    elif role == "kickplate_return":
        # Vertical panel perpendicular to X (like side) for kickplate frame
        # thin in X, depth in Y, height in Z
        return (t, w, h)
    else:
        # Default: treat as horizontal
        return (w, h, t)


def _safe_name(pid: str) -> str:
    """Sanitize a part id for use as FreeCAD object name."""
    return pid.replace("-", "_").replace(" ", "_")


def _generate_groups_code(parts: list[dict]) -> tuple[list[str], dict[str, str]]:
    """Generate code to create role-based groups and return role→group_var mapping."""
    roles_present = set(p["role"] for p in parts)
    groups_needed = {}
    for role in roles_present:
        group_name = _ROLE_GROUPS.get(role, "Otros")
        if group_name not in groups_needed:
            groups_needed[group_name] = f"grp_{group_name.lower().replace(' ', '_')}"

    lines = ["# -- Groups by role --"]
    for group_name, var_name in sorted(groups_needed.items()):
        lines.append(f'{var_name} = doc.addObject("App::DocumentObjectGroup", "{group_name}")')
        lines.append(f'{var_name}.Label = "{group_name}"')
    lines.append("")

    # Map role → group variable
    role_to_var = {}
    for role in roles_present:
        group_name = _ROLE_GROUPS.get(role, "Otros")
        role_to_var[role] = groups_needed[group_name]

    return lines, role_to_var


def _generate_panel_code(
    part: dict,
    role_to_group: dict[str, str],
    offset: tuple[float, float, float] = (0, 0, 0),
) -> list[str]:
    """Generate code for a single panel with App::Part container and properties."""
    pid = part["id"]
    role = part["role"]
    safe = _safe_name(pid)
    length, width, height = _box_dims(part)
    pos = part.get("position_mm", {"x": 0, "y": 0, "z": 0})
    color = _COLORS.get(role, _DEFAULT_COLOR)
    group_var = role_to_group.get(role, "doc")
    label = _ROLE_LABELS.get(role, role)
    material = part.get("material", "")
    thickness = part.get("thickness_mm", 0)
    edge_banding = part.get("edge_banding", "")

    px = pos["x"] + offset[0]
    py = pos["y"] + offset[1]
    pz = pos["z"] + offset[2]

    lines = []
    lines.append(f"# -- {pid} ({role}) --")

    # Create App::Part container
    lines.append(f'{safe}_part = doc.addObject("App::Part", "{safe}")')
    w_mm = part["width_mm"]
    h_mm = part["height_mm"]
    lines.append(f'{safe}_part.Label = "{label} — {pid} ({w_mm}x{h_mm}x{thickness}mm)"')

    # Create the box shape inside the Part
    lines.append(f'{safe} = doc.addObject("Part::Box", "{safe}_shape")')
    lines.append(f"{safe}.Length = {length}")
    lines.append(f"{safe}.Width = {width}")
    lines.append(f"{safe}.Height = {height}")

    # Add shape to Part container
    lines.append(f"{safe}_part.addObject({safe})")

    # Position the Part container
    lines.append(
        f"{safe}_part.Placement = FreeCAD.Placement("
        f"FreeCAD.Vector({px}, {py}, {pz}), "
        f"FreeCAD.Rotation(0, 0, 0, 1))"
    )

    # Visual properties
    lines.append(f"{safe}.ViewObject.ShapeColor = {color}")
    lines.append(f"{safe}.ViewObject.Transparency = 10")

    # Custom properties for metadata
    lines.append(f'{safe}_part.addProperty("App::PropertyString", "Role", "Furniture", "Panel role")')
    lines.append(f'{safe}_part.Role = "{role}"')
    # Use "PanelMaterial" to avoid conflict with App::Part's built-in "Material" property
    lines.append(f'{safe}_part.addProperty("App::PropertyString", "PanelMaterial", "Furniture", "Material type")')
    lines.append(f'{safe}_part.PanelMaterial = "{material}"')
    lines.append(f'{safe}_part.addProperty("App::PropertyFloat", "Thickness_mm", "Furniture", "Panel thickness in mm")')
    lines.append(f"{safe}_part.Thickness_mm = {thickness}")
    lines.append(f'{safe}_part.addProperty("App::PropertyString", "RealDimensions", "Furniture", "WxHxT in mm")')
    lines.append(f'{safe}_part.RealDimensions = "{part["width_mm"]}x{part["height_mm"]}x{thickness}"')

    if edge_banding:
        eb_str = edge_banding if isinstance(edge_banding, str) else json.dumps(edge_banding, ensure_ascii=False)
        # Use single quotes in generated code to avoid conflict with JSON double quotes
        lines.append(f'{safe}_part.addProperty("App::PropertyString", "EdgeBanding", "Furniture", "Edge banding spec")')
        lines.append(f"{safe}_part.EdgeBanding = '{eb_str}'")

    # Add Part to group
    lines.append(f"{group_var}.addObject({safe}_part)")
    lines.append("")

    return lines


def spec_to_freecad_script(spec: dict, doc_name: str = "Furniture") -> str:
    """Generate a FreeCAD Python script that builds the full 3D model.

    Uses App::Part containers, role-based groups, and custom properties
    for material, dimensions, and edge banding.

    Args:
        spec: Furniture spec as returned by design_furniture.
        doc_name: Name for the FreeCAD document.

    Returns:
        Python code string for FreeCAD's execute_code.
    """
    parts = spec.get("parts", [])
    furniture_type = spec.get("furniture_type", "cabinet")
    dims = spec.get("dimensions_cm", {})
    material_name = spec.get("material", "")

    lines = [
        "import FreeCAD",
        "import Part",
        "",
        f"# {furniture_type} — {dims.get('width', '?')}x{dims.get('height', '?')}x{dims.get('depth', '?')} cm",
        f"# Material: {material_name}",
        f'doc = FreeCAD.newDocument("{doc_name}")',
        "",
    ]

    # Create groups
    group_lines, role_to_group = _generate_groups_code(parts)
    lines.extend(group_lines)

    # Create panels
    for part in parts:
        lines.extend(_generate_panel_code(part, role_to_group))

    lines.append("doc.recompute()")
    lines.append("FreeCADGui.activeDocument().activeView().viewIsometric()")
    lines.append("FreeCADGui.SendMsgToActiveView('ViewFit')")
    lines.append(f'print("Built {len(parts)} panels for {furniture_type}")')

    return "\n".join(lines)


def exploded_view_script(spec: dict, gap_mm: float = 50, doc_name: str = "Exploded") -> str:
    """Generate a FreeCAD script for an exploded assembly view.

    Parts are separated along their primary axis with uniform gaps
    to visualize assembly order.

    Args:
        spec: Furniture spec.
        gap_mm: Gap between exploded parts in mm.
        doc_name: Name for the FreeCAD document.

    Returns:
        Python code string for FreeCAD.
    """
    parts = spec.get("parts", [])
    furniture_type = spec.get("furniture_type", "cabinet")

    # Define explosion direction per role
    # (dx, dy, dz) multiplier for the gap
    _explosion = {
        "side": (1.0, 0, 0),       # sides push outward in X
        "divider": (0, 0, 0),       # dividers stay
        "bottom": (0, 0, -1.0),     # bottom pushes down
        "top_panel": (0, 0, 1.0),   # top pushes up
        "back": (0, 1.0, 0),        # back pushes away
        "shelf": (0, 0, 0.3),       # shelves float up slightly
        "door": (0, -1.5, 0),       # doors push forward
        "rail": (0, 0, 0.2),        # rails float slightly
        "kickplate": (0, 0, -1.5),  # kickplate pushes down
        "kickplate_return": (0, 0, -1.5),
        "drawer_front": (0, -1.5, 0),
        "drawer_side": (0, -1.5, 0),
        "drawer_back": (0, -1.5, 0),
        "drawer_bottom": (0, -1.5, 0),
        "floor": (0, 0, -1.0),
    }

    lines = [
        "import FreeCAD",
        "import Part",
        "",
        f"# EXPLODED VIEW — {furniture_type}",
        f'doc = FreeCAD.newDocument("{doc_name}")',
        "",
    ]

    # Create groups
    group_lines, role_to_group = _generate_groups_code(parts)
    lines.extend(group_lines)

    for part in parts:
        pid = part["id"]
        role = part["role"]
        pos = part.get("position_mm", {"x": 0, "y": 0, "z": 0})

        # Calculate explosion offset
        dx, dy, dz = _explosion.get(role, (0, 0, 0))
        if role == "side" and "right" in pid:
            dx = abs(dx)
        elif role == "side" and "left" in pid:
            dx = -abs(dx)

        offset = (dx * gap_mm, dy * gap_mm, dz * gap_mm)
        lines.extend(_generate_panel_code(part, role_to_group, offset=offset))

    lines.append("doc.recompute()")
    lines.append("FreeCADGui.activeDocument().activeView().viewIsometric()")
    lines.append("FreeCADGui.SendMsgToActiveView('ViewFit')")
    lines.append(f'print("Exploded view: {len(parts)} panels")')

    return "\n".join(lines)


def cut_layout_script(cut_result: dict, doc_name: str = "CutLayout") -> str:
    """Generate a FreeCAD script that visualizes the cut optimization layout.

    Creates a flat 2D-like view of each sheet with placed panels.

    Args:
        cut_result: Result from optimize_cuts tool.
        doc_name: Name for the FreeCAD document.

    Returns:
        Python code string for FreeCAD.
    """
    sheets = cut_result.get("sheets", [])
    sheet_size = cut_result.get("sheet_size_mm", {})
    sheet_w = sheet_size.get("width", 2440)
    sheet_h = sheet_size.get("height", 1220)
    panel_thickness = 3  # visual thickness for the 2D layout

    lines = [
        "import FreeCAD",
        "import Part",
        "",
        f"# CUT LAYOUT — {len(sheets)} sheet(s)",
        f'doc = FreeCAD.newDocument("{doc_name}")',
        "",
    ]

    # Colors for alternating pieces
    _piece_colors = [
        (0.90, 0.75, 0.55, 1.0),
        (0.70, 0.85, 0.65, 1.0),
        (0.60, 0.75, 0.90, 1.0),
        (0.90, 0.72, 0.40, 1.0),
        (0.85, 0.60, 0.60, 1.0),
        (0.65, 0.80, 0.80, 1.0),
        (0.80, 0.65, 0.80, 1.0),
    ]

    for si, sheet in enumerate(sheets):
        # Sheet base offset (stack sheets along Y)
        y_offset = si * (sheet_h + 100)
        sheet_num = sheet.get("sheet_number", si + 1)

        # Create group for this sheet
        grp_name = f"Tablero_{sheet_num}"
        lines.append(f"# -- Sheet {sheet_num} --")
        lines.append(f'{grp_name} = doc.addObject("App::DocumentObjectGroup", "{grp_name}")')
        lines.append(f'{grp_name}.Label = "Tablero {sheet_num}"')

        # Draw sheet outline (thin box)
        sheet_name = f"Sheet_{sheet_num}"
        lines.append(f'{sheet_name} = doc.addObject("Part::Box", "{sheet_name}")')
        lines.append(f"{sheet_name}.Length = {sheet_w}")
        lines.append(f"{sheet_name}.Width = {sheet_h}")
        lines.append(f"{sheet_name}.Height = 1")
        lines.append(
            f"{sheet_name}.Placement = FreeCAD.Placement("
            f"FreeCAD.Vector(0, {y_offset}, 0), "
            f"FreeCAD.Rotation(0, 0, 0, 1))"
        )
        lines.append(f"{sheet_name}.ViewObject.ShapeColor = (0.95, 0.93, 0.88, 1.0)")
        lines.append(f"{sheet_name}.ViewObject.Transparency = 0")
        lines.append(f"{grp_name}.addObject({sheet_name})")
        lines.append("")

        # Draw pieces on this sheet
        pieces = sheet.get("pieces", [])
        for pi, piece in enumerate(pieces):
            piece_id = piece.get("id", f"piece_{pi}")
            px = piece.get("x", 0)
            py = piece.get("y", 0)
            pw = piece.get("width", 100)
            ph = piece.get("height", 100)
            rotated = piece.get("rotated", False)

            safe = f"S{sheet_num}_{_safe_name(piece_id)}"
            color = _piece_colors[pi % len(_piece_colors)]

            lines.append(f'{safe} = doc.addObject("Part::Box", "{safe}")')
            lines.append(f"{safe}.Length = {pw}")
            lines.append(f"{safe}.Width = {ph}")
            lines.append(f"{safe}.Height = {panel_thickness}")
            lines.append(
                f"{safe}.Placement = FreeCAD.Placement("
                f"FreeCAD.Vector({px}, {y_offset + py}, 1), "
                f"FreeCAD.Rotation(0, 0, 0, 1))"
            )
            lines.append(f"{safe}.ViewObject.ShapeColor = {color}")
            lines.append(f"{safe}.ViewObject.Transparency = 0")
            lines.append(f'{safe}.Label = "{piece_id}{" (R)" if rotated else ""}"')
            lines.append(f"{grp_name}.addObject({safe})")
            lines.append("")

    lines.append("doc.recompute()")
    lines.append("FreeCADGui.activeDocument().activeView().viewTop()")
    lines.append("FreeCADGui.SendMsgToActiveView('ViewFit')")
    lines.append(f'print("Cut layout: {len(sheets)} sheets rendered")')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Import from FreeCAD
# ---------------------------------------------------------------------------

def import_script(doc_name: str = "Furniture") -> str:
    """Generate a FreeCAD Python script that extracts all panels as JSON.

    The script reads every App::Part in the document, extracts custom
    properties (Role, Material, Thickness_mm, RealDimensions, EdgeBanding)
    and the Placement, then prints a JSON object to stdout.

    For objects WITHOUT custom properties (manually created Part::Box),
    it falls back to reading geometry (Length, Width, Height) and attempts
    to infer the role from the object name.

    Args:
        doc_name: Name of the FreeCAD document to read.

    Returns:
        Python code string. Execute via freecad-mcp's execute_code.
        The stdout will contain a JSON string to pass to parse_freecad_export().
    """
    # The script runs inside FreeCAD's Python interpreter
    return '''import FreeCAD
import json

doc_name = "''' + doc_name + '''"
doc = FreeCAD.getDocument(doc_name)
if doc is None:
    print(json.dumps({"error": f"Document '{doc_name}' not found"}))
else:
    panels = []
    groups_found = []

    for obj in doc.Objects:
        # Process App::Part containers (our standard)
        if obj.TypeId == "App::Part":
            panel = {"id": obj.Name, "label": obj.Label, "source": "App::Part"}

            # Read custom properties
            for prop in ["Role", "PanelMaterial", "Thickness_mm", "RealDimensions", "EdgeBanding"]:
                if hasattr(obj, prop):
                    val = getattr(obj, prop)
                    panel[prop] = val

            # Read placement
            pl = obj.Placement
            panel["position_mm"] = {
                "x": round(pl.Base.x, 2),
                "y": round(pl.Base.y, 2),
                "z": round(pl.Base.z, 2),
            }

            # Read child shape dimensions
            for child in obj.Group:
                if hasattr(child, "Length") and hasattr(child, "Width") and hasattr(child, "Height"):
                    panel["freecad_dims"] = {
                        "Length": round(child.Length, 2),
                        "Width": round(child.Width, 2),
                        "Height": round(child.Height, 2),
                    }
                    # Read color
                    if hasattr(child, "ViewObject") and hasattr(child.ViewObject, "ShapeColor"):
                        panel["color"] = list(child.ViewObject.ShapeColor)
                    break

            panels.append(panel)

        # Process standalone Part::Box (manually created)
        elif obj.TypeId == "Part::Box":
            # Skip if it's inside an App::Part (already processed)
            parents = obj.InList
            if any(p.TypeId == "App::Part" for p in parents):
                continue

            panel = {
                "id": obj.Name,
                "label": obj.Label,
                "source": "Part::Box",
            }

            panel["freecad_dims"] = {
                "Length": round(obj.Length, 2),
                "Width": round(obj.Width, 2),
                "Height": round(obj.Height, 2),
            }

            pl = obj.Placement
            panel["position_mm"] = {
                "x": round(pl.Base.x, 2),
                "y": round(pl.Base.y, 2),
                "z": round(pl.Base.z, 2),
            }

            if hasattr(obj, "ViewObject") and hasattr(obj.ViewObject, "ShapeColor"):
                panel["color"] = list(obj.ViewObject.ShapeColor)

            panels.append(panel)

        # Track groups
        elif obj.TypeId == "App::DocumentObjectGroup":
            groups_found.append({"name": obj.Name, "label": obj.Label, "count": len(obj.Group)})

    result = {
        "document": doc_name,
        "total_panels": len(panels),
        "groups": groups_found,
        "panels": panels,
    }
    print("FURNITURE_SPEC_JSON:" + json.dumps(result, ensure_ascii=False))
'''


# -- Reverse coordinate mapping --
_REVERSE_DIMS = {
    # role: which FreeCAD axis is (width, height, thickness)
    # FreeCAD axes: Length=X, Width=Y, Height=Z
    "side":        ("Width", "Height", "Length"),     # thin in X
    "divider":     ("Width", "Height", "Length"),     # thin in X
    "bottom":      ("Length", "Width", "Height"),     # thin in Z
    "top_panel":   ("Length", "Width", "Height"),     # thin in Z
    "shelf":       ("Length", "Width", "Height"),     # thin in Z
    "floor":       ("Length", "Width", "Height"),     # thin in Z
    "back":        ("Length", "Height", "Width"),     # thin in Y
    "door":        ("Length", "Height", "Width"),     # thin in Y
    "drawer_front":("Length", "Height", "Width"),     # thin in Y
    "drawer_side": ("Width", "Height", "Length"),     # thin in X
    "drawer_back": ("Length", "Height", "Width"),     # thin in Y
    "drawer_bottom":("Length", "Width", "Height"),    # thin in Z
    "rail":        ("Length", "Height", "Width"),     # thin in Y
    "kickplate":   ("Length", "Height", "Width"),     # thin in Y
    "kickplate_return": ("Height", "Length", "Width"),  # thin in X, like side
}


def _infer_role_from_name(name: str) -> str:
    """Best-effort role inference from object name/label."""
    n = name.lower()
    if "side" in n or "lateral" in n:
        return "side"
    if "bottom" in n or "piso" in n or "floor" in n:
        return "bottom"
    if "top" in n or "tapa" in n or "techo" in n:
        return "top_panel"
    if "back" in n or "respaldo" in n or "trasero" in n:
        return "back"
    if "shelf" in n or "repisa" in n or "estante" in n:
        return "shelf"
    if "door" in n or "puerta" in n:
        return "door"
    if "rail" in n or "travesaño" in n or "travesano" in n:
        return "rail"
    if "kick" in n or "zocalo" in n or "zócalo" in n:
        return "kickplate"
    if "divid" in n or "division" in n or "división" in n:
        return "divider"
    if "drawer" in n or "cajon" in n or "cajón" in n:
        return "drawer_front"
    return "unknown"


def _infer_role_from_geometry(dims: dict, pos: dict) -> str:
    """Infer role from FreeCAD box dimensions and position.

    Heuristic based on which axis is thinnest:
    - Thin in X (Length) → side or divider
    - Thin in Z (Height) → shelf, bottom, or top_panel
    - Thin in Y (Width) → back, door, rail, or kickplate
    """
    l, w, h = dims["Length"], dims["Width"], dims["Height"]
    min_dim = min(l, w, h)

    if min_dim == h and h <= 20:
        # Thin in Z — horizontal panel
        if pos["z"] < 20:
            return "bottom"
        return "shelf"
    if min_dim == l and l <= 20:
        # Thin in X — vertical side panel
        return "side"
    if min_dim == w and w <= 20:
        # Thin in Y — back or front panel
        if pos["y"] > 200:
            return "back"
        return "door"

    return "unknown"


def parse_freecad_export(raw_output: str) -> dict:
    """Parse the JSON output from the import script into a furniture spec.

    Handles two cases:
    1. Panels with custom properties (from our system) → direct reconstruction
    2. Standalone Part::Box (manually created) → geometry-based inference

    Args:
        raw_output: The stdout from executing the import script in FreeCAD.
            Must contain the line starting with "FURNITURE_SPEC_JSON:".

    Returns:
        A furniture spec compatible with validate_structure, generate_bom, etc.
        Includes a "warnings" key if any panels needed role inference.
    """
    # Extract JSON from output
    json_str = None
    for line in raw_output.split("\n"):
        if line.startswith("FURNITURE_SPEC_JSON:"):
            json_str = line[len("FURNITURE_SPEC_JSON:"):]
            break

    if json_str is None:
        return {"error": "No FURNITURE_SPEC_JSON found in output. Ensure the import script ran correctly."}

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON in output: {e}"}

    if "error" in data:
        return data

    panels = data.get("panels", [])
    if not panels:
        return {"error": "No panels found in document."}

    parts = []
    warnings = []
    materials_seen = set()

    for panel in panels:
        pid = panel["id"]

        # Determine role
        role = panel.get("Role", "")
        if not role:
            # Try inferring from name
            role = _infer_role_from_name(panel.get("label", pid))
            if role == "unknown" and "freecad_dims" in panel and "position_mm" in panel:
                role = _infer_role_from_geometry(panel["freecad_dims"], panel["position_mm"])
            if role == "unknown":
                warnings.append(f"Could not determine role for '{pid}'. Assigned 'unknown'. Please set Role property in FreeCAD.")

        # Determine dimensions
        real_dims = panel.get("RealDimensions", "")
        if real_dims and "x" in real_dims:
            # Parse "580x700x16" format
            try:
                parts_str = real_dims.split("x")
                width_mm = float(parts_str[0])
                height_mm = float(parts_str[1])
                thickness_mm = float(parts_str[2])
            except (ValueError, IndexError):
                real_dims = ""  # Fall through to geometry-based

        if not real_dims and "freecad_dims" in panel:
            # Reverse-map from FreeCAD dimensions
            fd = panel["freecad_dims"]
            mapping = _REVERSE_DIMS.get(role)
            if mapping:
                width_mm = fd[mapping[0]]
                height_mm = fd[mapping[1]]
                thickness_mm = fd[mapping[2]]
            else:
                # Unknown role — use sorted dims (largest=width, mid=height, smallest=thickness)
                sorted_dims = sorted([fd["Length"], fd["Width"], fd["Height"]], reverse=True)
                width_mm = sorted_dims[0]
                height_mm = sorted_dims[1]
                thickness_mm = sorted_dims[2]
                warnings.append(f"Panel '{pid}' has unknown role — dimensions assigned by size (width={width_mm}, height={height_mm}, thickness={thickness_mm}).")

        if not real_dims and "freecad_dims" not in panel:
            warnings.append(f"Panel '{pid}' has no dimensions. Skipping.")
            continue

        # Build part dict
        material = panel.get("PanelMaterial", "")
        if material:
            materials_seen.add(material)

        part = {
            "id": pid,
            "role": role,
            "width_mm": width_mm,
            "height_mm": height_mm,
            "thickness_mm": thickness_mm,
            "material": material,
            "position_mm": panel.get("position_mm", {"x": 0, "y": 0, "z": 0}),
        }

        edge_banding = panel.get("EdgeBanding", "")
        if edge_banding:
            part["edge_banding"] = edge_banding

        parts.append(part)

    # Infer furniture-level metadata
    all_positions_z = [p["position_mm"]["z"] for p in parts]
    max_z = max(all_positions_z) if all_positions_z else 0
    max_heights = [p["height_mm"] for p in parts if p["role"] in ("side", "divider")]
    furniture_height_mm = (max_z + max(max_heights)) if max_heights else max_z

    all_positions_x = [p["position_mm"]["x"] + p.get("width_mm", 0) for p in parts]
    furniture_width_mm = max(all_positions_x) if all_positions_x else 0

    all_positions_y = [p["position_mm"]["y"] + p.get("height_mm", 0) for p in parts if p["role"] in ("side", "bottom")]
    furniture_depth_mm = max(all_positions_y) if all_positions_y else 0

    spec = {
        "furniture_type": "imported",
        "source": "freecad",
        "document": data.get("document", ""),
        "material": list(materials_seen)[0] if len(materials_seen) == 1 else "mixed",
        "dimensions_cm": {
            "width": round(furniture_width_mm / 10, 1),
            "height": round(furniture_height_mm / 10, 1),
            "depth": round(furniture_depth_mm / 10, 1),
        },
        "parts": parts,
    }

    if warnings:
        spec["import_warnings"] = warnings

    return spec


# ---------------------------------------------------------------------------
# TechDraw — 2D technical drawing with orthographic views
# ---------------------------------------------------------------------------


def techdraw_script(spec: dict, doc_name: str = "TechDraw", export_svg: bool = True, export_dir: str = "/tmp") -> str:
    """Generate a FreeCAD Python script that creates a TechDraw page.

    Produces an A3 landscape sheet with three orthographic views
    (front, top, right) of the assembled furniture, plus overall
    dimension annotations for width, height, and depth.

    The script assumes the 3D model already exists in FreeCAD
    (built via spec_to_freecad_script). It reads the existing
    document or creates a new one and rebuilds the geometry inline
    so the TechDraw page has shapes to reference.

    Args:
        spec: Furniture spec as returned by design_furniture.
        doc_name: Name for the FreeCAD document (default: "TechDraw").

    Returns:
        Python code string for FreeCAD's execute_code.
    """
    parts = spec.get("parts", [])
    furniture_type = spec.get("furniture_type", "cabinet")
    dims = spec.get("dimensions_cm", {})
    material_name = spec.get("material", "")

    # Compute overall bounding box from parts for dimension annotations
    # We'll calculate in the script itself to keep it self-contained.

    lines = [
        "import FreeCAD",
        "import Part",
        "",
        f"# TechDraw — {furniture_type} "
        f"({dims.get('width', '?')}x{dims.get('height', '?')}x{dims.get('depth', '?')} cm)",
        f"# Material: {material_name}",
        "",
        "# --- Rebuild geometry as a compound for TechDraw ---",
        "shapes = []",
    ]

    # Generate simple boxes for each part (no App::Part, just shapes for compound)
    for part in parts:
        pid = part["id"]
        safe = _safe_name(pid)
        length, width, height = _box_dims(part)
        pos = part.get("position_mm", {"x": 0, "y": 0, "z": 0})
        lines.append(f"_b = Part.makeBox({length}, {width}, {height})")
        lines.append(
            f"_b.translate(FreeCAD.Vector({pos['x']}, {pos['y']}, {pos['z']}))"
        )
        lines.append(f"shapes.append(_b)  # {pid}")

    lines.extend([
        "",
        "compound = Part.makeCompound(shapes)",
        "",
        f'doc = FreeCAD.newDocument("{doc_name}")',
        'body = doc.addObject("Part::Feature", "FurnitureCompound")',
        "body.Shape = compound",
        "body.ViewObject.Visibility = False",
        "",
        "# --- TechDraw page ---",
        "import TechDraw",
        "",
        "page = doc.addObject('TechDraw::DrawPage', 'Page')",
        "template = doc.addObject('TechDraw::DrawSVGTemplate', 'Template')",
        "template.Template = FreeCAD.getResourceDir() + 'Mod/TechDraw/Templates/A3_Landscape_blank.svg'",
        "page.Template = template",
        "",
        "# Front view (looking from -Y toward +Y)",
        "front = doc.addObject('TechDraw::DrawViewPart', 'FrontView')",
        "front.Source = [body]",
        "front.Direction = FreeCAD.Vector(0, -1, 0)",
        "front.XDirection = FreeCAD.Vector(1, 0, 0)",
        "front.ScaleType = 'Custom'",
    ])

    # Auto-scale: fit the largest dimension into ~250mm on paper
    lines.extend([
        "",
        "# Auto-scale to fit A3",
        "bbox = compound.BoundBox",
        "max_dim = max(bbox.XLength, bbox.YLength, bbox.ZLength)",
        "scale = 250.0 / max_dim if max_dim > 0 else 0.1",
        "scale = round(scale, 3)",
        "front.Scale = scale",
        "front.X = 150",
        "front.Y = 150",
        "page.addView(front)",
        "",
        "# Top view (looking from +Z down)",
        "top_view = doc.addObject('TechDraw::DrawViewPart', 'TopView')",
        "top_view.Source = [body]",
        "top_view.Direction = FreeCAD.Vector(0, 0, -1)",
        "top_view.XDirection = FreeCAD.Vector(1, 0, 0)",
        "top_view.ScaleType = 'Custom'",
        "top_view.Scale = scale",
        "top_view.X = 150",
        "top_view.Y = 50",
        "page.addView(top_view)",
        "",
        "# Right view (looking from +X toward -X)",
        "right_view = doc.addObject('TechDraw::DrawViewPart', 'RightView')",
        "right_view.Source = [body]",
        "right_view.Direction = FreeCAD.Vector(1, 0, 0)",
        "right_view.XDirection = FreeCAD.Vector(0, 1, 0)",
        "right_view.ScaleType = 'Custom'",
        "right_view.Scale = scale",
        "right_view.X = 330",
        "right_view.Y = 150",
        "page.addView(right_view)",
        "",
        "# --- Overall dimension annotations ---",
        "# Width annotation (horizontal on front view)",
        "dim_w = doc.addObject('TechDraw::DrawViewDimension', 'DimWidth')",
        "dim_w.Type = 'Distance'",
        "dim_w.FormatSpec = f'{bbox.XLength:.0f}'",
        "",
        "# Height annotation (vertical on front view)",
        "dim_h = doc.addObject('TechDraw::DrawViewDimension', 'DimHeight')",
        "dim_h.Type = 'Distance'",
        "dim_h.FormatSpec = f'{bbox.ZLength:.0f}'",
        "",
        "# Depth annotation (horizontal on top view)",
        "dim_d = doc.addObject('TechDraw::DrawViewDimension', 'DimDepth')",
        "dim_d.Type = 'Distance'",
        "dim_d.FormatSpec = f'{bbox.YLength:.0f}'",
        "",
        "doc.recompute()",
        f'print("TechDraw page created for {furniture_type} with 3 views at scale", scale)',
    ])

    if export_svg:
        svg_filename = f"{doc_name}.svg"
        svg_path = f"{export_dir.rstrip('/')}/{svg_filename}"
        lines.extend([
            "",
            "# --- Export TechDraw page to SVG ---",
            "try:",
            "    import TechDrawGui",
            f"    svg_path = r'{svg_path}'",
            "    TechDrawGui.exportPageAsSvg(page, svg_path)",
            f'    print("SVG exported to:", svg_path)',
            "except Exception as _svg_err:",
            f'    print("SVG export failed (GUI may not be available):", _svg_err)',
        ])

    return "\n".join(lines)
