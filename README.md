# furniture-designer-mcp

MCP Server for professional furniture design — structural validation, cut optimization, BOM generation, and ergonomic standards.

## Install

```bash
uvx furniture-designer-mcp
```

Or in `.mcp.json`:

```json
{
  "mcpServers": {
    "furniture-designer": {
      "command": "uvx",
      "args": ["furniture-designer-mcp"]
    }
  }
}
```

## Tools

| Tool | Description |
|---|---|
| `design_furniture` | Generate a complete furniture spec with standards applied |
| `validate_structure` | Validate spec against structural rules |
| `optimize_cuts` | 2D bin packing for panel cutting on standard sheets |
| `generate_bom` | Bill of Materials with panels, hardware, edge banding |
| `get_assembly_steps` | Step-by-step assembly instructions |
| `get_standards` | Ergonomic standards by furniture type |
| `get_material_specs` | Material properties and limits |
| `get_structural_rules` | All structural rules |
| `get_hardware_catalog` | Hardware catalog with selection rules |
| `build_3d_model` | Generate FreeCAD script to build the furniture in 3D |
| `build_exploded_view` | Generate FreeCAD script for exploded assembly view |
| `build_cut_diagram` | Generate FreeCAD script to visualize cut layout on sheets |
