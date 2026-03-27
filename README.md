# furniture-designer-mcp

> **v0.1.1** — Servidor MCP para diseño profesional de muebles

Servidor [Model Context Protocol](https://modelcontextprotocol.io/) que convierte dimensiones y tipo de mueble en un paquete completo listo para fabricación: especificación técnica, validación estructural, optimización de cortes, lista de materiales, instrucciones de ensamble, reporte HTML interactivo con viewer 3D, y exportación opcional a FreeCAD.

<img width="1200" alt="reporte" src="https://github.com/user-attachments/assets/8218cef2-4624-49e2-856d-f965600ee53e" />


## Flujo general

```
"closet 180x240x60 en melamina 18mm, 2 secciones"
                    |
        +-----------------------+
        |   design_furniture    |  -> Spec: paneles, posiciones, hardware, secciones
        +-----------+-----------+
                    |
    +---------------+---------------+
    |               |               |
validate      generate_bom    optimize_cuts
    |               |               |
0 errores     18 paneles       3 tableros
1 warning     34 confirmats    32% desperdicio
              8.4m cantos      veta alineada
                    |
            get_assembly_steps
                    |
            14 pasos ordenados
            con tornilleria por paso
                    |
        update_design_report
                    |
        Reporte HTML interactivo
        http://localhost:8432/closet-dormitorio
```

## Instalacion

### Como servidor MCP (recomendado)

```bash
uvx furniture-designer-mcp
```

En `.mcp.json` de tu proyecto:

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

### Desarrollo local

```bash
git clone https://github.com/LuisEnVilla/furniture-designer-mcp.git
cd furniture-designer-mcp
uv sync
uv run furniture-designer-mcp
```

## Funcionalidades principales

### Reporte HTML interactivo

El entregable principal es un reporte HTML servido en `http://localhost:8432/{design_id}` con:

- **Pagina Diseno** — Viewer 3D (Three.js) del mueble ensamblado + ficha tecnica con specs, roles, hardware y notas. Incluye herramienta de medicion interactiva y diagrama 2D de dimensiones internas (tipo IKEA)
- **Pagina Partes** — Vista 3D explosionada + tabla de partes con dimensiones y canteado + guia de ensamble
- **Pagina Cortes** — Layout SVG por tablero con piezas coloreadas por rol, canteado visual, barra de uso (verde/amarillo/rojo)
- **Pagina Historial** — Timeline vertical de iteraciones con badges de cambios

<img width="1200" alt="Pagina Diseno" src="https://github.com/user-attachments/assets/127ca291-bd01-45a6-a9e2-fcacc2d5d2cf" />

<img width="1200" alt="Pagina Partes — vista explosionada" src="https://github.com/user-attachments/assets/580771cc-f25a-424d-b62b-d7c3a88c9ae5" />

<img width="1200" alt="Pagina Historial — timeline de iteraciones" src="https://github.com/user-attachments/assets/0762242f-80b8-457b-a5c3-fc70323fbb62" />


### Multi-diseno con persistencia

Cada diseño se almacena en `./designs/{design_id}/` con:

```
designs/
  closet-dormitorio/
    report.html       <- servido en http://localhost:8432/closet-dormitorio
    spec.json         <- ultimo spec (lectura rapida para el agente)
    metadata.json     <- {name, type, created, updated, iterations}
  cocina-isla/
    report.html
    spec.json
    metadata.json
```

Puedes trabajar en multiples diseños simultáneamente y retomar cualquiera en sesiones futuras.

### Live reload via WebSocket

El reporte se actualiza automáticamente en el navegador cada vez que el agente genera una nueva iteración. No necesitas recargar la página — el WebSocket notifica el cambio y el JS actualiza la vista.

### Mapa de secciones con lenguaje natural

El motor genera etiquetas de sección automáticamente basadas en los divisores verticales del diseño:

```json
{
  "S1": {
    "label_es": "Seccion izquierda",
    "aliases": ["izq", "left", "primera"],
    "x_start_mm": 18, "x_end_mm": 900,
    "parts": ["shelf_S1_1", "bar_S1"]
  },
  "S2": {
    "label_es": "Seccion derecha",
    "aliases": ["der", "right", "ultima"],
    "x_start_mm": 918, "x_end_mm": 1782,
    "parts": ["drawer_S2_1_front", "drawer_S2_2_front"]
  }
}
```

Esto permite que el usuario diga "haz la izquierda mas ancha" y el agente resuelva la referencia a la sección correcta.

### Zocalo como marco estructural

El zócalo no es un panel suelto — es un marco rectangular de 4 piezas que soporta todo el peso del mueble:

```
Vista superior del zocalo:

    +------ kickplate_front ------+    <- frente (retranqueado 5cm)
    |                              |
    kickplate_return_l    kickplate_return_r    <- retornos laterales
    |                              |
    +------ kickplate_back -------+    <- fondo
```

El frente se retranquea 5cm para que los pies no choquen. Los laterales del mueble se apoyan encima de este marco.

### Filtro automatico de paneles MDF

Los paneles de MDF 3mm (respaldos, fondos de cajón) se filtran automáticamente del optimizador de cortes — se cortan de un stock diferente (tablero MDF, no melamina). El filtro actúa sobre roles `back`, `drawer_bottom`, y cualquier panel con espesor menor al material principal.

## Herramientas (23 tools)

### Diseno

| Tool | Descripcion |
|---|---|
| `design_furniture` | Genera spec completa con paneles, hardware, posiciones, secciones y notas estructurales |

### Conocimiento

| Tool | Descripcion |
|---|---|
| `get_standards` | Estándares ergonómicos por tipo de mueble |
| `get_material_specs` | Propiedades del material (espesor, tramo máximo, agarre de tornillo) |
| `get_structural_rules` | 10 reglas estructurales con severidad y solución |
| `get_hardware_catalog` | Catálogo de herrajes con reglas de cantidad y colocación |
| `get_assembly_specs` | Especificaciones de ensamble: uniones, adhesivos, pre-taladrado, montaje |

> Todas aceptan `brief=true` para respuestas compactas (ahorro 60-80% tokens).

### Validacion y fabricacion

| Tool | Descripcion |
|---|---|
| `validate_structure` | Valida spec contra 10 reglas estructurales (errores + warnings) |
| `generate_bom` | Bill of Materials: paneles agrupados, herrajes, cantos en metros |
| `optimize_cuts` | Optimización 2D en tableros estándar (2440x1220mm) con veta y kerf |
| `get_assembly_steps` | Instrucciones de ensamble paso a paso en español |

### Multi-diseno y reporte

| Tool | Descripcion |
|---|---|
| `create_design` | Crea proyecto de diseño nuevo (retorna design_id) |
| `list_designs` | Lista todos los diseños activos con metadata |
| `get_design_context` | Recupera spec + historial de un diseño para retomar |
| `get_section_map` | Mapa de secciones con etiquetas y resolución de lenguaje natural |
| `start_design_server` | Inicia servidor HTTP (puerto 8432) con WebSocket live reload |
| `update_design_report` | Genera/actualiza reporte HTML interactivo |

### FreeCAD — exportar (requiere FreeCAD + RPC server)

| Tool | Descripcion |
|---|---|
| `build_3d_model` | Construye modelo 3D ensamblado en FreeCAD via XML-RPC |
| `build_exploded_view` | Construye vista explosionada en FreeCAD |
| `build_cut_diagram` | Construye diagrama de corte en FreeCAD |
| `build_techdraw` | Construye plano técnico TechDraw (vistas ortogonales A3) |

### FreeCAD — importar (requiere freecad-mcp)

| Tool | Descripcion |
|---|---|
| `build_import_script` | Script para extraer paneles de un documento FreeCAD existente |
| `parse_freecad_import` | Parsear salida del script de importación a spec |

### Desarrollo

| Tool | Descripcion |
|---|---|
| `reload_engine` | Recarga módulos del engine sin reiniciar el servidor MCP |

## Tipos de mueble

| Tipo | Descripcion | Caracteristicas clave |
|---|---|---|
| `kitchen_base` | Gabinete base de cocina | Zócalo 4 piezas, travesaños, sin tapa (para cubierta) |
| `kitchen_wall` | Gabinete aéreo de cocina | Sin zócalo, tapa superior e inferior |
| `closet` | Closet / armario | Zócalo, divisiones auto si >75cm, alerta anclaje si >180cm |
| `bookshelf` | Librero / estantería | Repisas múltiples, puertas opcionales |
| `desk` | Escritorio | Espacio para rodillas (60cm), panel de recato |
| `vanity` | Vanitorio / mueble de baño | Estructura tipo base de cocina |

<!-- ![Tipos de mueble soportados — diagrama comparativo](docs/screenshots/furniture-types-overview.png) -->

## Materiales

| Material | Espesor | Tramo max. sin soporte | Mejor para |
|---|---|---|---|
| `melamine_16` (default) | 16mm | 75cm | Uso general, más económico |
| `melamine_18` | 18mm | 85cm | Cocinas y closets de gama alta |
| `mdf_15` | 15mm | 80cm | Muebles pintados |
| `mdf_18` | 18mm | 90cm | Puertas con diseño CNC |
| `plywood_18` | 18mm | 100cm | Tramos largos, alta resistencia |
| `solid_pine_20` | 20mm | 120cm | Muebles de madera maciza |

## Arquitectura del servidor

```
furniture-designer-mcp/
  src/furniture_designer_mcp/
    server.py                  <- Punto de entrada MCP (23 tools)
    engine/
      designer.py              <- Motor principal: spec + section_labels
      structural_validator.py  <- 10 reglas estructurales
      cut_optimizer.py         <- Bin packing 2D con veta y kerf
      bom_generator.py         <- Bill of Materials
      spec_validator.py        <- Validacion de formato de spec
      spec_builder.py          <- Construccion de spec desde parametros
      section_mapper.py        <- Mapa de secciones + resolucion natural
      design_store.py          <- Multi-diseno + persistencia ./designs/
      http_server.py           <- HTTP + WebSocket (puerto 8432)
      report_generator.py      <- Template HTML interactivo (~1900 lineas)
      freecad_scripts.py       <- Generacion de scripts FreeCAD
      freecad_client.py        <- XML-RPC client para FreeCAD
    knowledge/
      standards.py             <- Estandares ergonomicos
      materials.py             <- Propiedades de materiales
      structural_rules.py      <- Reglas de ingenieria
      hardware_catalog.py      <- Catalogo de herrajes
      assembly_specs.py        <- Especificaciones de ensamble
```

## Consideraciones tecnicas

### Unidades

- **Entrada**: dimensiones en **cm** (ancho, alto, fondo)
- **Salida**: spec en **mm** (`width_mm`, `height_mm`, `thickness_mm`)
- **Cortes**: el optimizer usa `width`/`height` (sin sufijo `_mm`) — schema diferente al spec

### Veta del material

El optimizador soporta `grain_direction="length"` para mantener la dirección de veta consistente en melaminas con textura. Esto restringe la rotación de piezas. Si una pieza no cabe con restricción de veta, se relaja automáticamente a `none` con aviso.

### Desbaste de sierra (kerf)

3mm por defecto. Se descuenta en cada corte del optimizador. Ajustable según la hoja utilizada.

### Respaldos

Siempre MDF 3mm. El validador genera error si un mueble no tiene panel trasero (rol `back`). Se excluyen automáticamente del optimizador de cortes de melamina.

### Divisiones automaticas

Si el ancho de una sección excede el tramo máximo del material, se agrega una división vertical automáticamente.

### Muebles altos (>180cm)

El validador genera warning de anclaje a pared por riesgo de volcamiento.

### Cajones completos

`design_furniture` genera caja completa: frente + 2 laterales + trasera + fondo MDF 3mm + correderas telescópicas.

### Modo compact

Las tools principales retornan `compact=true` por defecto: resumen legible + JSON reducido. Usar `compact=false` solo si se necesita el JSON completo.

### Hot-reload

`reload_engine` recarga todos los módulos del engine sin reiniciar el servidor MCP. Útil durante desarrollo.

## Requisitos

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) para gestión de paquetes
- FreeCAD 0.21+ con addon MCP (solo para exportación 3D)

## Licencia

MIT
