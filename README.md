# furniture-designer-mcp

MCP Server para diseño profesional de muebles de melamina y madera. Genera especificaciones completas, valida estructura, optimiza cortes, produce listas de materiales y genera scripts 3D para FreeCAD.

## Resumen ejecutivo

Este servidor MCP convierte dimensiones y tipo de mueble en un paquete completo listo para fabricación:

```
Entrada: "closet 120x240x60 en melamina 16mm"
                    ↓
        ┌───────────────────────┐
        │   design_furniture    │  → Spec completa con paneles, posiciones, hardware
        └───────────┬───────────┘
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
validate      generate_bom    optimize_cuts
    ↓               ↓               ↓
0 errores     12 paneles       3 tableros
0 warnings    26 confirmats    38% desperdicio
              6.2m cantos      veta alineada
                    ↓
            get_assembly_steps
                    ↓
            11 pasos ordenados
            con tornillería por paso
```

### Resultados que produce

| Herramienta | Resultado |
|---|---|
| `design_furniture` | Spec JSON con cada panel (dimensiones en mm, posición XYZ, rol, canto, material) |
| `validate_structure` | Reporte de errores (deben corregirse) y warnings (recomendados) contra 10 reglas estructurales |
| `generate_bom` | Lista agrupada de paneles, herrajes, cantos en metros, resumen de compra |
| `optimize_cuts` | Layout de corte por tablero con posiciones, rotación, dirección de veta, % desperdicio y diagrama ASCII |
| `get_assembly_steps` | Pasos ordenados con referencia a piezas, tipo de tornillo/fijación y tips por paso |
| `get_assembly_specs` | Especificaciones detalladas de ensamble: tipos de unión, adhesivos, pre-taladrado por material |
| `build_3d_model` | Script Python para FreeCAD con componentes App::Part, grupos por rol y propiedades de material |
| `build_exploded_view` | Script para vista explosionada con separación por eje de ensamble |
| `build_cut_diagram` | Script para visualizar layout de corte en FreeCAD (vista superior) |
| `build_import_script` | Script para leer paneles de un documento FreeCAD existente |
| `parse_freecad_import` | Reconstruir spec desde la salida del script de importación |

### Consideraciones

- **Dimensiones**: la entrada es en **cm**, la salida en **mm** (estándar de fabricación).
- **Veta**: el optimizador de cortes soporta `grain="length"` para mantener la dirección de veta consistente en melaminas con textura. Esto restringe la rotación de piezas y puede aumentar el número de tableros necesarios.
- **Kerf**: el desbaste de la sierra (3mm default) se descuenta en cada corte. Ajustable según la hoja utilizada.
- **Back panels**: siempre MDF 3mm por convención. El validador genera error si falta.
- **Divisiones automáticas**: si el ancho excede el tramo máximo del material, se agrega división vertical automáticamente.
- **Muebles altos (>180cm)**: el validador genera warning de anclaje a pared.
- **Modo `brief`**: las knowledge tools aceptan `brief=true` para respuestas compactas (ahorro de 34-84% en tokens). Recomendado para agentes con ventana de contexto limitada.
- **FreeCAD**: los scripts generan componentes `App::Part` con propiedades (`Material`, `Role`, `Thickness_mm`, `RealDimensions`, `EdgeBanding`) y grupos por función (`Estructura`, `Repisas`, `Puertas`, `Respaldo`). Requiere FreeCAD 0.21+ con el addon MCP.
- Los **labels de paneles** en FreeCAD incluyen dimensiones en mm (ej: "Lateral — side_left (590×2215×18mm)")
- Todas las tools validan el spec de entrada y retornan errores claros si el formato es incorrecto
- El optimizador de cortes genera **sugerencias accionables** cuando una pieza no cabe en el tablero

## Instalación

```bash
uvx furniture-designer-mcp
```

O en `.mcp.json`:

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

## Herramientas (16 tools)

### Diseño

| Tool | Descripción |
|---|---|
| `design_furniture` | Genera spec completa con paneles, hardware, posiciones y notas estructurales |

### Conocimiento

| Tool | Descripción |
|---|---|
| `get_standards` | Estándares ergonómicos por tipo de mueble |
| `get_material_specs` | Propiedades del material (espesor, tramo máximo, agarre de tornillo) |
| `get_structural_rules` | 10 reglas estructurales con severidad y solución |
| `get_hardware_catalog` | Catálogo de herrajes con reglas de cantidad y colocación |
| `get_assembly_specs` | Especificaciones de ensamble: uniones, adhesivos, pre-taladrado, montaje de bisagras/correderas |

Todas las knowledge tools aceptan `brief=true` para respuestas compactas.

### Validación y fabricación

| Tool | Descripción |
|---|---|
| `validate_structure` | Valida spec contra reglas estructurales (errores + warnings) |
| `generate_bom` | Bill of Materials: paneles agrupados, herrajes, cantos |
| `optimize_cuts` | Optimización de corte 2D en tableros estándar con soporte de veta y kerf |
| `get_assembly_steps` | Instrucciones de ensamble paso a paso en español |

### FreeCAD — Exportar (requiere freecad-mcp)

| Tool | Descripción |
|---|---|
| `build_3d_model` | Script para modelo 3D con componentes, grupos y propiedades |
| `build_exploded_view` | Script para vista explosionada |
| `build_cut_diagram` | Script para diagrama de corte (vista superior) |
| `build_techdraw` | Script para plano técnico TechDraw con vistas ortogonales |

### FreeCAD — Importar (requiere freecad-mcp)

| Tool | Descripción |
|---|---|
| `build_import_script` | Script para extraer paneles de un documento FreeCAD existente |
| `parse_freecad_import` | Parsear salida del script de importación a spec de mueble |

## Tipos de mueble soportados

| Tipo | Descripción | Características |
|---|---|---|
| `kitchen_base` | Gabinete base de cocina | Zócalo, travesaños, sin tapa (para cubierta) |
| `kitchen_wall` | Gabinete aéreo de cocina | Sin zócalo, tapa superior e inferior |
| `closet` | Closet / armario | Zócalo, divisiones automáticas si >75cm ancho |
| `bookshelf` | Librero / estantería | Repisas múltiples, puertas opcionales |
| `desk` | Escritorio | Espacio para rodillas (60cm), panel de recato |
| `vanity` | Vanitorio / mueble de baño | Estructura tipo base de cocina |

## Materiales soportados

| Material | Espesor | Tramo máximo sin soporte |
|---|---|---|
| `melamine_16` (default) | 16mm | 75cm |
| `melamine_18` | 18mm | 85cm |
| `mdf_15` | 15mm | 80cm |
| `mdf_18` | 18mm | 90cm |
| `plywood_18` | 18mm | 100cm |
| `solid_pine_20` | 20mm | 110cm |

## Licencia

MIT
