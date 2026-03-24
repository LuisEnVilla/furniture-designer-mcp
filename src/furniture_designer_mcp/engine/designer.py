"""Furniture spec generator.

Takes user parameters + ergonomic standards + structural rules and produces
a complete JSON spec with all parts, positions, hardware, and notes.
"""

from __future__ import annotations

from ..knowledge.ergonomics import ERGONOMIC_STANDARDS
from ..knowledge.materials import MATERIALS
from ..knowledge.structural_rules import STRUCTURAL_RULES


def generate_furniture_spec(
    furniture_type: str,
    width: float,
    height: float,
    depth: float,
    material: str = "melamine_16",
    options: dict | None = None,
) -> dict:
    """Generate a complete furniture specification.

    All input dimensions in cm. Output dimensions in mm for manufacturing.
    """
    opts = options or {}
    mat = MATERIALS.get(material)
    if mat is None:
        raise ValueError(f"Unknown material: {material}")

    standards = ERGONOMIC_STANDARDS.get(furniture_type, ERGONOMIC_STANDARDS["general"])
    t = mat["thickness_mm"]  # material thickness in mm

    # Convert to mm for internal calculations
    W = width * 10   # total width mm
    H = height * 10  # total height mm
    D = depth * 10   # total depth mm

    parts: list[dict] = []
    hardware: list[dict] = []
    notes: list[str] = []

    # --- Dispatch to type-specific builder ---
    if furniture_type == "kitchen_base":
        parts, hardware, notes = _build_kitchen_base(W, H, D, t, opts, standards, mat)
    elif furniture_type == "kitchen_wall":
        parts, hardware, notes = _build_box_cabinet(W, H, D, t, opts, standards, mat, has_kickplate=False)
    elif furniture_type == "bookshelf":
        parts, hardware, notes = _build_box_cabinet(W, H, D, t, opts, standards, mat, has_kickplate=False)
    elif furniture_type == "closet":
        parts, hardware, notes = _build_box_cabinet(W, H, D, t, opts, standards, mat, has_kickplate=True)
    elif furniture_type == "desk":
        parts, hardware, notes = _build_desk(W, H, D, t, opts, standards, mat)
    elif furniture_type == "vanity":
        parts, hardware, notes = _build_kitchen_base(W, H, D, t, opts, standards, mat)
    else:
        parts, hardware, notes = _build_box_cabinet(W, H, D, t, opts, standards, mat, has_kickplate=False)

    # --- Structural validation notes ---
    max_span = mat["max_span_no_support_cm"]
    if width > max_span:
        notes.append(
            f"ATENCIÓN: Ancho ({width}cm) excede tramo libre máximo del material "
            f"({max_span}cm). Se agregó división vertical."
        )

    spec = {
        "furniture_type": furniture_type,
        "dimensions_cm": {"width": width, "height": height, "depth": depth},
        "dimensions_mm": {"width": W, "height": H, "depth": D},
        "material": material,
        "material_thickness_mm": t,
        "parts": parts,
        "hardware": hardware,
        "notes": notes,
        "standards_applied": standards.get("name", furniture_type),
    }
    return spec


# ---------------------------------------------------------------------------
# Builder: kitchen base cabinet
# ---------------------------------------------------------------------------

def _build_kitchen_base(W, H, D, t, opts, standards, mat):
    parts = []
    hardware = []
    notes = []

    kickplate_h = opts.get("kickplate_height", 10) * 10  # mm
    body_h = H - kickplate_h  # cabinet body height
    inner_w = W - 2 * t       # inner width
    inner_d = D               # depth
    max_span = mat["max_span_no_support_cm"]

    # Sides
    parts.append(_panel("side_left", "side", D, body_h, t, pos=[0, 0, kickplate_h]))
    parts.append(_panel("side_right", "side", D, body_h, t, pos=[W - t, 0, kickplate_h]))

    # Bottom
    parts.append(_panel("bottom", "bottom", inner_w, D, t, pos=[t, 0, kickplate_h]))

    # Vertical divider if too wide
    num_sections = 1
    if (W / 10) > max_span:
        num_sections = 2
        mid_x = W / 2 - t / 2
        parts.append(_panel("divider_center", "divider", D, body_h, t, pos=[mid_x, 0, kickplate_h]))

    # Top rails (no full top panel — countertop goes on top)
    rail_h = 80  # 8cm rail
    parts.append(_panel("rail_front", "rail", inner_w, rail_h, t, pos=[t, 0, kickplate_h + body_h - rail_h]))
    parts.append(_panel("rail_back", "rail", inner_w, rail_h, t, pos=[t, D - t, kickplate_h + body_h - rail_h]))

    # Back panel
    back_t = 3  # 3mm MDF
    parts.append(_panel("back", "back", inner_w, body_h, back_t, pos=[t, D - back_t, kickplate_h]))

    # Shelf
    num_shelves = opts.get("num_shelves", 1)
    section_w = inner_w / num_sections
    for i in range(num_shelves):
        shelf_z = kickplate_h + body_h * (i + 1) / (num_shelves + 1)
        parts.append(_panel(f"shelf_{i+1}", "shelf", section_w - 2, D - 20, t,
                            pos=[t + 1, 0, shelf_z], adjustable=True))

    # Kickplate
    setback = 50  # 5cm setback
    parts.append(_panel("kickplate", "kickplate", inner_w, kickplate_h, t, pos=[t, setback, 0]))

    # Door(s)
    door_type = opts.get("door_type", "single" if W <= 600 else "double")
    door_gap = 3  # mm gap
    if door_type == "double":
        door_w = (W - door_gap) / 2
        door_h = body_h - door_gap
        parts.append(_panel("door_left", "door", door_w, door_h, t, pos=[0, 0, kickplate_h]))
        parts.append(_panel("door_right", "door", door_w, door_h, t, pos=[door_w + door_gap, 0, kickplate_h]))
        hardware.append(_hinge_set("door_left", door_h))
        hardware.append(_hinge_set("door_right", door_h))
    else:
        door_w = W - door_gap
        door_h = body_h - door_gap
        parts.append(_panel("door", "door", door_w, door_h, t, pos=[0, 0, kickplate_h]))
        hardware.append(_hinge_set("door", door_h))

    # Connectors
    hardware.append({"type": "confirmat_7x50", "usage": "panel joints", "estimated_qty": _estimate_confirmats(parts)})
    hardware.append({"type": "shelf_pin_5mm", "qty": num_shelves * 4, "usage": "adjustable shelves"})

    notes.append(f"Zócalo retranqueado {setback/10}cm del frente.")
    notes.append("Travesaños superior frontal y trasero incluidos (sin tapa superior — va cubierta).")

    return parts, hardware, notes


# ---------------------------------------------------------------------------
# Builder: generic box cabinet (bookshelf, wall cabinet, closet)
# ---------------------------------------------------------------------------

def _build_box_cabinet(W, H, D, t, opts, standards, mat, has_kickplate=False):
    parts = []
    hardware = []
    notes = []

    kickplate_h = opts.get("kickplate_height", 10) * 10 if has_kickplate else 0
    body_h = H - kickplate_h
    inner_w = W - 2 * t
    max_span = mat["max_span_no_support_cm"]

    # Sides
    parts.append(_panel("side_left", "side", D, body_h, t, pos=[0, 0, kickplate_h]))
    parts.append(_panel("side_right", "side", D, body_h, t, pos=[W - t, 0, kickplate_h]))

    # Top and bottom
    parts.append(_panel("top", "top_panel", inner_w, D, t, pos=[t, 0, kickplate_h + body_h - t]))
    parts.append(_panel("bottom", "bottom", inner_w, D, t, pos=[t, 0, kickplate_h]))

    # Vertical divider if too wide
    num_sections = 1
    if (W / 10) > max_span:
        num_sections = 2
        mid_x = W / 2 - t / 2
        parts.append(_panel("divider_center", "divider", D, body_h, t, pos=[mid_x, 0, kickplate_h]))
        notes.append(f"División vertical agregada: ancho ({W/10}cm) excede tramo libre ({max_span}cm).")

    # Back panel
    back_t = 3
    parts.append(_panel("back", "back", inner_w, body_h, back_t, pos=[t, D - back_t, kickplate_h]))

    # Rails for wide cabinets
    if W > 600:
        rail_h = 80
        parts.append(_panel("rail_back_top", "rail", inner_w, rail_h, t,
                            pos=[t, D - t, kickplate_h + body_h - t - rail_h]))
        notes.append("Travesaño trasero superior agregado por ancho > 60cm.")

    # Shelves
    num_shelves = opts.get("num_shelves", max(1, int(body_h / 300) - 1))
    section_w = inner_w / num_sections
    for i in range(num_shelves):
        shelf_z = kickplate_h + t + (body_h - 2 * t) * (i + 1) / (num_shelves + 1)
        parts.append(_panel(f"shelf_{i+1}", "shelf", section_w - 2, D - 20, t,
                            pos=[t + 1, 0, shelf_z], adjustable=True))

    # Kickplate
    if has_kickplate:
        setback = 50
        parts.append(_panel("kickplate", "kickplate", inner_w, kickplate_h, t, pos=[t, setback, 0]))

    # Doors (optional)
    has_doors = opts.get("has_doors", False)
    if has_doors:
        door_gap = 3
        if W > 600:
            door_w = (W - door_gap) / 2
            parts.append(_panel("door_left", "door", door_w, body_h - door_gap, t, pos=[0, 0, kickplate_h]))
            parts.append(_panel("door_right", "door", door_w, body_h - door_gap, t,
                                pos=[door_w + door_gap, 0, kickplate_h]))
            hardware.append(_hinge_set("door_left", body_h))
            hardware.append(_hinge_set("door_right", body_h))
        else:
            parts.append(_panel("door", "door", W - door_gap, body_h - door_gap, t, pos=[0, 0, kickplate_h]))
            hardware.append(_hinge_set("door", body_h))

    # Hardware
    hardware.append({"type": "confirmat_7x50", "usage": "panel joints", "estimated_qty": _estimate_confirmats(parts)})
    hardware.append({"type": "shelf_pin_5mm", "qty": num_shelves * 4, "usage": "adjustable shelves"})

    # Tall furniture warning
    if H > 1800:
        notes.append("ATENCIÓN: Mueble alto (>180cm). Anclar a pared con escuadra de seguridad.")

    return parts, hardware, notes


# ---------------------------------------------------------------------------
# Builder: desk
# ---------------------------------------------------------------------------

def _build_desk(W, H, D, t, opts, standards, mat):
    parts = []
    hardware = []
    notes = []

    inner_w = W - 2 * t
    leg_clearance = 600  # 60cm for knees

    # Top surface
    parts.append(_panel("top_surface", "top_panel", W, D, t, pos=[0, 0, H - t]))

    # Side panels (legs)
    leg_d = D
    parts.append(_panel("side_left", "side", leg_d, H - t, t, pos=[0, 0, 0]))
    parts.append(_panel("side_right", "side", leg_d, H - t, t, pos=[W - t, 0, 0]))

    # Back rail for rigidity
    rail_h = 100  # 10cm
    parts.append(_panel("rail_back", "rail", inner_w, rail_h, t, pos=[t, D - t, H - t - rail_h]))

    # Bottom rail
    parts.append(_panel("rail_bottom_back", "rail", inner_w, rail_h, t, pos=[t, D - t, 0]))

    # Back panel
    back_t = 3
    parts.append(_panel("back", "back", inner_w, H - t, back_t, pos=[t, D - back_t, 0]))

    # Optional modesty panel (front bottom)
    has_modesty = opts.get("has_modesty_panel", True)
    if has_modesty:
        modesty_h = H - t - leg_clearance
        if modesty_h > 0:
            parts.append(_panel("modesty_panel", "rail", inner_w, modesty_h, t, pos=[t, 0, 0]))

    # Hardware
    hardware.append({"type": "confirmat_7x50", "usage": "panel joints", "estimated_qty": _estimate_confirmats(parts)})

    notes.append(f"Espacio libre para rodillas: {leg_clearance/10}cm de alto.")
    notes.append("Superficie a 75cm del piso (estándar ergonómico).")

    return parts, hardware, notes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _panel(id: str, role: str, width: float, height: float, thickness: float,
           pos: list | None = None, adjustable: bool = False) -> dict:
    """Create a panel spec. Dimensions in mm."""
    p = {
        "id": id,
        "role": role,
        "width_mm": round(width, 1),
        "height_mm": round(height, 1),
        "thickness_mm": round(thickness, 1),
    }
    if pos:
        p["position_mm"] = {"x": round(pos[0], 1), "y": round(pos[1], 1), "z": round(pos[2], 1)}
    if adjustable:
        p["adjustable"] = True
    # Edge banding: visible edges by default
    if role == "door":
        p["edge_banding"] = ["top", "bottom", "left", "right"]
    elif role == "shelf":
        p["edge_banding"] = ["front"]
    elif role in ("side", "panel_vertical"):
        p["edge_banding"] = ["front"]
    return p


def _hinge_set(door_id: str, door_height_mm: float) -> dict:
    """Calculate hinge quantity for a door."""
    h_cm = door_height_mm / 10
    if h_cm <= 60:
        qty = 2
    elif h_cm <= 120:
        qty = 3
    elif h_cm <= 180:
        qty = 4
    else:
        qty = 5
    return {
        "type": "hinge_35mm_soft_close",
        "door": door_id,
        "qty": qty,
        "placement": f"{100}mm from top and bottom edges",
    }


def _estimate_confirmats(parts: list[dict]) -> int:
    """Rough estimate of confirmat screws needed."""
    structural = [p for p in parts if p["role"] in ("side", "bottom", "top_panel", "divider", "rail")]
    # ~4 confirmats per structural joint, ~2 joints per structural part
    return len(structural) * 4
