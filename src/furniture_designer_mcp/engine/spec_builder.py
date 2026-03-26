"""High-level spec builder.

Converts a user-friendly layout description into a complete furniture spec
with all positions, clearances, and hardware calculated automatically.

This is a convenience layer on top of designer.py that eliminates the need
to manually calculate mm positions, slide clearances, kickplate offsets, etc.
"""

from __future__ import annotations

import math

from ..knowledge.materials import MATERIALS
from .designer import (
    _panel,
    _build_drawer_box,
    _estimate_confirmats,
    _hanging_bar,
    _hinge_set,
)


def build_spec_from_layout(layout: dict) -> dict:
    """Generate a complete furniture spec from a high-level layout description.

    Args:
        layout: {
            "furniture_type": "closet",
            "width_cm": 240,
            "height_cm": 240,
            "depth_cm": 60,
            "material": "melamine_16",       # optional, default melamine_16
            "kickplate_height_cm": 10,       # optional, default 10
            "back_type": "full",             # "full", "rails", "none"
            "columns": [
                {
                    "width_cm": 80,          # or "auto" to distribute remaining
                    "rows": [
                        {"type": "hanging_bar", "height_cm": 160},
                        {"type": "shelf"},
                        {"type": "drawers", "count": 3, "drawer_height_mm": 140},
                        {"type": "shelves", "count": 4},
                        {"type": "empty", "height_cm": 30},
                    ]
                },
                ...
            ]
        }

    Returns:
        Complete furniture spec compatible with validate_structure,
        generate_bom, optimize_cuts, build_3d_model, etc.
    """
    # --- Parse layout ---
    furniture_type = layout.get("furniture_type", "closet")
    W_cm = layout["width_cm"]
    H_cm = layout["height_cm"]
    D_cm = layout["depth_cm"]
    material_key = layout.get("material", "melamine_16")

    mat = MATERIALS.get(material_key)
    if mat is None:
        raise ValueError(f"Unknown material: {material_key}")

    t = mat["thickness_mm"]
    W = W_cm * 10
    H = H_cm * 10
    D = D_cm * 10

    kickplate_h_cm = layout.get("kickplate_height_cm", 10)
    kickplate_h = kickplate_h_cm * 10
    back_type = layout.get("back_type", "full")

    body_h = H - kickplate_h
    inner_w = W - 2 * t

    columns = layout.get("columns", [])
    if not columns:
        raise ValueError("Layout must have at least one column.")

    parts: list[dict] = []
    hardware: list[dict] = []
    notes: list[str] = []

    # --- Resolve column widths ---
    max_span_cm = mat.get("max_span_no_support_cm", 75)
    column_widths_mm = _resolve_column_widths(columns, inner_w, t, max_span_cm)
    num_columns = len(columns)

    # --- Structural shell ---
    # Sides
    parts.append(_panel("side_left", "side", D, body_h, t, pos=[0, 0, kickplate_h]))
    parts.append(_panel("side_right", "side", D, body_h, t, pos=[W - t, 0, kickplate_h]))

    # Top and bottom
    parts.append(_panel("top", "top_panel", inner_w, D, t, pos=[t, 0, kickplate_h + body_h - t]))
    parts.append(_panel("bottom", "bottom", inner_w, D, t, pos=[t, 0, kickplate_h]))

    # Dividers between columns
    divider_positions = []
    cursor_x = t
    for col_i in range(num_columns - 1):
        cursor_x += column_widths_mm[col_i]
        divider_positions.append(cursor_x)
        parts.append(_panel(
            f"divider_{col_i + 1}", "divider", D, body_h, t,
            pos=[cursor_x, 0, kickplate_h],
        ))
        cursor_x += t  # divider thickness

    if divider_positions:
        notes.append(f"{len(divider_positions)} divisor(es) para {num_columns} columnas.")

    # Back panel
    if back_type == "full":
        back_t = 3
        parts.append(_panel("back", "back", inner_w, body_h, back_t, pos=[t, D - back_t, kickplate_h]))
    elif back_type == "rails":
        rail_h = 80
        parts.append(_panel("rail_back_top_struct", "back_rail", inner_w, rail_h, t,
                            pos=[t, D - t, kickplate_h + body_h - rail_h]))
        parts.append(_panel("rail_back_bottom_struct", "back_rail", inner_w, rail_h, t,
                            pos=[t, D - t, kickplate_h]))
        notes.append("Respaldo tipo rails — ventilación posterior.")
    elif back_type == "none":
        notes.append("Sin respaldo — mueble requiere anclaje a pared.")

    # Rails for wide cabinets
    if W > 600:
        rail_h = 80
        parts.append(_panel("rail_back_top", "rail", inner_w, rail_h, t,
                            pos=[t, D - t, kickplate_h + body_h - t - rail_h]))

    # Kickplate base frame (4 pieces: front, back, 2 returns)
    if kickplate_h > 0:
        setback = 50
        return_depth = D - setback - t
        parts.append(_panel("kickplate_front", "kickplate", inner_w, kickplate_h, t, pos=[t, setback, 0]))
        parts.append(_panel("kickplate_back", "kickplate", inner_w, kickplate_h, t, pos=[t, D - t, 0]))
        parts.append(_panel("kickplate_return_l", "kickplate_return", return_depth, kickplate_h, t, pos=[t, setback + t, 0]))
        parts.append(_panel("kickplate_return_r", "kickplate_return", return_depth, kickplate_h, t, pos=[W - 2 * t, setback + t, 0]))

    # --- Column content ---
    total_shelf_pins = 0
    col_x = t  # start after left side

    for col_i, col_cfg in enumerate(columns):
        col_w = column_widths_mm[col_i]
        rows = col_cfg.get("rows", [])
        cid = f"C{col_i + 1}"

        if not rows:
            # Default: shelves filling the column
            rows = [{"type": "shelves", "count": max(1, int((body_h - 2 * t) / 300) - 1)}]

        c_parts, c_hw, c_notes, c_pins = _build_column_rows(
            cid, rows, col_x, col_w, body_h, kickplate_h, D, t,
        )
        parts.extend(c_parts)
        hardware.extend(c_hw)
        notes.extend(c_notes)
        total_shelf_pins += c_pins

        col_x += col_w + t  # next column starts after divider

    # --- Hardware ---
    hardware.append({"type": "confirmat_7x50", "usage": "panel joints",
                     "estimated_qty": _estimate_confirmats(parts)})
    if total_shelf_pins > 0:
        hardware.append({"type": "shelf_pin_5mm", "qty": total_shelf_pins,
                         "usage": "adjustable shelves"})

    # Tall furniture warning
    if H > 1800:
        hardware.append({"type": "wall_anchor", "qty": 2,
                         "usage": "anti-tip anchoring"})
        notes.append("ATENCIÓN: Mueble alto (>180cm). Anclar a pared con escuadra de seguridad.")

    spec = {
        "furniture_type": furniture_type,
        "dimensions_cm": {"width": W_cm, "height": H_cm, "depth": D_cm},
        "dimensions_mm": {"width": W, "height": H, "depth": D},
        "material": material_key,
        "material_thickness_mm": t,
        "back_type": back_type,
        "parts": parts,
        "hardware": hardware,
        "notes": notes,
        "standards_applied": furniture_type,
    }
    return spec


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_column_widths(columns: list[dict], inner_w: float, t: float,
                           max_span_cm: float = 75) -> list[float]:
    """Resolve column widths, distributing 'auto' columns evenly.

    Ensures no column exceeds max_span by splitting auto columns if needed.
    """
    max_span_mm = max_span_cm * 10
    num_cols = len(columns)
    num_dividers = num_cols - 1
    available_w = inner_w - num_dividers * t

    fixed_total = 0.0
    auto_count = 0

    for col in columns:
        w = col.get("width_cm")
        if w is None or w == "auto":
            auto_count += 1
        else:
            fixed_total += w * 10

    if auto_count > 0:
        auto_w = (available_w - fixed_total) / auto_count
        if auto_w < 200:  # less than 20cm
            raise ValueError(
                f"Not enough space for auto columns: {auto_w/10:.1f}cm each. "
                f"Reduce fixed column widths or total width."
            )
        # Cap auto columns to max_span (shelf width = col_w - 2, must be <= max_span)
        if auto_w > max_span_mm:
            auto_w = max_span_mm
    else:
        auto_w = 0

    widths = []
    for col in columns:
        w = col.get("width_cm")
        if w is None or w == "auto":
            widths.append(auto_w)
        else:
            widths.append(w * 10)

    return widths


def _build_column_rows(
    cid: str,
    rows: list[dict],
    col_x: float,
    col_w: float,
    body_h: float,
    kickplate_h: float,
    D: float,
    t: float,
) -> tuple[list[dict], list[dict], list[str], int]:
    """Build content for a column from its row definitions.

    Returns (parts, hardware, notes, shelf_pin_count).
    """
    parts = []
    hardware = []
    notes = []
    shelf_pins = 0

    base_z = kickplate_h + t  # above bottom panel
    top_z = kickplate_h + body_h - t  # below top panel
    usable_h = top_z - base_z

    # Calculate row heights
    row_heights = _resolve_row_heights(rows, usable_h, t)

    cursor_z = base_z
    for row_i, (row_cfg, row_h) in enumerate(zip(rows, row_heights)):
        rid = f"{cid}_R{row_i + 1}"
        rtype = row_cfg.get("type", "empty")

        if rtype == "shelf":
            # Single shelf at this position
            parts.append(_panel(
                f"shelf_{rid}", "shelf", col_w - 2, D - 20, t,
                pos=[col_x + 1, 0, cursor_z + row_h / 2], adjustable=True,
            ))
            shelf_pins += 4

        elif rtype == "shelves":
            count = row_cfg.get("count", max(1, int(row_h / 300) - 1))
            for i in range(count):
                sz = cursor_z + row_h * (i + 1) / (count + 1)
                parts.append(_panel(
                    f"shelf_{rid}_{i+1}", "shelf", col_w - 2, D - 20, t,
                    pos=[col_x + 1, 0, sz], adjustable=True,
                ))
                shelf_pins += 4
            notes.append(f"{cid}: {count} repisa(s).")

        elif rtype == "drawers":
            count = row_cfg.get("count", 3)
            front_h = row_cfg.get("drawer_height_mm", 140)
            box_h = 110
            gap = 3
            for i in range(count):
                d_z = cursor_z + i * (front_h + gap)
                d_parts, d_hw = _build_drawer_box(
                    drawer_id=f"drawer_{rid}_{i+1}",
                    section_x=col_x,
                    section_inner_w=col_w,
                    drawer_z=d_z,
                    depth=D,
                    drawer_h=box_h,
                    front_h=front_h,
                    t=t,
                )
                parts.extend(d_parts)
                hardware.extend(d_hw)
            notes.append(f"{cid}: {count} cajón(es).")

        elif rtype == "hanging_bar":
            bar_h_cm = row_cfg.get("height_cm", 160)
            bar_z = kickplate_h + bar_h_cm * 10
            # Clamp to within this row
            if bar_z < cursor_z:
                bar_z = cursor_z + 50
            if bar_z > cursor_z + row_h:
                bar_z = cursor_z + row_h - 50
            bar_parts, bar_hw = _hanging_bar(rid, col_x, col_w, D, bar_z, t)
            parts.extend(bar_parts)
            hardware.extend(bar_hw)
            notes.append(f"{cid}: barra de colgar a {bar_z/10:.0f}cm.")

        elif rtype == "empty":
            pass  # intentionally empty

        # Add separator shelf between rows (except after last row)
        if row_i < len(rows) - 1:
            sep_z = cursor_z + row_h
            parts.append(_panel(
                f"shelf_{rid}_sep", "shelf", col_w - 2, D - 20, t,
                pos=[col_x + 1, 0, sep_z],
            ))

        cursor_z += row_h + (t if row_i < len(rows) - 1 else 0)

    return parts, hardware, notes, shelf_pins


def _resolve_row_heights(rows: list[dict], usable_h: float, t: float) -> list[float]:
    """Resolve row heights within a column.

    Rows with explicit height_cm get their space first.
    Rows with type-based defaults get calculated heights.
    Remaining space is distributed to 'auto' rows.
    """
    num_separators = max(0, len(rows) - 1)
    available = usable_h - num_separators * t

    heights = []
    auto_indices = []

    for i, row in enumerate(rows):
        h_cm = row.get("height_cm")
        if h_cm is not None:
            heights.append(h_cm * 10)
        elif row.get("type") == "drawers":
            count = row.get("count", 3)
            front_h = row.get("drawer_height_mm", 140)
            gap = 3
            drawer_block = count * (front_h + gap) - gap
            heights.append(drawer_block)
        else:
            heights.append(None)
            auto_indices.append(i)

    fixed_total = sum(h for h in heights if h is not None)
    remaining = available - fixed_total

    if auto_indices:
        auto_h = remaining / len(auto_indices)
        for idx in auto_indices:
            heights[idx] = max(auto_h, 100)  # minimum 10cm
    elif remaining < -1:  # allow 1mm tolerance
        raise ValueError(
            f"Row heights exceed available space: "
            f"{fixed_total/10:.1f}cm specified but only {available/10:.1f}cm available."
        )

    return heights
