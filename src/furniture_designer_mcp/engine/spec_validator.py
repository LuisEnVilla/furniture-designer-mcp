"""Validation helpers for furniture specs and cut-optimizer part lists."""

from __future__ import annotations

VALID_ROLES: set[str] = {
    "side",
    "bottom",
    "top_panel",
    "floor",
    "shelf",
    "back",
    "door",
    "rail",
    "kickplate",
    "kickplate_return",
    "divider",
    "drawer_front",
    "drawer_side",
    "drawer_back",
    "drawer_bottom",
    "back_rail",
}

REQUIRED_PART_FIELDS: set[str] = {
    "id",
    "role",
    "width_mm",
    "height_mm",
    "thickness_mm",
}

REQUIRED_CUT_PART_FIELDS: set[str] = {
    "id",
    "width",
    "height",
}

# Maps commonly confused field names to their correct counterparts in a spec.
_FIELD_RENAMES: dict[str, str] = {
    "name": "id",
    "width": "width_mm",
    "height": "height_mm",
    "thickness": "thickness_mm",
    "position": "position_mm",
}

_NUMERIC_SPEC_FIELDS: tuple[str, ...] = ("width_mm", "height_mm", "thickness_mm")
_NUMERIC_CUT_FIELDS: tuple[str, ...] = ("width", "height")


def validate_spec(spec: dict) -> list[str]:
    """Validate a furniture spec dictionary.

    Returns a list of error strings.  An empty list means the spec is valid.
    """
    errors: list[str] = []

    # Detect 'panels' used instead of 'parts'
    if "panels" in spec and "parts" not in spec:
        errors.append(
            "Spec contains 'panels' instead of 'parts'. "
            "Rename the key to 'parts'."
        )
        return errors

    # 'parts' must be present, a list, and non-empty
    if "parts" not in spec:
        errors.append("Spec is missing the required 'parts' field.")
        return errors

    parts = spec["parts"]

    if not isinstance(parts, list):
        errors.append("'parts' must be a list.")
        return errors

    if len(parts) == 0:
        errors.append("'parts' list is empty; at least one part is required.")
        return errors

    # Validate each part
    for idx, part in enumerate(parts):
        prefix = f"parts[{idx}]"

        # Detect mis-named fields
        for wrong, correct in _FIELD_RENAMES.items():
            if wrong in part and correct not in part:
                errors.append(
                    f"{prefix}: found '{wrong}' — did you mean '{correct}'?"
                )

        # Check required fields
        for field in REQUIRED_PART_FIELDS:
            if field not in part:
                errors.append(f"{prefix}: missing required field '{field}'.")

        # Validate role value
        role = part.get("role")
        if role is not None and role not in VALID_ROLES:
            errors.append(
                f"{prefix}: unrecognised role '{role}'. "
                f"Valid roles: {', '.join(sorted(VALID_ROLES))}."
            )

        # Validate numeric types
        for field in _NUMERIC_SPEC_FIELDS:
            value = part.get(field)
            if value is not None and not isinstance(value, (int, float)):
                errors.append(
                    f"{prefix}: '{field}' must be numeric, got {type(value).__name__}."
                )

    return errors


def validate_cut_parts(parts: list[dict]) -> list[str]:
    """Validate a list of part dicts destined for ``optimize_cuts``.

    The schema expected by the cut optimizer differs from the furniture spec
    schema (e.g. ``width`` instead of ``width_mm``).

    Returns a list of error strings.  An empty list means the input is valid.
    """
    errors: list[str] = []

    if not isinstance(parts, list):
        errors.append("'parts' must be a list.")
        return errors

    if len(parts) == 0:
        errors.append("'parts' list is empty; at least one part is required.")
        return errors

    for idx, part in enumerate(parts):
        prefix = f"parts[{idx}]"

        # Detect spec-style fields used by mistake
        for spec_field, cut_field in (("width_mm", "width"), ("height_mm", "height")):
            if spec_field in part and cut_field not in part:
                errors.append(
                    f"{prefix}: found '{spec_field}' — the cut optimizer "
                    f"expects '{cut_field}' instead."
                )

        # Check required fields
        for field in REQUIRED_CUT_PART_FIELDS:
            if field not in part:
                errors.append(f"{prefix}: missing required field '{field}'.")

        # Validate numeric types
        for field in _NUMERIC_CUT_FIELDS:
            value = part.get(field)
            if value is not None and not isinstance(value, (int, float)):
                errors.append(
                    f"{prefix}: '{field}' must be numeric, got {type(value).__name__}."
                )

    return errors
