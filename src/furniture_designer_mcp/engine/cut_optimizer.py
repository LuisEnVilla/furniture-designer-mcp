"""2D Guillotine Cut Optimizer for panel cutting.

Uses a Shelf-based heuristic (Best Height Fit Decreasing) which is
appropriate for table saws that can only make edge-to-edge straight cuts.

Pure Python — no external dependencies.
"""

from __future__ import annotations


def optimize_cuts(
    parts: list[dict],
    sheet_width: float = 2440,
    sheet_height: float = 1220,
    blade_kerf: float = 3,
) -> dict:
    """Optimize panel cuts on standard sheets.

    Args:
        parts: List of dicts with keys: id, width, height, qty (default 1),
            can_rotate (default True). Dimensions in mm.
        sheet_width: Sheet width in mm.
        sheet_height: Sheet height in mm.
        blade_kerf: Saw blade width in mm.

    Returns:
        Dict with: sheets (list of placements), summary stats, text diagram.
    """
    # Expand parts by quantity
    pieces: list[dict] = []
    for p in parts:
        qty = p.get("qty", 1)
        for i in range(qty):
            piece = {
                "id": f"{p['id']}_{i+1}" if qty > 1 else p["id"],
                "original_id": p["id"],
                "width": p["width"],
                "height": p["height"],
                "can_rotate": p.get("can_rotate", True),
                "placed": False,
                "rotated": False,
            }
            pieces.append(piece)

    # Sort by height descending (BFHD heuristic)
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
                # Piece doesn't fit even in a fresh sheet
                return {
                    "error": f"Piece '{piece['id']}' ({piece['width']}x{piece['height']}mm) "
                             f"doesn't fit in sheet ({sheet_width}x{sheet_height}mm)."
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
            sheet_data["pieces"].append({
                "id": pl["id"],
                "x": pl["x"],
                "y": pl["y"],
                "width": pl["width"],
                "height": pl["height"],
                "rotated": pl["rotated"],
            })
        result["sheets"].append(sheet_data)

    return result


# ---------------------------------------------------------------------------
# Shelf-based placement
# ---------------------------------------------------------------------------

def _try_place_in_sheet(sheet, piece, sheet_w, sheet_h, kerf):
    """Try to place a piece in an existing sheet using shelf algorithm."""
    pw, ph = piece["width"], piece["height"]

    orientations = [(pw, ph, False)]
    if piece["can_rotate"] and pw != ph:
        orientations.append((ph, pw, True))

    for w, h, rotated in orientations:
        # Try existing shelves
        for shelf in sheet["shelves"]:
            if shelf["remaining_width"] >= w and shelf["height"] >= h:
                # Fits in this shelf
                x = shelf["x_cursor"]
                y = shelf["y"]
                sheet["placements"].append({
                    "id": piece["id"],
                    "x": x, "y": y,
                    "width": w, "height": h,
                    "rotated": rotated,
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

        # Label
        label = pl["id"][:12]
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
