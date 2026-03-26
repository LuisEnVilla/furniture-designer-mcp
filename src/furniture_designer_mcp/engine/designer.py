"""Furniture spec generator.

Takes user parameters + ergonomic standards + structural rules and produces
a complete JSON spec with all parts, positions, hardware, and notes.
"""

from __future__ import annotations

from ..knowledge.ergonomics import ERGONOMIC_STANDARDS
from ..knowledge.materials import MATERIALS
from ..knowledge.structural_rules import STRUCTURAL_RULES
from .section_mapper import map_sections

# Safety limits for quantities
MAX_SHELVES = 20
MAX_DRAWERS = 10


def _clamp_quantities(opts: dict, notes: list[str]) -> dict:
    """Clamp num_shelves / num_drawers to safe maximums. Mutates opts in-place."""
    ns = opts.get("num_shelves")
    if ns is not None and ns > MAX_SHELVES:
        notes.append(f"⚠ num_shelves={ns} excede límite ({MAX_SHELVES}). Ajustado a {MAX_SHELVES}.")
        opts["num_shelves"] = MAX_SHELVES
    nd = opts.get("num_drawers")
    if nd is not None and nd > MAX_DRAWERS:
        notes.append(f"⚠ num_drawers={nd} excede límite ({MAX_DRAWERS}). Ajustado a {MAX_DRAWERS}.")
        opts["num_drawers"] = MAX_DRAWERS
    # Warn if sections + num_shelves both provided (potential conflict)
    if opts.get("sections") and opts.get("num_shelves") is not None:
        notes.append("⚠ Se proporcionó 'sections' y 'num_shelves' al mismo tiempo. "
                      "'sections' tiene prioridad — 'num_shelves' se ignora para secciones personalizadas.")
    return opts


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
    opts = dict(options) if options else {}
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

    # Clamp quantities to safe limits
    _clamp_quantities(opts, notes)

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

    # --- Store back_type in spec for validator ---
    back_type = opts.get("back_type", "full") if opts else "full"

    spec = {
        "furniture_type": furniture_type,
        "dimensions_cm": {"width": width, "height": height, "depth": depth},
        "dimensions_mm": {"width": W, "height": H, "depth": D},
        "material": material,
        "material_thickness_mm": t,
        "back_type": back_type,
        "parts": parts,
        "hardware": hardware,
        "notes": notes,
        "standards_applied": standards.get("name", furniture_type),
    }

    # Auto-generate section labels for natural language referencing
    spec["section_labels"] = map_sections(spec)

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

    # Vertical dividers (auto-calculated)
    divider_positions = _calc_dividers(inner_w, max_span, t)
    num_sections = len(divider_positions) + 1

    for i, div_x in enumerate(divider_positions):
        parts.append(_panel(f"divider_{i+1}", "divider", D, body_h, t, pos=[div_x, 0, kickplate_h]))

    if divider_positions:
        notes.append(f"{len(divider_positions)} divisor(es) vertical(es) agregado(s): ancho interior ({inner_w/10:.1f}cm) excede tramo libre ({max_span}cm).")

    # Top rails (no full top panel — countertop goes on top)
    rail_h = 80  # 8cm rail
    parts.append(_panel("rail_front", "rail", inner_w, rail_h, t, pos=[t, 0, kickplate_h + body_h - rail_h]))
    parts.append(_panel("rail_back", "rail", inner_w, rail_h, t, pos=[t, D - t, kickplate_h + body_h - rail_h]))

    # Back panel
    back_type = opts.get("back_type", "full")
    if back_type == "full":
        back_t = 3  # 3mm MDF
        parts.append(_panel("back", "back", inner_w, body_h, back_t, pos=[t, D - back_t, kickplate_h]))
    elif back_type == "rails":
        rail_back_h = 80
        parts.append(_panel("rail_back_top", "back_rail", inner_w, rail_back_h, t,
                            pos=[t, D - t, kickplate_h + body_h - rail_back_h]))
        parts.append(_panel("rail_back_bottom", "back_rail", inner_w, rail_back_h, t,
                            pos=[t, D - t, kickplate_h]))
        notes.append("Respaldo tipo rails — ventilación posterior.")
    elif back_type == "none":
        notes.append("Sin respaldo — mueble requiere anclaje a pared.")

    # Shelf
    num_shelves = opts.get("num_shelves", 1)
    section_w = (inner_w - len(divider_positions) * t) / num_sections
    for i in range(num_shelves):
        shelf_z = kickplate_h + body_h * (i + 1) / (num_shelves + 1)
        parts.append(_panel(f"shelf_{i+1}", "shelf", section_w - 2, D - 20, t,
                            pos=[t + 1, 0, shelf_z], adjustable=True))

    # Kickplate base frame (4 pieces: front, back, 2 returns)
    setback = 50  # 5cm setback from front
    return_depth = D - setback - t  # from behind front rail to back rail
    parts.append(_panel("kickplate_front", "kickplate", inner_w, kickplate_h, t, pos=[t, setback, 0]))
    parts.append(_panel("kickplate_back", "kickplate", inner_w, kickplate_h, t, pos=[t, D - t, 0]))
    parts.append(_panel("kickplate_return_l", "kickplate_return", return_depth, kickplate_h, t, pos=[t, setback + t, 0]))
    parts.append(_panel("kickplate_return_r", "kickplate_return", return_depth, kickplate_h, t, pos=[W - 2 * t, setback + t, 0]))

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

    # Drawers
    num_drawers = opts.get("num_drawers", 0)
    if num_drawers > 0:
        drawer_front_h = opts.get("drawer_height", 140)  # mm, visible front
        drawer_box_h = 110  # mm, internal box height
        drawer_gap = 3  # mm between drawers
        drawer_start_z = kickplate_h + t  # Start above bottom panel

        for i in range(num_drawers):
            d_z = drawer_start_z + i * (drawer_front_h + drawer_gap)
            d_parts, d_hw = _build_drawer_box(
                drawer_id=f"drawer_{i+1}",
                section_x=t,
                section_inner_w=section_w,
                drawer_z=d_z,
                depth=D,
                drawer_h=drawer_box_h,
                front_h=drawer_front_h,
                t=t,
            )
            parts.extend(d_parts)
            hardware.extend(d_hw)

        notes.append(f"{num_drawers} cajón(es) con caja completa (laterales + trasera + fondo).")

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

    # Vertical dividers (auto-calculated)
    divider_positions = _calc_dividers(inner_w, max_span, t)
    num_sections = len(divider_positions) + 1

    for i, div_x in enumerate(divider_positions):
        parts.append(_panel(f"divider_{i+1}", "divider", D, body_h, t, pos=[div_x, 0, kickplate_h]))

    if divider_positions:
        notes.append(
            f"{len(divider_positions)} divisor(es) vertical(es) agregado(s): "
            f"ancho interior ({inner_w/10:.1f}cm) excede tramo libre ({max_span}cm)."
        )

    # Back panel
    back_type = opts.get("back_type", "full")
    if back_type == "full":
        back_t = 3
        parts.append(_panel("back", "back", inner_w, body_h, back_t, pos=[t, D - back_t, kickplate_h]))
    elif back_type == "rails":
        rail_back_h = 80
        parts.append(_panel("rail_back_top_struct", "back_rail", inner_w, rail_back_h, t,
                            pos=[t, D - t, kickplate_h + body_h - rail_back_h]))
        parts.append(_panel("rail_back_bottom_struct", "back_rail", inner_w, rail_back_h, t,
                            pos=[t, D - t, kickplate_h]))
        notes.append("Respaldo tipo rails — ventilación posterior.")
    elif back_type == "none":
        notes.append("Sin respaldo — mueble requiere anclaje a pared.")

    # Rails for wide cabinets
    if W > 600:
        rail_h = 80
        parts.append(_panel("rail_back_top", "rail", inner_w, rail_h, t,
                            pos=[t, D - t, kickplate_h + body_h - t - rail_h]))
        notes.append("Travesaño trasero superior agregado por ancho > 60cm.")

    # Section width
    section_w = (inner_w - len(divider_positions) * t) / num_sections

    # --- Reconcile sections config with dividers ---
    sections_cfg = opts.get("sections")
    if sections_cfg:
        # If user requests more sections than auto-calculated, add extra dividers
        requested_sections = len(sections_cfg)
        if requested_sections > num_sections:
            divider_positions = _calc_dividers_for_n(inner_w, requested_sections, t)
            # Remove old dividers and re-add
            parts = [p for p in parts if p["role"] != "divider"]
            for i, div_x in enumerate(divider_positions):
                parts.append(_panel(f"divider_{i+1}", "divider", D, body_h, t, pos=[div_x, 0, kickplate_h]))
            num_sections = requested_sections
            section_w = (inner_w - len(divider_positions) * t) / num_sections
            notes.append(f"{len(divider_positions)} divisor(es) para {num_sections} secciones personalizadas.")

    # --- Section content ---
    if sections_cfg:
        # Custom layout per section
        total_shelf_pins = 0
        for sec_i, sec_cfg in enumerate(sections_cfg):
            sec_x = _section_start_x(sec_i, section_w, divider_positions, t)
            s_parts, s_hw, s_notes = _build_section_content(
                section_index=sec_i,
                section_config=sec_cfg,
                section_x=sec_x,
                section_w=section_w,
                body_h=body_h,
                kickplate_h=kickplate_h,
                D=D,
                t=t,
            )
            parts.extend(s_parts)
            hardware.extend(s_hw)
            notes.extend(s_notes)
            # Count adjustable shelves for pins
            total_shelf_pins += sum(4 for p in s_parts if p.get("adjustable"))
        hardware.append({"type": "confirmat_7x50", "usage": "panel joints", "estimated_qty": _estimate_confirmats(parts)})
        if total_shelf_pins > 0:
            hardware.append({"type": "shelf_pin_5mm", "qty": total_shelf_pins, "usage": "adjustable shelves"})
    else:
        # Default uniform layout (backwards compatible)
        num_shelves = opts.get("num_shelves", max(1, int(body_h / 300) - 1))
        for i in range(num_shelves):
            shelf_z = kickplate_h + t + (body_h - 2 * t) * (i + 1) / (num_shelves + 1)
            parts.append(_panel(f"shelf_{i+1}", "shelf", section_w - 2, D - 20, t,
                                pos=[t + 1, 0, shelf_z], adjustable=True))

        # Drawers (global)
        num_drawers = opts.get("num_drawers", 0)
        if num_drawers > 0:
            drawer_front_h = opts.get("drawer_height", 140)
            drawer_box_h = 110
            drawer_gap = 3
            drawer_start_z = kickplate_h + t

            for i in range(num_drawers):
                d_z = drawer_start_z + i * (drawer_front_h + drawer_gap)
                d_parts, d_hw = _build_drawer_box(
                    drawer_id=f"drawer_{i+1}",
                    section_x=t,
                    section_inner_w=section_w,
                    drawer_z=d_z,
                    depth=D,
                    drawer_h=drawer_box_h,
                    front_h=drawer_front_h,
                    t=t,
                )
                parts.extend(d_parts)
                hardware.extend(d_hw)
            notes.append(f"{num_drawers} cajón(es) con caja completa (laterales + trasera + fondo).")

        hardware.append({"type": "confirmat_7x50", "usage": "panel joints", "estimated_qty": _estimate_confirmats(parts)})
        hardware.append({"type": "shelf_pin_5mm", "qty": num_shelves * 4, "usage": "adjustable shelves"})

    # Kickplate base frame (4 pieces: front, back, 2 returns)
    if has_kickplate:
        setback = 50  # 5cm setback from front
        return_depth = D - setback - t  # from behind front rail to back rail
        parts.append(_panel("kickplate_front", "kickplate", inner_w, kickplate_h, t, pos=[t, setback, 0]))
        parts.append(_panel("kickplate_back", "kickplate", inner_w, kickplate_h, t, pos=[t, D - t, 0]))
        parts.append(_panel("kickplate_return_l", "kickplate_return", return_depth, kickplate_h, t, pos=[t, setback + t, 0]))
        parts.append(_panel("kickplate_return_r", "kickplate_return", return_depth, kickplate_h, t, pos=[W - 2 * t, setback + t, 0]))

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

def _calc_dividers(total_inner_w: float, max_span_cm: float, t: float) -> list[float]:
    """Calcula posiciones X de divisores necesarios para respetar max_span.

    Args:
        total_inner_w: Ancho interior libre en mm (entre laterales).
        max_span_cm: Tramo libre máximo del material en cm.
        t: Espesor del material en mm.

    Returns:
        Lista de posiciones X (en mm, desde borde izquierdo del mueble)
        donde colocar cada divisor.
    """
    import math
    max_span_mm = max_span_cm * 10
    num_sections = math.ceil(total_inner_w / max_span_mm)
    if num_sections <= 1:
        return []

    num_dividers = num_sections - 1
    net_w = total_inner_w - num_dividers * t
    section_w = net_w / num_sections

    positions = []
    for i in range(1, num_sections):
        pos_x = t + i * section_w + (i - 1) * t
        positions.append(pos_x)

    return positions


def _calc_dividers_for_n(total_inner_w: float, num_sections: int, t: float) -> list[float]:
    """Calcula posiciones de divisores para exactamente N secciones.

    Similar a _calc_dividers pero fuerza un número específico de secciones
    en vez de calcularlo desde max_span.
    """
    if num_sections <= 1:
        return []

    num_dividers = num_sections - 1
    net_w = total_inner_w - num_dividers * t
    section_w = net_w / num_sections

    positions = []
    for i in range(1, num_sections):
        pos_x = t + i * section_w + (i - 1) * t
        positions.append(pos_x)

    return positions


def _section_start_x(section_index: int, section_w: float, divider_positions: list[float], t: float) -> float:
    """Calcula la posición X de inicio de una sección.

    Sección 0 empieza en x=t (después del lateral izquierdo).
    Secciones siguientes empiezan después del divisor correspondiente + su espesor.
    """
    if section_index == 0:
        return t
    return divider_positions[section_index - 1] + t


def _hanging_bar(
    section_id: str,
    section_x: float,
    section_w: float,
    D: float,
    height_z: float,
    t: float,
) -> tuple[list[dict], list[dict]]:
    """Genera soporte y hardware para barra de colgar.

    Returns (parts, hardware).
    """
    # Two small support rails (left and right brackets)
    bracket_h = 30  # 3cm bracket
    parts = [
        _panel(f"{section_id}_bar_support_l", "rail", bracket_h, bracket_h, t,
               pos=[section_x, 0, height_z]),
        _panel(f"{section_id}_bar_support_r", "rail", bracket_h, bracket_h, t,
               pos=[section_x + section_w - bracket_h, 0, height_z]),
    ]
    hardware = [
        {
            "type": "hanging_bar_chrome",
            "section": section_id,
            "qty": 1,
            "length_mm": round(section_w, 1),
            "description": f"Tubo cromado Ø25mm, {round(section_w/10, 1)}cm",
            "position_z_mm": round(height_z, 1),
        },
    ]
    return parts, hardware


def _build_section_content(
    section_index: int,
    section_config: dict,
    section_x: float,
    section_w: float,
    body_h: float,
    kickplate_h: float,
    D: float,
    t: float,
) -> tuple[list[dict], list[dict], list[str]]:
    """Genera partes, hardware y notas para una sección individual.

    Args:
        section_index: Índice de la sección (0-based).
        section_config: Dict con "content" y parámetros opcionales.
        section_x: Posición X de inicio de la sección (mm).
        section_w: Ancho interior de la sección (mm).
        body_h: Altura del cuerpo del mueble (mm).
        kickplate_h: Altura del zócalo (mm).
        D: Profundidad total (mm).
        t: Espesor del material (mm).
    """
    parts = []
    hardware = []
    notes = []

    sid = f"S{section_index + 1}"
    content = section_config.get("content", "shelves")
    base_z = kickplate_h + t  # above bottom panel
    usable_h = body_h - 2 * t  # between bottom and top panels

    if content == "shelves":
        num_shelves = section_config.get("num_shelves", max(1, int(usable_h / 300) - 1))
        for i in range(num_shelves):
            shelf_z = base_z + usable_h * (i + 1) / (num_shelves + 1)
            parts.append(_panel(
                f"shelf_{sid}_{i+1}", "shelf", section_w - 2, D - 20, t,
                pos=[section_x + 1, 0, shelf_z], adjustable=True,
            ))
        notes.append(f"Sección {sid}: {num_shelves} repisa(s).")

    elif content == "drawers":
        num_drawers = section_config.get("num_drawers", 3)
        drawer_front_h = section_config.get("drawer_height", 140)
        drawer_box_h = 110
        drawer_gap = 3
        for i in range(num_drawers):
            d_z = base_z + i * (drawer_front_h + drawer_gap)
            d_parts, d_hw = _build_drawer_box(
                drawer_id=f"drawer_{sid}_{i+1}",
                section_x=section_x,
                section_inner_w=section_w,
                drawer_z=d_z,
                depth=D,
                drawer_h=drawer_box_h,
                front_h=drawer_front_h,
                t=t,
            )
            parts.extend(d_parts)
            hardware.extend(d_hw)
        notes.append(f"Sección {sid}: {num_drawers} cajón(es).")

    elif content == "hanging":
        bar_h_cm = section_config.get("hanging_bar_height_cm", 160)
        bar_z = kickplate_h + bar_h_cm * 10
        bar_parts, bar_hw = _hanging_bar(sid, section_x, section_w, D, bar_z, t)
        parts.extend(bar_parts)
        hardware.extend(bar_hw)
        notes.append(f"Sección {sid}: barra de colgar a {bar_h_cm}cm.")

    elif content == "drawers+hanging":
        # Drawers at bottom, hanging bar above
        num_drawers = section_config.get("num_drawers", 3)
        drawer_front_h = section_config.get("drawer_height", 140)
        drawer_box_h = 110
        drawer_gap = 3
        for i in range(num_drawers):
            d_z = base_z + i * (drawer_front_h + drawer_gap)
            d_parts, d_hw = _build_drawer_box(
                drawer_id=f"drawer_{sid}_{i+1}",
                section_x=section_x,
                section_inner_w=section_w,
                drawer_z=d_z,
                depth=D,
                drawer_h=drawer_box_h,
                front_h=drawer_front_h,
                t=t,
            )
            parts.extend(d_parts)
            hardware.extend(d_hw)

        # Separator shelf above drawers
        drawers_top_z = base_z + num_drawers * (drawer_front_h + drawer_gap)
        parts.append(_panel(
            f"shelf_{sid}_sep", "shelf", section_w - 2, D - 20, t,
            pos=[section_x + 1, 0, drawers_top_z],
        ))

        # Hanging bar above separator
        bar_h_cm = section_config.get("hanging_bar_height_cm", 160)
        bar_z = kickplate_h + bar_h_cm * 10
        if bar_z <= drawers_top_z + t:
            bar_z = drawers_top_z + t + 50  # at least 5cm above separator
        bar_parts, bar_hw = _hanging_bar(sid, section_x, section_w, D, bar_z, t)
        parts.extend(bar_parts)
        hardware.extend(bar_hw)
        notes.append(f"Sección {sid}: {num_drawers} cajón(es) + barra de colgar.")

    elif content == "drawers+shelves":
        # Drawers at bottom, shelves above
        num_drawers = section_config.get("num_drawers", 3)
        drawer_front_h = section_config.get("drawer_height", 140)
        drawer_box_h = 110
        drawer_gap = 3
        for i in range(num_drawers):
            d_z = base_z + i * (drawer_front_h + drawer_gap)
            d_parts, d_hw = _build_drawer_box(
                drawer_id=f"drawer_{sid}_{i+1}",
                section_x=section_x,
                section_inner_w=section_w,
                drawer_z=d_z,
                depth=D,
                drawer_h=drawer_box_h,
                front_h=drawer_front_h,
                t=t,
            )
            parts.extend(d_parts)
            hardware.extend(d_hw)

        # Separator shelf above drawers
        drawers_top_z = base_z + num_drawers * (drawer_front_h + drawer_gap)
        parts.append(_panel(
            f"shelf_{sid}_sep", "shelf", section_w - 2, D - 20, t,
            pos=[section_x + 1, 0, drawers_top_z],
        ))

        # Shelves above separator
        remaining_h = (kickplate_h + body_h - t) - (drawers_top_z + t)
        num_shelves = section_config.get("num_shelves", max(1, int(remaining_h / 300) - 1))
        for i in range(num_shelves):
            shelf_z = drawers_top_z + t + remaining_h * (i + 1) / (num_shelves + 1)
            parts.append(_panel(
                f"shelf_{sid}_{i+1}", "shelf", section_w - 2, D - 20, t,
                pos=[section_x + 1, 0, shelf_z], adjustable=True,
            ))
        notes.append(f"Sección {sid}: {num_drawers} cajón(es) + {num_shelves} repisa(s).")

    elif content == "empty":
        notes.append(f"Sección {sid}: vacía.")

    return parts, hardware, notes


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
    elif role == "drawer_front":
        p["edge_banding"] = ["top", "bottom", "left", "right"]
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


def _build_drawer_box(
    drawer_id: str,
    section_x: float,
    section_inner_w: float,
    drawer_z: float,
    depth: float,
    drawer_h: float = 110,
    front_h: float = 140,
    t: float = 16,
    slide_clearance: float = 13,
    bottom_t: float = 3,
) -> tuple[list[dict], list[dict]]:
    """Generate all 5 parts + hardware for one drawer box.

    Returns (parts, hardware).
    """
    box_outer_w = section_inner_w - 2 * slide_clearance
    box_inner_w = box_outer_w - 2 * t
    box_depth = depth - t - 20  # depth minus front thickness minus back clearance

    parts = [
        # Visible front panel (full section width)
        _panel(f"{drawer_id}_front", "drawer_front", section_inner_w, front_h, t,
               pos=[section_x, 0, drawer_z]),
        # Left side
        _panel(f"{drawer_id}_side_l", "drawer_side", box_depth, drawer_h, t,
               pos=[section_x + slide_clearance, t, drawer_z + bottom_t]),
        # Right side
        _panel(f"{drawer_id}_side_r", "drawer_side", box_depth, drawer_h, t,
               pos=[section_x + slide_clearance + t + box_inner_w, t, drawer_z + bottom_t]),
        # Back
        _panel(f"{drawer_id}_back", "drawer_back", box_inner_w, drawer_h, t,
               pos=[section_x + slide_clearance + t, box_depth, drawer_z + bottom_t]),
        # Bottom (thin panel)
        _panel(f"{drawer_id}_bottom", "drawer_bottom", box_outer_w, box_depth, bottom_t,
               pos=[section_x + slide_clearance, t, drawer_z]),
    ]

    hardware = [
        {
            "type": "telescopic_slide",
            "drawer": drawer_id,
            "qty": 1,
            "description": "Par de correderas telescópicas",
        },
    ]

    return parts, hardware
