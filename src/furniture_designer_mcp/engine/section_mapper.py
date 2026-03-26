"""Section mapper — resolve natural language references to section IDs.

Analyzes a furniture spec to identify sections (created by vertical dividers)
and assigns human-readable labels and aliases for natural language resolution.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Label templates by section count
# ---------------------------------------------------------------------------

_LABELS_BY_COUNT = {
    1: [
        {"label_es": "Sección principal", "label_short": "principal",
         "aliases": ["principal", "única", "todo", "completo", "main"]},
    ],
    2: [
        {"label_es": "Sección izquierda", "label_short": "izquierda",
         "aliases": ["izquierda", "izq", "left", "primera", "1"]},
        {"label_es": "Sección derecha", "label_short": "derecha",
         "aliases": ["derecha", "der", "right", "última", "segunda", "2"]},
    ],
    3: [
        {"label_es": "Sección izquierda", "label_short": "izquierda",
         "aliases": ["izquierda", "izq", "left", "primera", "1"]},
        {"label_es": "Sección centro", "label_short": "centro",
         "aliases": ["centro", "central", "medio", "middle", "center", "segunda", "2"]},
        {"label_es": "Sección derecha", "label_short": "derecha",
         "aliases": ["derecha", "der", "right", "última", "tercera", "3"]},
    ],
    4: [
        {"label_es": "Sección izquierda", "label_short": "izquierda",
         "aliases": ["izquierda", "izq", "left", "primera", "1"]},
        {"label_es": "Sección centro-izquierda", "label_short": "centro-izq",
         "aliases": ["centro-izq", "centro-izquierda", "segunda", "2"]},
        {"label_es": "Sección centro-derecha", "label_short": "centro-der",
         "aliases": ["centro-der", "centro-derecha", "tercera", "3"]},
        {"label_es": "Sección derecha", "label_short": "derecha",
         "aliases": ["derecha", "der", "right", "última", "cuarta", "4"]},
    ],
}


def _labels_for_count(n: int) -> list[dict]:
    """Get label templates for a given section count."""
    if n in _LABELS_BY_COUNT:
        return _LABELS_BY_COUNT[n]

    # For 5+ sections, generate numbered labels
    labels = []
    for i in range(n):
        if i == 0:
            short = "izquierda"
            aliases = ["izquierda", "izq", "left", "primera", str(i + 1)]
        elif i == n - 1:
            short = "derecha"
            aliases = ["derecha", "der", "right", "última", str(i + 1)]
        else:
            short = f"sección {i + 1}"
            aliases = [f"sección {i + 1}", str(i + 1)]
        labels.append({
            "label_es": f"Sección {short}",
            "label_short": short,
            "aliases": aliases,
        })
    return labels


# ---------------------------------------------------------------------------
# Main functions
# ---------------------------------------------------------------------------


def map_sections(spec: dict) -> dict:
    """Generate section_labels from a furniture spec.

    Analyzes dividers and parts to create a section map with:
    - Human-readable labels (Spanish)
    - Aliases for natural language matching
    - X boundaries for each section
    - Part IDs belonging to each section

    Returns:
        dict mapping section IDs (S1, S2, ...) to section info.
    """
    parts = spec.get("parts", [])
    t = spec.get("material_thickness_mm", 18)
    dims = spec.get("dimensions_mm", {})
    total_w = dims.get("width", 0)

    # Find dividers (sorted by X position)
    dividers = sorted(
        [p for p in parts if p.get("role") == "divider"],
        key=lambda p: (p.get("position_mm") or {}).get("x", 0),
    )

    # Calculate section boundaries
    if not dividers:
        # Single section
        sections_bounds = [(t, total_w - t)]
    else:
        bounds = []
        prev_x = t  # After left side panel
        for div in dividers:
            div_x = (div.get("position_mm") or {}).get("x", 0)
            bounds.append((prev_x, div_x))
            prev_x = div_x + t
        bounds.append((prev_x, total_w - t))  # Last section to right side
        sections_bounds = bounds

    num_sections = len(sections_bounds)
    labels = _labels_for_count(num_sections)

    # Build section map
    section_map = {}
    for i, (x_start, x_end) in enumerate(sections_bounds):
        section_id = f"S{i + 1}"
        label_info = labels[i] if i < len(labels) else {
            "label_es": f"Sección {i + 1}",
            "label_short": str(i + 1),
            "aliases": [str(i + 1)],
        }

        # Find parts in this section (by X position within bounds)
        section_parts = []
        for p in parts:
            pos = p.get("position_mm") or {}
            px = pos.get("x", 0)
            role = p.get("role", "")
            # Skip structural parts (sides, top, bottom, kickplate, rails, dividers)
            if role in ("side", "top_panel", "bottom", "kickplate", "kickplate_return", "rail", "divider", "back_rail"):
                continue
            # Check if part's X is within section bounds
            if x_start <= px < x_end:
                section_parts.append(p.get("id", ""))

        section_map[section_id] = {
            "label_es": label_info["label_es"],
            "label_short": label_info["label_short"],
            "aliases": label_info["aliases"],
            "column_index": i,
            "x_start_mm": round(x_start, 1),
            "x_end_mm": round(x_end, 1),
            "width_mm": round(x_end - x_start, 1),
            "parts": section_parts,
        }

    return section_map


def resolve_reference(section_labels: dict, user_text: str) -> str | None:
    """Resolve a natural language reference to a section ID.

    Examples:
        "izquierda" → "S1"
        "centro"    → "S2"
        "derecha"   → "S3"
        "cajón 2 del centro" → "S2" (extracts section reference)
        "S2"        → "S2" (pass-through)

    Returns:
        Section ID (e.g., "S1") or None if no match.
    """
    if not section_labels or not user_text:
        return None

    text = user_text.lower().strip()

    # Direct match (S1, S2, etc.)
    direct = re.match(r"^s(\d+)$", text)
    if direct:
        sid = f"S{direct.group(1)}"
        if sid in section_labels:
            return sid

    # Search by aliases
    best_match = None
    best_len = 0
    for section_id, info in section_labels.items():
        for alias in info.get("aliases", []):
            alias_lower = alias.lower()
            if alias_lower in text and len(alias_lower) > best_len:
                best_match = section_id
                best_len = len(alias_lower)

    return best_match
