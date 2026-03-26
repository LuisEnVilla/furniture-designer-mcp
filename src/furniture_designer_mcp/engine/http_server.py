"""HTTP server with WebSocket for live reload of design reports.

Serves HTML reports from a designs directory and notifies connected
browsers via WebSocket when a design is updated.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DesignServer
# ---------------------------------------------------------------------------


class DesignServer:
    """Lightweight HTTP + WebSocket server for design reports.

    Routes:
        GET /                        → Index page listing all designs
        GET /{design_id}             → Serve report.html
        GET /api/{design_id}/spec    → JSON spec for the design
        WS  /ws/{design_id}          → WebSocket channel for live reload
    """

    def __init__(self, port: int = 8432, designs_dir: str = "./designs"):
        self.port = port
        self.designs_dir = Path(designs_dir).resolve()
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._ws_clients: dict[str, list[web.WebSocketResponse]] = {}
        self._started = False

    # -- Public API ----------------------------------------------------------

    async def start(self) -> str:
        """Start the server. Returns the base URL."""
        if self._started:
            return self.get_base_url()

        self.designs_dir.mkdir(parents=True, exist_ok=True)

        app = web.Application()
        app.router.add_get("/", self._handle_index)
        app.router.add_get("/ws/{design_id}", self._handle_ws)
        app.router.add_get("/api/{design_id}/spec", self._handle_spec)
        app.router.add_get("/{design_id}", self._handle_report)

        self._app = app
        self._runner = web.AppRunner(app)
        await self._runner.setup()

        # Try preferred port, fallback to OS-assigned
        try:
            site = web.TCPSite(self._runner, "localhost", self.port)
            await site.start()
        except OSError:
            logger.warning("Port %d busy, using random port", self.port)
            site = web.TCPSite(self._runner, "localhost", 0)
            await site.start()
            # Extract actual port from the socket
            sock = site._server.sockets[0]
            self.port = sock.getsockname()[1]

        self._started = True
        logger.info("Design server started at %s", self.get_base_url())
        return self.get_base_url()

    async def stop(self):
        """Stop the server."""
        if self._runner:
            await self._runner.cleanup()
            self._started = False

    async def notify_update(self, design_id: str):
        """Notify all WebSocket clients watching a design that it changed."""
        clients = self._ws_clients.get(design_id, [])
        dead = []
        for ws in clients:
            try:
                await ws.send_str("reload")
            except Exception:
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            clients.remove(ws)

    def get_base_url(self) -> str:
        return f"http://localhost:{self.port}"

    def get_url(self, design_id: str) -> str:
        return f"{self.get_base_url()}/{design_id}"

    @property
    def is_running(self) -> bool:
        return self._started

    # -- Route handlers ------------------------------------------------------

    async def _handle_index(self, request: web.Request) -> web.Response:
        """Serve an index page listing all designs."""
        designs = []
        if self.designs_dir.exists():
            for d in sorted(self.designs_dir.iterdir()):
                if d.is_dir() and (d / "report.html").exists():
                    meta_path = d / "metadata.json"
                    meta = {}
                    if meta_path.exists():
                        try:
                            meta = json.loads(meta_path.read_text())
                        except Exception:
                            pass
                    designs.append({
                        "id": d.name,
                        "name": meta.get("name", d.name),
                        "type": meta.get("type", "—"),
                        "updated": meta.get("updated", "—"),
                        "iterations": meta.get("iterations_count", 0),
                    })

        rows = ""
        for d in designs:
            rows += (
                f'<tr>'
                f'<td><a href="/{d["id"]}" style="color:var(--accent);text-decoration:none;font-weight:500">{d["name"]}</a></td>'
                f'<td>{d["type"]}</td>'
                f'<td>{d["iterations"]}</td>'
                f'<td>{d["updated"]}</td>'
                f'</tr>'
            )

        if not rows:
            rows = '<tr><td colspan="4" style="text-align:center;color:var(--text-dim);padding:40px">No hay diseños aún. Usa <code>create_design</code> para comenzar.</td></tr>'

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Furniture Designer — Diseños</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
    --bg-base: #f8f9fb; --bg-white: #ffffff; --accent: #2563eb;
    --text-primary: #111827; --text-secondary: #4b5563; --text-dim: #9ca3af;
    --border: #e5e7eb; --radius: 8px;
}}
*, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:var(--bg-base); font-family:'DM Sans',sans-serif; color:var(--text-primary); padding:48px; }}
.container {{ max-width:800px; margin:0 auto; }}
h1 {{ font-size:24px; font-weight:600; margin-bottom:8px; }}
.subtitle {{ color:var(--text-dim); font-size:14px; margin-bottom:32px; }}
table {{ width:100%; border-collapse:collapse; background:var(--bg-white); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }}
th {{ text-align:left; padding:12px 16px; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-dim); border-bottom:2px solid var(--border); background:var(--bg-base); }}
td {{ padding:12px 16px; border-bottom:1px solid var(--border); color:var(--text-secondary); font-size:14px; }}
tr:last-child td {{ border-bottom:none; }}
code {{ font-family:'JetBrains Mono',monospace; font-size:13px; background:var(--bg-base); padding:2px 6px; border-radius:4px; }}
</style>
</head>
<body>
<div class="container">
    <h1>Furniture Designer</h1>
    <p class="subtitle">Diseños activos</p>
    <table>
        <thead><tr><th>Diseño</th><th>Tipo</th><th>Iteraciones</th><th>Última actualización</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
</div>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")

    async def _handle_report(self, request: web.Request) -> web.Response:
        """Serve a design's report.html."""
        design_id = request.match_info["design_id"]
        report_path = self.designs_dir / design_id / "report.html"
        if not report_path.exists():
            return web.Response(status=404, text=f"Design '{design_id}' not found.")
        return web.FileResponse(report_path)

    async def _handle_spec(self, request: web.Request) -> web.Response:
        """Return the latest spec.json for a design."""
        design_id = request.match_info["design_id"]
        spec_path = self.designs_dir / design_id / "spec.json"
        if not spec_path.exists():
            return web.Response(status=404, text=f"Spec for '{design_id}' not found.")
        return web.FileResponse(spec_path, headers={"Content-Type": "application/json"})

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket endpoint for live reload notifications."""
        design_id = request.match_info["design_id"]
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Register client
        if design_id not in self._ws_clients:
            self._ws_clients[design_id] = []
        self._ws_clients[design_id].append(ws)
        logger.debug("WS client connected for '%s' (%d total)",
                      design_id, len(self._ws_clients[design_id]))

        try:
            async for msg in ws:
                # We don't expect messages from the client, just keep connection alive
                pass
        finally:
            self._ws_clients[design_id].remove(ws)
            logger.debug("WS client disconnected from '%s'", design_id)

        return ws


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_server: DesignServer | None = None


def get_server(port: int = 8432, designs_dir: str = "./designs") -> DesignServer:
    """Get or create the singleton DesignServer."""
    global _server
    if _server is None:
        _server = DesignServer(port=port, designs_dir=designs_dir)
    return _server
