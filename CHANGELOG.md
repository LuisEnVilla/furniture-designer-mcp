# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

## [0.1.1] — 2026-03-26

### Reporte HTML — Nuevas herramientas de visualizacion

- **Herramienta de medicion 3D**: boton "Medir" en el viewer — click en dos superficies de paneles para obtener la distancia exacta (mm/cm) con linea de acotado, desglose por ejes y nombres de las partes medidas. Zero tokens adicionales (100% client-side)
- **Diagrama 2D de dimensiones internas**: boton "Dimensiones" que muestra un diagrama tipo IKEA con vista frontal del mueble, acotado de espacios usables (ancho y alto de cada compartimiento), dimensiones externas totales y profundidad util. Unidades en cm
- **Correccion de orientacion de camara**: la vista 3D ahora abre desde el frente del mueble (donde van puertas/cajones) en lugar de desde atras
- **Vista frontal correcta en diagrama 2D**: espejo del eje X para que el diagrama coincida con la perspectiva natural del usuario mirando el mueble de frente

## [0.1.0] — 2026-03-26

Primera versión pública del servidor MCP para diseño de muebles.

### Motor de diseño

- **6 tipos de mueble**: `kitchen_base`, `kitchen_wall`, `closet`, `bookshelf`, `desk`, `vanity`
- **6 materiales**: `melamine_16`, `melamine_18`, `mdf_15`, `mdf_18`, `plywood_18`, `solid_pine_20`
- Generación completa de spec con paneles, posiciones XYZ, hardware y canteado
- Cajones completos: caja de 5 piezas (frente + 2 laterales + trasera + fondo MDF) + correderas telescópicas
- Divisiones verticales automáticas cuando el ancho excede el tramo máximo del material
- Zócalo como marco de 4 piezas: `kickplate_front`, `kickplate_back`, `kickplate_return_l`, `kickplate_return_r`
- Límites de cantidad: `num_shelves` <= 20, `num_drawers` <= 10 (con warning si se exceden)

### Validación estructural

- 10 reglas de ingeniería con severidad (`error` / `warning`)
- Respaldo obligatorio, tramo máximo, travesaños, divisores, zócalo, anclaje, refuerzo, confirmats, piso

### Optimización de cortes

- Bin packing 2D en tableros estándar 2440x1220mm
- Soporte de dirección de veta (`grain_direction`)
- Desbaste de sierra (kerf) configurable (3mm default)
- Auto-relajación de grano cuando una pieza no cabe
- Filtro automático de paneles MDF (respaldos, fondos de cajón) — se cortan de stock diferente
- Auto-conversión `width_mm` -> `width` con warning

### Multi-diseño y persistencia

- `create_design` / `list_designs` / `get_design_context` para gestión de proyectos
- Persistencia en `./designs/{design_id}/` con `report.html`, `spec.json`, `metadata.json`
- Cada iteración se guarda como nueva versión con comentario

### Servidor HTTP + Live Reload

- Servidor HTTP en puerto 8432 (aiohttp)
- WebSocket para notificación automática de cambios
- Página índice en `/` con lista de diseños activos
- Fallback a puerto aleatorio si 8432 está ocupado
- Auto-reconexión del WebSocket con backoff exponencial

### Reporte HTML interactivo

- Viewer 3D con Three.js v0.169 (ES Modules via importmap)
- 4 páginas: Diseño (ensamblado), Partes (explosionado), Cortes (SVG), Historial (timeline)
- Paleta clara: fondo `#f8f9fb`, cards blancas, tipografía DM Sans + JetBrains Mono
- Layout de cortes SVG coloreado por rol con canteado visual
- Barra de uso por tablero (verde/amarillo/rojo)
- Ficha técnica tipo producto con specs, roles, hardware y notas
- Slider de iteraciones para comparar versiones
- Responsive para desktop

### Mapa de secciones

- `section_mapper.py`: asignación automática de etiquetas (izquierda, centro, derecha)
- Aliases en español para resolución de lenguaje natural
- `get_section_map` tool con parámetro `resolve` para consultas directas

### Base de conocimiento

- Estándares ergonómicos por tipo de mueble
- Propiedades de 6 materiales con tramos máximos
- Catálogo de herrajes con reglas de cantidad
- Especificaciones de ensamble: uniones, adhesivos, pre-taladrado, montaje

### FreeCAD (exportar)

- Ejecución directa via XML-RPC (no retorna scripts, ejecuta en FreeCAD)
- Modelo 3D con `App::Part`, grupos por rol, propiedades custom
- Vista explosionada con separación por eje de ensamble
- Diagrama de corte (vista superior de tableros)
- Plano técnico TechDraw (vistas ortogonales A3)
- Labels con dimensiones en mm

### FreeCAD (importar)

- Script de extracción para documentos FreeCAD existentes
- Parseo a spec con detección de roles y warnings de importación

### Desarrollo

- `reload_engine` para hot-reload sin reiniciar servidor
- Modo `compact=true` en design tools (resumen + JSON reducido)
- Modo `brief=true` en knowledge tools (ahorro 60-80% tokens)
- Validación de spec en todas las tools con errores descriptivos

### Roles de panel soportados

`side`, `bottom`, `top_panel`, `floor`, `shelf`, `back`, `door`, `rail`, `kickplate`, `kickplate_return`, `divider`, `drawer_front`, `drawer_side`, `drawer_back`, `drawer_bottom`
