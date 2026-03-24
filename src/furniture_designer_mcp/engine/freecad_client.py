"""Lightweight XML-RPC client for FreeCAD.

Connects to the FreeCAD RPC server (started via the MCP Addon)
on localhost:9875 and executes Python code directly.

This avoids round-tripping generated scripts through the agent's
context window — the script is built and executed server-side,
returning only a short summary to the caller.
"""

from __future__ import annotations

import xmlrpc.client
import logging

logger = logging.getLogger(__name__)

_DEFAULT_HOST = "localhost"
_DEFAULT_PORT = 9875


class FreeCADClient:
    """Thin wrapper around the FreeCAD XML-RPC server."""

    def __init__(self, host: str = _DEFAULT_HOST, port: int = _DEFAULT_PORT):
        self._url = f"http://{host}:{port}"
        self._server = xmlrpc.client.ServerProxy(self._url, allow_none=True)

    def is_available(self) -> bool:
        """Check if FreeCAD RPC server is reachable."""
        try:
            return bool(self._server.ping())
        except Exception:
            return False

    def execute_code(self, code: str) -> dict:
        """Execute Python code in FreeCAD and return the result.

        Returns:
            dict with keys:
                success (bool): True if code ran without errors.
                message (str): stdout output from the code.
                error (str): error description if success is False.
        """
        try:
            result = self._server.execute_code(code)
            # The RPC server returns different formats depending on
            # success/failure.  Normalise to a consistent dict.
            if isinstance(result, dict):
                return result
            # Older versions may return a raw string on error
            if isinstance(result, str):
                return {"success": False, "error": result}
            return {"success": bool(result), "message": str(result)}
        except ConnectionRefusedError:
            return {
                "success": False,
                "error": (
                    "No se pudo conectar a FreeCAD. "
                    "Asegúrate de que FreeCAD esté abierto y el RPC Server "
                    f"esté corriendo en {self._url}."
                ),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Module-level singleton — created lazily.
_client: FreeCADClient | None = None


def get_client() -> FreeCADClient:
    """Return (and cache) the default FreeCAD client."""
    global _client
    if _client is None:
        _client = FreeCADClient()
    return _client
