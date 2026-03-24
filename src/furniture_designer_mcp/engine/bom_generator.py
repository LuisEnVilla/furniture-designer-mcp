"""Bill of Materials (BOM) generator for furniture specs."""

from __future__ import annotations


def generate_bom(spec: dict) -> dict:
    """Generate a Bill of Materials from a furniture spec.

    Returns:
        Dict with: panels (cut list), hardware, edge_banding, summary.
    """
    parts = spec.get("parts", [])
    hardware_list = spec.get("hardware", [])
    material = spec.get("material", "melamine_16")
    t = spec.get("material_thickness_mm", 16)

    # --- Panels ---
    panels = []
    back_panels = []

    for p in parts:
        entry = {
            "id": p["id"],
            "role": p["role"],
            "width_mm": p["width_mm"],
            "height_mm": p["height_mm"],
            "thickness_mm": p["thickness_mm"],
            "material": "mdf_3" if p["role"] in ("back", "drawer_bottom") else material,
            "edge_banding": p.get("edge_banding", []),
            "qty": 1,
        }
        if p["role"] in ("back", "drawer_bottom"):
            back_panels.append(entry)
        else:
            panels.append(entry)

    # Group identical panels
    grouped_panels = _group_identical(panels)
    grouped_backs = _group_identical(back_panels)

    # --- Edge banding ---
    total_edge_m = 0
    edge_details = []
    for p in panels:
        edges = p.get("edge_banding", [])
        for edge in edges:
            if edge in ("top", "bottom", "front", "back_edge"):
                length = p["width_mm"]
            else:  # left, right
                length = p["height_mm"]
            total_edge_m += length / 1000
            edge_details.append({
                "panel": p["id"],
                "edge": edge,
                "length_mm": length,
            })

    # --- Summary ---
    total_panels = sum(g["qty"] for g in grouped_panels)
    total_back_panels = sum(g["qty"] for g in grouped_backs)

    summary = {
        "total_structural_panels": total_panels,
        "total_back_panels": total_back_panels,
        "total_pieces": total_panels + total_back_panels,
        "structural_material": material,
        "structural_thickness_mm": t,
        "edge_banding_total_meters": round(total_edge_m, 2),
        "hardware_items": len(hardware_list),
    }

    return {
        "panels": grouped_panels,
        "back_panels": grouped_backs,
        "hardware": hardware_list,
        "edge_banding": {
            "total_meters": round(total_edge_m, 2),
            "details": edge_details,
        },
        "summary": summary,
    }


def _group_identical(panels: list[dict]) -> list[dict]:
    """Group panels with identical dimensions."""
    groups: dict[str, dict] = {}
    for p in panels:
        key = f"{p['width_mm']}x{p['height_mm']}x{p['thickness_mm']}"
        if key in groups:
            groups[key]["qty"] += 1
            groups[key]["ids"].append(p["id"])
        else:
            groups[key] = {
                **p,
                "qty": 1,
                "ids": [p["id"]],
            }
    return list(groups.values())
