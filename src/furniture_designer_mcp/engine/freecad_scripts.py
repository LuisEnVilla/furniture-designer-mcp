"""Generate FreeCAD Python scripts from furniture specs.

These scripts are meant to be executed via freecad-mcp's execute_code tool.
Each function returns a Python code string ready for FreeCAD's interpreter.

Best practices applied:
- App::Part container per panel (proper component pattern)
- Groups by role for tree organization (Estructura, Puertas, etc.)
- Custom properties for material, thickness, role, edge banding
- Descriptive labels on each component
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
    "divider": (0.90, 0.72, 0.40, 1.0),
    "drawer_front": (0.60, 0.75, 0.90, 1.0),
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
    "back": "Respaldo",
    "shelf": "Repisas",
    "door": "Puertas",
    "drawer_front": "Cajones",
}

# -- Descriptive labels by role --
_ROLE_LABELS = {
    "side": "Lateral",
    "bottom": "Piso",
    "top_panel": "Tapa superior",
    "floor": "Piso",
    "shelf": "Repisa",
    "back": "Respaldo",
    "door": "Puerta",
    "rail": "Travesaño",
    "kickplate": "Zócalo",
    "divider": "División vertical",
    "drawer_front": "Frente de cajón",
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
    elif role in ("rail",):
        # Horizontal beam
        # wide in X, thin in Y, height in Z
        return (w, t, h)
    elif role in ("kickplate",):
        # Vertical panel at front-bottom
        # wide in X, thin in Y, height in Z
        return (w, t, h)
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
    lines.append(f'{safe}_part.Label = "{label} — {pid}"')

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
    lines.append(f'{safe}_part.addProperty("App::PropertyString", "Material", "Furniture", "Material type")')
    lines.append(f'{safe}_part.Material = "{material}"')
    lines.append(f'{safe}_part.addProperty("App::PropertyFloat", "Thickness_mm", "Furniture", "Panel thickness in mm")')
    lines.append(f"{safe}_part.Thickness_mm = {thickness}")
    lines.append(f'{safe}_part.addProperty("App::PropertyString", "RealDimensions", "Furniture", "WxHxT in mm")')
    lines.append(f'{safe}_part.RealDimensions = "{part["width_mm"]}x{part["height_mm"]}x{thickness}"')

    if edge_banding:
        eb_str = edge_banding if isinstance(edge_banding, str) else json.dumps(edge_banding, ensure_ascii=False)
        lines.append(f'{safe}_part.addProperty("App::PropertyString", "EdgeBanding", "Furniture", "Edge banding spec")')
        lines.append(f'{safe}_part.EdgeBanding = "{eb_str}"')

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
        "drawer_front": (0, -1.5, 0),
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
