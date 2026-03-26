"""Structural validator for furniture specs.

Checks a furniture spec against the structural rules defined in
knowledge/structural_rules.py.
"""

from __future__ import annotations

from ..knowledge.materials import MATERIALS
from ..knowledge.structural_rules import STRUCTURAL_RULES


def validate_structure(spec: dict) -> dict:
    """Validate a furniture spec against structural rules.

    Returns:
        Dict with: status ("pass"/"fail"), errors (list), warnings (list).
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    parts = spec.get("parts", [])
    material_key = spec.get("material", "melamine_16")
    mat = MATERIALS.get(material_key, {})
    dims = spec.get("dimensions_cm", {})
    width_cm = dims.get("width", 0)
    height_cm = dims.get("height", 0)
    t_mm = spec.get("material_thickness_mm", 16)

    roles = {p["role"] for p in parts}
    max_span = mat.get("max_span_no_support_cm", 80)

    # Rule: back_panel_required (respects back_type option)
    back_type = spec.get("back_type", "full")

    if "back" not in roles and back_type == "full":
        errors.append({
            "rule": "back_panel_required",
            "message": "Falta el respaldo (back panel). El mueble se va a rackear.",
            "fix": "Agregar panel trasero de MDF 3mm mínimo.",
        })
    elif "back" not in roles and back_type == "rails":
        back_rails = [p for p in parts if p["role"] == "back_rail"]
        if not back_rails:
            errors.append({
                "rule": "back_panel_required",
                "message": "back_type='rails' pero no se encontraron rails traseros.",
                "fix": "Agregar rails traseros (superior e inferior).",
            })
        else:
            warnings.append({
                "rule": "back_panel_ventilation",
                "message": "Respaldo tipo rails. Menor rigidez lateral.",
                "fix": "Asegurar anclaje a pared si el mueble es alto.",
            })
    elif "back" not in roles and back_type == "none":
        warnings.append({
            "rule": "back_panel_none",
            "message": "Sin respaldo. DEBE estar anclado a pared.",
            "fix": "Instalar escuadras de anclaje a pared.",
        })

    # Rule: max_span_check — check shelves
    shelves = [p for p in parts if p["role"] == "shelf"]
    for shelf in shelves:
        shelf_w_cm = shelf["width_mm"] / 10
        if shelf_w_cm > max_span:
            errors.append({
                "rule": "max_span_check",
                "message": (
                    f"Repisa '{shelf['id']}' tiene {shelf_w_cm}cm de tramo libre. "
                    f"Máximo para {mat.get('name', material_key)}: {max_span}cm."
                ),
                "fix": "Agregar división vertical o listón de refuerzo.",
            })

    # Rule: cross_rails_wide
    if width_cm > 60:
        rails = [p for p in parts if p["role"] == "rail"]
        if not rails:
            errors.append({
                "rule": "cross_rails_wide",
                "message": f"Mueble de {width_cm}cm de ancho sin travesaños. Los laterales se abrirán.",
                "fix": "Agregar travesaños de 8cm mínimo, trasero superior e inferior.",
            })

    # Rule: vertical_divider_wide
    # Check if any section > 90cm
    dividers = [p for p in parts if p["role"] == "divider"]
    sides = [p for p in parts if p["role"] == "side"]
    if width_cm > 90 and not dividers:
        errors.append({
            "rule": "vertical_divider_wide",
            "message": f"Sección de {width_cm}cm sin división vertical. Las repisas se pandearán.",
            "fix": "Agregar panel vertical intermedio.",
        })

    # Rule: kickplate_floor_cabinet
    furniture_type = spec.get("furniture_type", "")
    floor_types = {"kitchen_base", "closet", "vanity"}
    if furniture_type in floor_types:
        has_kickplate = any(p["role"] == "kickplate" for p in parts)
        if not has_kickplate:
            warnings.append({
                "rule": "kickplate_floor_cabinet",
                "message": "Gabinete de piso sin zócalo.",
                "fix": "Agregar zócalo de 10cm retranqueado 5cm, o patas ajustables.",
            })

    # Rule: shelf_reinforcement
    for shelf in shelves:
        shelf_w_cm = shelf["width_mm"] / 10
        if shelf_w_cm > 80:
            warnings.append({
                "rule": "shelf_reinforcement",
                "message": f"Repisa '{shelf['id']}' de {shelf_w_cm}cm — considerar listón de refuerzo.",
                "fix": "Agregar listón de 2x4cm en borde trasero o frontal.",
            })

    # Rule: tall_furniture_anchoring
    if height_cm > 180:
        top_rails = [p for p in parts if p["role"] == "rail" and "top" in p["id"].lower()]
        if not top_rails:
            warnings.append({
                "rule": "tall_furniture_anchoring",
                "message": f"Mueble de {height_cm}cm de alto. Riesgo de volcadura.",
                "fix": "Agregar travesaño superior y escuadra de anclaje a pared.",
            })

    # Rule: floor_panel_load_bearing
    floor_panels = [p for p in parts if p["role"] in ("bottom", "floor")]
    for fp in floor_panels:
        if fp["thickness_mm"] < t_mm and furniture_type in floor_types:
            warnings.append({
                "rule": "floor_panel_load_bearing",
                "message": f"Piso '{fp['id']}' de {fp['thickness_mm']}mm — menor que laterales ({t_mm}mm).",
                "fix": "Usar mismo espesor que los laterales.",
            })

    status = "fail" if errors else "pass"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "rules_checked": len(STRUCTURAL_RULES),
        "summary": (
            f"{'✗' if errors else '✓'} {len(errors)} errores, {len(warnings)} advertencias. "
            f"{'Corregir errores antes de fabricar.' if errors else 'Estructura correcta.'}"
        ),
    }
