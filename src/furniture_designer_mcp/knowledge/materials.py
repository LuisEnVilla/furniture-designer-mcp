"""Material specifications for furniture design.

max_span_no_support: Maximum unsupported horizontal span (in cm) before
the shelf/panel will visibly sag under light load (~15 kg/m).
"""

MATERIALS: dict = {
    "mdf_15": {
        "name": "MDF 15mm",
        "thickness_mm": 15,
        "max_span_no_support_cm": 80,
        "density_kg_m3": 750,
        "screw_holding": "medium",
        "moisture_resistance": "low",
        "finish": "Requiere pintura o laminado",
        "edge_banding": True,
        "sheet_sizes_mm": [
            {"width": 2440, "height": 1220},
        ],
        "notes": [
            "Bueno para pintar — superficie lisa",
            "No resiste humedad, evitar en baños/cocinas sin sellar",
            "Agarre de tornillo menor que madera maciza — usar tarugos + pegamento en uniones críticas",
        ],
    },
    "mdf_18": {
        "name": "MDF 18mm",
        "thickness_mm": 18,
        "max_span_no_support_cm": 90,
        "density_kg_m3": 750,
        "screw_holding": "medium",
        "moisture_resistance": "low",
        "finish": "Requiere pintura o laminado",
        "edge_banding": True,
        "sheet_sizes_mm": [
            {"width": 2440, "height": 1220},
        ],
        "notes": [
            "Estándar para muebles pintados de calidad media-alta",
            "Ideal para puertas con diseño ruteado (CNC)",
        ],
    },
    "melamine_16": {
        "name": "Melamina 16mm",
        "thickness_mm": 16,
        "max_span_no_support_cm": 75,
        "density_kg_m3": 680,
        "screw_holding": "medium",
        "moisture_resistance": "medium",
        "finish": "Laminado de fábrica — listo para usar",
        "edge_banding": True,
        "sheet_sizes_mm": [
            {"width": 2440, "height": 1220},
            {"width": 1830, "height": 2440},
        ],
        "notes": [
            "Material más usado en carpintería comercial",
            "No necesita acabado adicional, solo canto en bordes vistos",
            "Confirmat 7x50mm es el tornillo estándar",
            "Colores disponibles: blanco, nogal, roble, wengué, gris, etc.",
        ],
    },
    "melamine_18": {
        "name": "Melamina 18mm",
        "thickness_mm": 18,
        "max_span_no_support_cm": 85,
        "density_kg_m3": 680,
        "screw_holding": "medium-high",
        "moisture_resistance": "medium",
        "finish": "Laminado de fábrica",
        "edge_banding": True,
        "sheet_sizes_mm": [
            {"width": 2440, "height": 1220},
            {"width": 1830, "height": 2440},
        ],
        "notes": [
            "Preferido para muebles de cocina y closets de alta gama",
            "Mejor agarre de tornillo que 16mm",
            "Más costoso que 16mm pero más robusto",
        ],
    },
    "plywood_18": {
        "name": "Triplay / contrachapado 18mm",
        "thickness_mm": 18,
        "max_span_no_support_cm": 100,
        "density_kg_m3": 600,
        "screw_holding": "high",
        "moisture_resistance": "medium-high",
        "finish": "Requiere acabado (barniz, laca, laminado)",
        "edge_banding": True,
        "sheet_sizes_mm": [
            {"width": 2440, "height": 1220},
        ],
        "notes": [
            "Excelente relación resistencia/peso",
            "Buen agarre de tornillo en todas las direcciones",
            "Canto visible puede dejarse natural como detalle de diseño",
            "Más caro pero superior estructuralmente",
        ],
    },
    "solid_pine_20": {
        "name": "Madera maciza pino 20mm",
        "thickness_mm": 20,
        "max_span_no_support_cm": 110,
        "density_kg_m3": 500,
        "screw_holding": "high",
        "moisture_resistance": "medium",
        "finish": "Requiere sellador + barniz o pintura",
        "edge_banding": False,
        "sheet_sizes_mm": [],
        "available_widths_cm": [10, 15, 20, 25, 30],
        "available_lengths_cm": [240, 300],
        "notes": [
            "No viene en tableros — se compra por tabla y se lamina",
            "Excelente agarre de tornillo",
            "Se deforma con humedad — necesita buen secado y sellado",
            "Para tableros anchos, laminar varias tablas con prensa",
        ],
    },
}
