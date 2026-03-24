"""Hardware catalog with selection rules for furniture design.

Quantities and placement rules follow standard cabinet-making practice.
"""

HARDWARE_CATALOG: dict = {
    "hinges": {
        "name": "Bisagras",
        "types": [
            {
                "id": "hinge_35mm_soft_close",
                "name": "Bisagra cazoleta 35mm con cierre suave",
                "cup_diameter_mm": 35,
                "cup_depth_mm": 12,
                "opening_angle": 110,
                "overlay": "full",
                "description": "Bisagra estándar para puertas overlay (que cubren el lateral).",
            },
            {
                "id": "hinge_35mm_half_overlay",
                "name": "Bisagra cazoleta 35mm media cubierta",
                "cup_diameter_mm": 35,
                "cup_depth_mm": 12,
                "opening_angle": 110,
                "overlay": "half",
                "description": "Para puertas que comparten un lateral central.",
            },
            {
                "id": "hinge_35mm_inset",
                "name": "Bisagra cazoleta 35mm embutida",
                "cup_diameter_mm": 35,
                "cup_depth_mm": 12,
                "opening_angle": 110,
                "overlay": "inset",
                "description": "Puerta queda al ras con el lateral (estilo europeo).",
            },
            {
                "id": "hinge_170_corner",
                "name": "Bisagra 170° para esquinero",
                "cup_diameter_mm": 35,
                "opening_angle": 170,
                "description": "Para gabinetes esquineros — permite abrir la puerta casi plana.",
            },
        ],
        "quantity_rules": [
            {"door_height_max_cm": 60, "quantity": 2},
            {"door_height_max_cm": 120, "quantity": 3},
            {"door_height_max_cm": 180, "quantity": 4},
            {"door_height_max_cm": 240, "quantity": 5},
        ],
        "placement_rules": {
            "distance_from_top_cm": 10,
            "distance_from_bottom_cm": 10,
            "cup_distance_from_edge_mm": 22,
            "note": "La cazoleta se perfora a 22mm del borde de la puerta (centro del orificio de 35mm).",
        },
    },
    "slides": {
        "name": "Correderas para cajones",
        "types": [
            {
                "id": "slide_full_extension",
                "name": "Corredera telescópica extensión completa",
                "extension": "100%",
                "load_capacity_kg": 35,
                "available_lengths_cm": [25, 30, 35, 40, 45, 50],
                "description": "Permite sacar el cajón completamente. Estándar para cocinas.",
            },
            {
                "id": "slide_3_4_extension",
                "name": "Corredera extensión 3/4",
                "extension": "75%",
                "load_capacity_kg": 25,
                "available_lengths_cm": [25, 30, 35, 40, 45, 50],
                "description": "Más económica. Suficiente para recámaras y oficinas.",
            },
            {
                "id": "slide_soft_close",
                "name": "Corredera extensión completa con cierre suave",
                "extension": "100%",
                "load_capacity_kg": 40,
                "available_lengths_cm": [30, 35, 40, 45, 50],
                "description": "Premium. Cierre automático suave.",
            },
            {
                "id": "slide_undermount",
                "name": "Corredera de piso (undermount)",
                "extension": "100%",
                "load_capacity_kg": 50,
                "available_lengths_cm": [30, 35, 40, 45, 50],
                "description": "Se monta debajo del cajón. Invisible. Requiere cajón con fondo.",
            },
        ],
        "selection_rules": {
            "kitchen": "slide_full_extension o slide_soft_close",
            "bedroom": "slide_3_4_extension (suficiente para ropa)",
            "heavy_load": "slide_undermount (herramientas, archivos)",
        },
        "mounting_rules": {
            "clearance_each_side_mm": 12.7,
            "note": "El cajón debe ser 25.4mm (1 pulgada) más angosto que el hueco, para dejar 12.7mm por lado para la corredera.",
        },
    },
    "connectors": {
        "name": "Conectores y tornillería",
        "types": [
            {
                "id": "confirmat_7x50",
                "name": "Tornillo confirmat 7x50mm",
                "pilot_hole_mm": 5,
                "description": "Tornillo estándar para unir paneles de melamina/MDF. Pre-taladrar siempre con broca de 5mm.",
                "usage": "Uniones de lateral a piso, lateral a techo, etc.",
            },
            {
                "id": "minifix",
                "name": "Conector minifix (excéntrica)",
                "hole_diameter_mm": 15,
                "bolt_hole_mm": 8,
                "description": "Unión invisible y desmontable. Se ve solo un tapón plástico.",
                "usage": "Muebles desarmables, uniones de exhibición.",
            },
            {
                "id": "wooden_dowel_8x35",
                "name": "Tarugos de madera 8x35mm",
                "diameter_mm": 8,
                "length_mm": 35,
                "hole_depth_mm": 18,
                "description": "Para alineación de paneles. Siempre usar con pegamento.",
                "usage": "Complemento de confirmats o minifix para alinear piezas.",
            },
            {
                "id": "cam_bolt",
                "name": "Perno de excéntrica",
                "description": "Parte macho del sistema minifix. Se atornilla en un panel.",
                "usage": "Se usa en combinación con el minifix.",
            },
        ],
        "spacing_rules": {
            "confirmat_min_from_edge_cm": 5,
            "confirmat_max_spacing_cm": 25,
            "confirmat_min_spacing_cm": 10,
            "dowels_per_joint": "2-3 tarugos por unión, espaciados uniformemente",
        },
    },
    "shelf_pins": {
        "name": "Soportes de repisa",
        "types": [
            {
                "id": "shelf_pin_5mm",
                "name": "Perno de repisa 5mm",
                "hole_diameter_mm": 5,
                "hole_depth_mm": 10,
                "description": "Pin metálico o plástico para repisas ajustables.",
            },
            {
                "id": "shelf_pin_with_rubber",
                "name": "Perno de repisa 5mm con goma",
                "hole_diameter_mm": 5,
                "description": "Con almohadilla de goma para que la repisa no resbale.",
            },
        ],
        "placement_rules": {
            "pins_per_shelf": 4,
            "distance_from_front_cm": 3,
            "distance_from_back_cm": 3,
            "vertical_hole_spacing_cm": 3.2,
            "note": "Perforar columna de agujeros cada 3.2cm (sistema 32mm) en cada lateral, a 3cm del borde frontal y trasero.",
        },
    },
}
