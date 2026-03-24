"""2D Guillotine Cut Optimizer for panel cutting.

Uses a Shelf-based heuristic (Best Height Fit Decreasing) which is
appropriate for table saws that can only make edge-to-edge straight cuts.

Supports grain direction constraints: when a piece has grain="length",
the grain runs along its `width` dimension. The optimizer ensures grain
alignment is preserved across all placements on a sheet.

Pure Python — no external dependencies.
"""

from __future__ import annotations


def optimize_cuts(
    parts: list[dict],
    sheet_width: float = 2440,
    sheet_height: float = 1220,
    blade_kerf: float = 3,
    grain_direction: str = "auto",
) -> dict:
    """Optimize panel cuts on standard sheets.

    Args:
        parts: List of dicts with keys:
            - id (str): Part identifier
            - width (float): Part width in mm (grain runs along this axis if grain="length")
            - height (float): Part height in mm
            - qty (int, default 1): Number of copies
            - can_rotate (bool, default True): Allow 90° rotation
            - grain (str, optional): "length" = grain runs along width,
              "width" = grain runs along height, "none" = no grain constraint.
              Overrides can_rotate when set to "length" or "width".
        sheet_width: Sheet width in mm (grain runs along this axis on the sheet).
        sheet_height: Sheet height in mm.
        blade_kerf: Saw blade width in mm.
        grain_direction: Global default for pieces without explicit grain.
            "auto" = use each piece's grain/can_rotate fields (default).
            "length" = all pieces have grain along their width dimension.
            "none" = ignore grain, allow free rotation.

    Returns:
        Dict with: sheets (list of placements), summary stats, text diagram.
    """
    # Expand parts by quantity and resolve grain/rotation
    pieces: list[dict] = []
    for p in parts:
        qty = p.get("qty", 1)
        grain = p.get("grain", None)

        # Resolve grain: explicit piece grain > global grain_direction > can_rotate
        if grain is None:
            if grain_direction == "auto":
                grain = "none" if p.get("can_rotate", True) else "length"
            else:
                grain = grain_direction

        for i in range(qty):
            piece = {
                "id": f"{p['id']}_{i+1}" if qty > 1 else p["id"],
                "original_id": p["id"],
                "width": p["width"],
                "height": p["height"],
                "grain": grain,
                "placed": False,
                "rotated": False,
            }
            pieces.append(piece)

    # Sort by largest dimension descending (BHFD heuristic)
    pieces.sort(key=lambda p: max(p["width"], p["height"]), reverse=True)

    sheets: list[dict] = []

    for piece in pieces:
        if piece["placed"]:
            continue
        placed = False

        # Try to fit in existing sheets
        for sheet in sheets:
            if _try_place_in_sheet(sheet, piece, sheet_width, sheet_height, blade_kerf):
                placed = True
                break

        # New sheet needed
        if not placed:
            new_sheet = {"id": len(sheets) + 1, "shelves": [], "placements": []}
            if _try_place_in_sheet(new_sheet, piece, sheet_width, sheet_height, blade_kerf):
                sheets.append(new_sheet)
            else:
                return {
                    "error": _build_fit_error(piece, sheet_width, sheet_height)
                }

    # Calculate stats
    total_sheet_area = len(sheets) * sheet_width * sheet_height
    total_used_area = sum(p["width"] * p["height"] for p in pieces)
    waste_pct = round((1 - total_used_area / total_sheet_area) * 100, 1) if total_sheet_area else 0

    # Build text diagram
    diagrams = []
    for sheet in sheets:
        diagrams.append(_text_diagram(sheet, sheet_width, sheet_height))

    result = {
        "sheets_needed": len(sheets),
        "sheet_size_mm": {"width": sheet_width, "height": sheet_height},
        "blade_kerf_mm": blade_kerf,
        "grain_direction": grain_direction,
        "waste_percentage": waste_pct,
        "total_pieces": len(pieces),
        "sheets": [],
        "text_diagrams": diagrams,
    }

    for sheet in sheets:
        sheet_data = {
            "sheet_number": sheet["id"],
            "pieces": [],
        }
        for pl in sheet["placements"]:
            piece_data = {
                "id": pl["id"],
                "x": pl["x"],
                "y": pl["y"],
                "width": pl["width"],
                "height": pl["height"],
                "rotated": pl["rotated"],
            }
            if pl.get("grain_arrow"):
                piece_data["grain_arrow"] = pl["grain_arrow"]
            sheet_data["pieces"].append(piece_data)
        result["sheets"].append(sheet_data)

    return result


# ---------------------------------------------------------------------------
# Actionable error messages
# ---------------------------------------------------------------------------

def _build_fit_error(piece, sheet_width, sheet_height):
    """Build a descriptive error message with suggestions when a piece doesn't fit."""
    pid = piece["id"]
    pw, ph = piece["width"], piece["height"]
    grain = piece["grain"]
    sheet_max = max(sheet_width, sheet_height)
    sheet_min = min(sheet_width, sheet_height)

    header = (
        f"La pieza '{pid}' ({pw}x{ph}mm) no cabe en el tablero "
        f"({sheet_width}x{sheet_height}mm)."
    )
    suggestions: list[str] = []

    # Check if the piece fits rotated (ignoring grain)
    fits_normal = pw <= sheet_width and ph <= sheet_height
    fits_rotated = ph <= sheet_width and pw <= sheet_height

    # 1. If grain is restrictive, suggest changing to 'none'
    if grain in ("length", "width"):
        suggestions.append(
            f"Cambiar grain a 'none' para permitir rotación libre "
            f"(actual: grain='{grain}')."
        )

        # 2. If it fits rotated but grain prevents it
        if fits_rotated and not fits_normal:
            suggestions.append(
                f"La pieza cabe rotada ({ph}x{pw}mm). "
                f"Usa grain='none' o can_rotate=true."
            )
        elif fits_normal and not fits_rotated:
            suggestions.append(
                f"La pieza cabe sin rotar ({pw}x{ph}mm) pero la orientación "
                f"de grano actual lo impide. Revisa la dirección de grain."
            )

    elif grain == "none":
        # Grain is already unrestricted — rotation didn't help either
        pass

    # 3. If the piece exceeds even the largest sheet dimension
    piece_max = max(pw, ph)
    piece_min = min(pw, ph)
    if piece_max > sheet_max or piece_min > sheet_min:
        suggestions.append(
            f"La pieza excede las dimensiones del tablero. Usar un tablero "
            f"más grande (se necesita al menos {piece_min}x{piece_max}mm útiles)."
        )

    # 4. If nothing else works, suggest splitting
    if not fits_normal and not fits_rotated:
        suggestions.append(
            f"Dividir la pieza en partes más pequeñas que quepan en el tablero."
        )

    if not suggestions:
        suggestions.append(
            "Verificar las dimensiones de la pieza y del tablero."
        )

    lines = [header, "Sugerencias:"]
    for s in suggestions:
        lines.append(f"  - {s}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Grain-aware orientation logic
# ---------------------------------------------------------------------------

def _allowed_orientations(piece, sheet_width, sheet_height):
    """Return list of (w, h, rotated, grain_arrow) tuples respecting grain.

    Convention:
    - Sheet grain runs along sheet_width (horizontal = →).
    - piece["grain"] == "length": grain along piece's width dimension.
      → place as-is (width horizontal) = grain matches sheet.
      → rotating 90° would put grain vertical = NOT allowed.
    - piece["grain"] == "width": grain along piece's height dimension.
      → as-is: grain vertical (↑) — only allowed if we accept vertical grain.
      → rotate: grain becomes horizontal (→) — matches sheet grain.
      So for "width" grain: prefer rotated orientation.
    - piece["grain"] == "none": both orientations allowed.
    """
    pw, ph = piece["width"], piece["height"]
    grain = piece["grain"]

    if grain == "none":
        orientations = [(pw, ph, False, "→")]
        if pw != ph:
            orientations.append((ph, pw, True, "→"))
        return orientations

    if grain == "length":
        # Grain along piece width → must keep width along sheet_width (horizontal)
        return [(pw, ph, False, "→")]

    if grain == "width":
        # Grain along piece height → rotate so grain aligns with sheet horizontal
        return [(ph, pw, True, "→")]

    # Fallback: treat as no constraint
    orientations = [(pw, ph, False, "→")]
    if pw != ph:
        orientations.append((ph, pw, True, "→"))
    return orientations


# ---------------------------------------------------------------------------
# Shelf-based placement
# ---------------------------------------------------------------------------

def _try_place_in_sheet(sheet, piece, sheet_w, sheet_h, kerf):
    """Try to place a piece in an existing sheet using shelf algorithm."""
    orientations = _allowed_orientations(piece, sheet_w, sheet_h)

    for w, h, rotated, grain_arrow in orientations:
        # Try existing shelves
        for shelf in sheet["shelves"]:
            if shelf["remaining_width"] >= w and shelf["height"] >= h:
                x = shelf["x_cursor"]
                y = shelf["y"]
                sheet["placements"].append({
                    "id": piece["id"],
                    "x": x, "y": y,
                    "width": w, "height": h,
                    "rotated": rotated,
                    "grain_arrow": grain_arrow,
                })
                shelf["x_cursor"] += w + kerf
                shelf["remaining_width"] -= (w + kerf)
                piece["placed"] = True
                piece["rotated"] = rotated
                return True

        # Create new shelf
        y_cursor = sum(s["height"] + kerf for s in sheet["shelves"])
        if y_cursor + h <= sheet_h and w <= sheet_w:
            new_shelf = {
                "y": y_cursor,
                "height": h,
                "x_cursor": w + kerf,
                "remaining_width": sheet_w - w - kerf,
            }
            sheet["shelves"].append(new_shelf)
            sheet["placements"].append({
                "id": piece["id"],
                "x": 0, "y": y_cursor,
                "width": w, "height": h,
                "rotated": rotated,
                "grain_arrow": grain_arrow,
            })
            piece["placed"] = True
            piece["rotated"] = rotated
            return True

    return False


# ---------------------------------------------------------------------------
# Text diagram
# ---------------------------------------------------------------------------

def _text_diagram(sheet, sheet_w, sheet_h):
    """Generate a simple ASCII diagram of a sheet."""
    scale = 60 / sheet_w  # 60 chars wide
    lines = []
    lines.append(f"┌{'─' * 60}┐  Tablero #{sheet['id']} ({sheet_w}x{sheet_h}mm)")

    # Create a grid
    grid_h = int(sheet_h * scale) + 1
    grid_w = 62

    rows = [list(" " * grid_w) for _ in range(grid_h)]

    for pl in sheet["placements"]:
        x1 = int(pl["x"] * scale) + 1
        y1 = int(pl["y"] * scale)
        x2 = int((pl["x"] + pl["width"]) * scale) + 1
        y2 = int((pl["y"] + pl["height"]) * scale)

        x1 = min(x1, grid_w - 2)
        x2 = min(x2, grid_w - 2)
        y1 = min(y1, grid_h - 1)
        y2 = min(y2, grid_h - 1)

        # Label with grain arrow
        arrow = pl.get("grain_arrow", "")
        label = f"{pl['id'][:10]}{arrow}" if arrow else pl["id"][:12]
        mid_y = (y1 + y2) // 2
        mid_x = (x1 + x2) // 2 - len(label) // 2
        if 0 <= mid_y < grid_h and mid_x >= 0:
            for ci, ch in enumerate(label):
                if mid_x + ci < grid_w:
                    rows[mid_y][mid_x + ci] = ch

    diagram = "\n".join("".join(row) for row in rows)
    lines.append(diagram)
    lines.append(f"└{'─' * 60}┘")

    return "\n".join(lines)
