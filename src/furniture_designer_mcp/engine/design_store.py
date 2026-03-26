"""Multi-design store with persistence.

Manages multiple furniture designs, each with its own directory containing:
- report.html  — interactive HTML report for the browser
- spec.json    — latest furniture spec for fast agent reads
- metadata.json — design metadata (name, type, timestamps, iteration count)
"""

from __future__ import annotations

import json
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _slug(name: str) -> str:
    """Convert a design name to a URL-safe slug."""
    s = name.lower().strip()
    s = re.sub(r"[áàäâ]", "a", s)
    s = re.sub(r"[éèëê]", "e", s)
    s = re.sub(r"[íìïî]", "i", s)
    s = re.sub(r"[óòöô]", "o", s)
    s = re.sub(r"[úùüû]", "u", s)
    s = re.sub(r"[ñ]", "n", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "design"


class DesignStore:
    """Manages multiple furniture designs on disk."""

    def __init__(self, base_dir: str = "./designs"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create(self, name: str, furniture_type: str) -> dict:
        """Create a new design directory.

        Returns: {"design_id": str, "path": str, "created": str}
        """
        design_id = _slug(name)

        # Avoid collisions
        design_dir = self.base_dir / design_id
        if design_dir.exists():
            i = 2
            while (self.base_dir / f"{design_id}-{i}").exists():
                i += 1
            design_id = f"{design_id}-{i}"
            design_dir = self.base_dir / design_id

        design_dir.mkdir(parents=True)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        metadata = {
            "name": name,
            "type": furniture_type,
            "design_id": design_id,
            "created": now,
            "updated": now,
            "iterations_count": 0,
        }
        (design_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2)
        )

        logger.info("Created design '%s' at %s", design_id, design_dir)
        return {
            "design_id": design_id,
            "path": str(design_dir),
            "created": now,
        }

    def list_designs(self) -> list[dict]:
        """List all designs with metadata."""
        designs = []
        if not self.base_dir.exists():
            return designs

        for d in sorted(self.base_dir.iterdir()):
            if not d.is_dir():
                continue
            meta_path = d / "metadata.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text())
                meta["has_report"] = (d / "report.html").exists()
                meta["has_spec"] = (d / "spec.json").exists()
                designs.append(meta)
            except Exception as e:
                logger.warning("Failed to read metadata for %s: %s", d.name, e)

        return designs

    def get_spec(self, design_id: str) -> dict | None:
        """Read the latest spec.json for a design."""
        spec_path = self.base_dir / design_id / "spec.json"
        if not spec_path.exists():
            return None
        try:
            return json.loads(spec_path.read_text())
        except Exception as e:
            logger.error("Failed to read spec for %s: %s", design_id, e)
            return None

    def get_metadata(self, design_id: str) -> dict | None:
        """Read metadata.json for a design."""
        meta_path = self.base_dir / design_id / "metadata.json"
        if not meta_path.exists():
            return None
        try:
            return json.loads(meta_path.read_text())
        except Exception:
            return None

    def save_iteration(
        self,
        design_id: str,
        spec: dict,
        comment: str = "",
        iteration_name: str = "",
        cut_data: dict | None = None,
    ) -> dict:
        """Save a new iteration for a design.

        Writes spec.json, updates metadata.json, generates report.html.
        Returns: {"iteration": str, "report_path": str, "spec_path": str}
        """
        design_dir = self.base_dir / design_id
        if not design_dir.exists():
            raise FileNotFoundError(f"Design '{design_id}' not found.")

        # Read current metadata
        meta_path = design_dir / "metadata.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

        # Determine iteration name
        count = meta.get("iterations_count", 0) + 1
        if not iteration_name:
            iteration_name = f"v{count}"

        # Write spec.json (atomic)
        spec_path = design_dir / "spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2))

        # Generate report.html
        from .report_generator import generate_design_report

        report_path = str(design_dir / "report.html")
        generate_design_report(
            spec=spec,
            comment=comment,
            iteration_name=iteration_name,
            output_path=report_path,
            cut_data=cut_data,
        )

        # Update metadata
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        meta["updated"] = now
        meta["iterations_count"] = count
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

        logger.info("Saved iteration %s for design '%s'", iteration_name, design_id)

        return {
            "iteration": iteration_name,
            "report_path": report_path,
            "spec_path": str(spec_path),
        }

    def get_report_path(self, design_id: str) -> str | None:
        """Get the report.html path for a design."""
        path = self.base_dir / design_id / "report.html"
        return str(path) if path.exists() else None

    def design_exists(self, design_id: str) -> bool:
        """Check if a design directory exists."""
        return (self.base_dir / design_id / "metadata.json").exists()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_store: DesignStore | None = None


def get_store(base_dir: str = "./designs") -> DesignStore:
    """Get or create the singleton DesignStore."""
    global _store
    if _store is None:
        _store = DesignStore(base_dir=base_dir)
    return _store
