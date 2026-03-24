"""Compact formatters for knowledge data.

When brief=True, tools return a condensed one-line-per-item format instead of
full JSON dumps.  This reduces context-window consumption by ~60-80%.
"""

from __future__ import annotations


def brief_standards(standards: dict) -> str:
    """Format ergonomic standards as a compact summary."""
    lines = [f"# {standards.get('name', 'Standards')}"]
    for key, val in standards.items():
        if key in ("name", "notes"):
            continue
        if isinstance(val, dict):
            parts = []
            for k, v in val.items():
                if k == "note":
                    continue
                parts.append(f"{k}={v}")
            lines.append(f"- {key}: {', '.join(parts)}")
        else:
            lines.append(f"- {key}: {val}")
    notes = standards.get("notes", [])
    if notes:
        lines.append(f"- notas: {'; '.join(notes)}")
    return "\n".join(lines)


def brief_material(specs: dict) -> str:
    """Format material specs as a compact summary."""
    lines = [
        f"# {specs['name']}",
        f"- espesor: {specs['thickness_mm']}mm",
        f"- tramo_max_sin_soporte: {specs['max_span_no_support_cm']}cm",
        f"- densidad: {specs['density_kg_m3']} kg/m³",
        f"- agarre_tornillo: {specs['screw_holding']}",
        f"- resistencia_humedad: {specs['moisture_resistance']}",
        f"- canto: {'sí' if specs.get('edge_banding') else 'no'}",
    ]
    sheets = specs.get("sheet_sizes_mm", [])
    if sheets:
        sizes = [f"{s['width']}x{s['height']}" for s in sheets]
        lines.append(f"- tableros_mm: {', '.join(sizes)}")
    return "\n".join(lines)


def brief_structural_rules(rules: list[dict]) -> str:
    """Format structural rules as compact lines."""
    lines = ["# Reglas estructurales"]
    for r in rules:
        sev = "❌" if r["severity"] == "error" else "⚠️"
        lines.append(f"{sev} [{r['id']}] {r['rule']} → Fix: {r['fix']}")
    return "\n".join(lines)


def brief_hardware(data: dict) -> str:
    """Format hardware catalog as compact lines."""
    lines = ["# Hardware"]
    for category, info in data.items():
        lines.append(f"\n## {info['name']}")
        for item in info.get("types", []):
            lines.append(f"- {item['id']}: {item['name']}")
        # Key rules only
        if "quantity_rules" in info:
            rules = [f"≤{r['door_height_max_cm']}cm→{r['quantity']}" for r in info["quantity_rules"]]
            lines.append(f"  cantidad: {', '.join(rules)}")
        if "selection_rules" in info:
            for ctx, rec in info["selection_rules"].items():
                lines.append(f"  {ctx}: {rec}")
    return "\n".join(lines)


def brief_hardware_category(data: dict) -> str:
    """Format a single hardware category as compact lines."""
    lines = [f"# {data['name']}"]
    for item in data.get("types", []):
        lines.append(f"- {item['id']}: {item['name']}")
    if "quantity_rules" in data:
        rules = [f"≤{r['door_height_max_cm']}cm→{r['quantity']}" for r in data["quantity_rules"]]
        lines.append(f"  cantidad: {', '.join(rules)}")
    if "selection_rules" in data:
        for ctx, rec in data["selection_rules"].items():
            lines.append(f"  {ctx}: {rec}")
    return "\n".join(lines)


def brief_assembly_specs(data: dict) -> str:
    """Format assembly specs as a compact summary."""
    lines = [f"# {data['name']}"]

    # Methods summary
    for method in data.get("methods", []):
        lines.append(f"- {method['id']}: {method['name']} — {method['when']}")

    # By joint type
    for joint_id, joint in data.get("by_joint_type", {}).items():
        lines.append(f"- {joint_id}: {joint['description']} → {joint['recommended']}, mín. {joint.get('min_confirmats', '?')} confirmats")

    # Process steps (for single-method specs like hinge_mounting)
    if "process" in data:
        lines.append(f"- pasos: {len(data['process'])}")
        for step in data["process"]:
            lines.append(f"  {step}")

    # Quantity rules
    for rule in data.get("quantity_by_door_height", []):
        lines.append(f"- ≤{rule['max_height_cm']}cm → {rule['qty']} bisagras")

    # Adhesive types
    for adhesive in data.get("types", []):
        usage = ", ".join(adhesive.get("usage", [])[:3])
        lines.append(f"- {adhesive['id']}: {adhesive['name']} → {usage}")

    # Pre-drilling rules
    for rule in data.get("rules", []):
        lines.append(f"- {rule['material']}: piloto confirmat {rule['confirmat_pilot_mm']}mm/{rule['confirmat_pilot_depth_mm']}mm prof., tarugo {rule['dowel_pilot_mm']}mm/{rule['dowel_pilot_depth_mm']}mm prof.")

    # Drawer slides
    if "clearance_per_side_mm" in data:
        lines.append(f"- holgura: {data['clearance_per_side_mm']}mm por lado ({data['total_clearance_mm']}mm total)")

    # Common mistakes
    for mistake in data.get("common_mistakes", []):
        lines.append(f"  ⚠️ {mistake}")

    return "\n".join(lines)
