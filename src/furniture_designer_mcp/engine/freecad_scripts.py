"""Generate FreeCAD Python scripts from furniture specs.

These scripts are meant to be executed via freecad-mcp's execute_code tool.
Each function returns a Python code string ready for FreeCAD's interpreter.
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


def spec_to_freecad_script(spec: dict, doc_name: str = "Furniture") -> str:
    """Generate a FreeCAD Python script that builds the full 3D model.

    Args:
        spec: Furniture spec as returned by design_furniture.
        doc_name: Name for the FreeCAD document.

    Returns:
        Python code string for FreeCAD's execute_code.
    """
    parts = spec.get("parts", [])
    furniture_type = spec.get("furniture_type", "cabinet")
    dims = spec.get("dimensions_cm", {})

    lines = [
        "import FreeCAD",
        "import Part",
        "",
        f"# {furniture_type} — {dims.get('width', '?')}x{dims.get('height', '?')}x{dims.get('depth', '?')} cm",
        f'doc = FreeCAD.newDocument("{doc_name}")',
        "",
    ]

    for part in parts:
        pid = part["id"]
        role = part["role"]
        length, width, height = _box_dims(part)
        pos = part.get("position_mm", {"x": 0, "y": 0, "z": 0})
        color = _COLORS.get(role, _DEFAULT_COLOR)

        # Sanitize name for FreeCAD (no spaces, starts with letter)
        safe_name = pid.replace("-", "_").replace(" ", "_")

        lines.append(f"# -- {pid} ({role}) --")
        lines.append(f'{safe_name} = doc.addObject("Part::Box", "{safe_name}")')
        lines.append(f"{safe_name}.Length = {length}")
        lines.append(f"{safe_name}.Width = {width}")
        lines.append(f"{safe_name}.Height = {height}")
        lines.append(
            f"{safe_name}.Placement = FreeCAD.Placement("
            f"FreeCAD.Vector({pos['x']}, {pos['y']}, {pos['z']}), "
            f"FreeCAD.Rotation(0, 0, 0, 1))"
        )
        lines.append(
            f"{safe_name}.ViewObject.ShapeColor = {color}"
        )
        lines.append(f"{safe_name}.ViewObject.Transparency = 10")
        lines.append(f'# Label: {pid} [{part["width_mm"]}x{part["height_mm"]}x{part["thickness_mm"]}mm]')
        lines.append("")

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

    for i, part in enumerate(parts):
        pid = part["id"]
        role = part["role"]
        length, width, height = _box_dims(part)
        pos = part.get("position_mm", {"x": 0, "y": 0, "z": 0})
        color = _COLORS.get(role, _DEFAULT_COLOR)
        safe_name = pid.replace("-", "_").replace(" ", "_")

        # Apply explosion offset
        dx, dy, dz = _explosion.get(role, (0, 0, 0))
        # For sides, left goes negative, right goes positive
        if role == "side" and "right" in pid:
            dx = abs(dx)
        elif role == "side" and "left" in pid:
            dx = -abs(dx)

        ex = pos["x"] + dx * gap_mm
        ey = pos["y"] + dy * gap_mm
        ez = pos["z"] + dz * gap_mm

        lines.append(f'{safe_name} = doc.addObject("Part::Box", "{safe_name}")')
        lines.append(f"{safe_name}.Length = {length}")
        lines.append(f"{safe_name}.Width = {width}")
        lines.append(f"{safe_name}.Height = {height}")
        lines.append(
            f"{safe_name}.Placement = FreeCAD.Placement("
            f"FreeCAD.Vector({ex}, {ey}, {ez}), "
            f"FreeCAD.Rotation(0, 0, 0, 1))"
        )
        lines.append(f"{safe_name}.ViewObject.ShapeColor = {color}")
        lines.append(f"{safe_name}.ViewObject.Transparency = 15")
        lines.append("")

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
    sheet_w = cut_result.get("sheet_width_mm", 2440)
    sheet_h = cut_result.get("sheet_height_mm", 1220)
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

        # Draw sheet outline (thin box)
        sheet_name = f"Sheet_{si + 1}"
        lines.append(f"# -- Sheet {si + 1} --")
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
        lines.append("")

        # Draw pieces on this sheet
        placements = sheet.get("placements", [])
        for pi, piece in enumerate(placements):
            piece_id = piece.get("id", f"piece_{pi}")
            px = piece.get("x", 0)
            py = piece.get("y", 0)
            pw = piece.get("placed_width", piece.get("width", 100))
            ph = piece.get("placed_height", piece.get("height", 100))

            safe_name = f"S{si + 1}_{piece_id}".replace("-", "_").replace(" ", "_")
            color = _piece_colors[pi % len(_piece_colors)]

            lines.append(f'{safe_name} = doc.addObject("Part::Box", "{safe_name}")')
            lines.append(f"{safe_name}.Length = {pw}")
            lines.append(f"{safe_name}.Width = {ph}")
            lines.append(f"{safe_name}.Height = {panel_thickness}")
            lines.append(
                f"{safe_name}.Placement = FreeCAD.Placement("
                f"FreeCAD.Vector({px}, {y_offset + py}, 1), "
                f"FreeCAD.Rotation(0, 0, 0, 1))"
            )
            lines.append(f"{safe_name}.ViewObject.ShapeColor = {color}")
            lines.append(f"{safe_name}.ViewObject.Transparency = 0")
            lines.append("")

    lines.append("doc.recompute()")
    lines.append("FreeCADGui.activeDocument().activeView().viewTop()")
    lines.append("FreeCADGui.SendMsgToActiveView('ViewFit')")
    lines.append(f'print("Cut layout: {len(sheets)} sheets rendered")')

    return "\n".join(lines)
