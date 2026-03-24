"""Ergonomic standards for furniture design.

All dimensions in centimeters unless noted otherwise.
Sources: ANSI/BIFMA, Architectural Graphic Standards, common
cabinet-making practice in Latin America.
"""

ERGONOMIC_STANDARDS: dict = {
    "kitchen_base": {
        "name": "Gabinete base de cocina",
        "height": {"min": 85, "max": 92, "default": 90, "note": "Incluye zócalo de 10cm"},
        "depth": {"min": 55, "max": 65, "default": 60},
        "width": {"min": 30, "max": 120, "default": 60},
        "kickplate_height": {"min": 8, "max": 15, "default": 10},
        "countertop_thickness": {"min": 2, "max": 5, "default": 3},
        "countertop_overhang_front": 2,
        "setback_from_wall": 2,
        "notes": [
            "Altura total con cubierta: 90-92cm",
            "El cuerpo del gabinete mide altura - zócalo - cubierta",
            "Cajón superior estándar: 15-20cm de altura útil",
            "Espacio entre base y mueble de pared: 45-55cm",
        ],
    },
    "kitchen_wall": {
        "name": "Gabinete de pared / aéreo de cocina",
        "height": {"min": 30, "max": 90, "default": 70},
        "depth": {"min": 28, "max": 38, "default": 33},
        "width": {"min": 30, "max": 120, "default": 60},
        "bottom_clearance_from_floor": {"min": 140, "max": 150, "default": 145},
        "top_clearance_from_floor": {"max": 220, "note": "Alcance cómodo sin banco"},
        "notes": [
            "El borde inferior queda a 145cm del piso (55cm sobre cubierta)",
            "Profundidad menor que base para no golpearse la cabeza",
            "Repisas internas cada 25-30cm de altura",
        ],
    },
    "closet": {
        "name": "Closet / armario",
        "height": {"min": 200, "max": 260, "default": 240},
        "depth": {"min": 55, "max": 65, "default": 60},
        "width": {"min": 80, "max": 300, "default": 180},
        "hanging_rod_high": {"default": 180, "note": "Ropa larga: abrigos, vestidos"},
        "hanging_rod_mid": {"default": 120, "note": "Ropa corta: camisas, sacos"},
        "hanging_rod_double_upper": {"default": 170},
        "hanging_rod_double_lower": {"default": 85},
        "shelf_spacing": {"min": 25, "max": 40, "default": 30},
        "drawer_height": {"min": 12, "max": 25, "default": 18},
        "notes": [
            "Profundidad de 60cm para ganchos estándar (45cm útil + holgura)",
            "Sección de doble barra para camisas: 85cm y 170cm",
            "Zapatero: repisas inclinadas cada 15-20cm",
            "Cajones de ropa interior: 12-15cm de altura",
        ],
    },
    "bookshelf": {
        "name": "Librero / estantería",
        "height": {"min": 80, "max": 240, "default": 180},
        "depth": {"min": 22, "max": 35, "default": 28},
        "width": {"min": 40, "max": 120, "default": 80},
        "shelf_spacing": {"min": 25, "max": 35, "default": 30},
        "notes": [
            "Libros estándar: 25cm entre repisas",
            "Libros grandes / arte: 35cm entre repisas",
            "Profundidad de 28cm es suficiente para la mayoría de libros",
            "Si supera 180cm de alto, anclar a pared por seguridad",
        ],
    },
    "desk": {
        "name": "Escritorio",
        "height": {"min": 72, "max": 78, "default": 75},
        "depth": {"min": 50, "max": 80, "default": 60},
        "width": {"min": 80, "max": 180, "default": 120},
        "leg_clearance_height": {"min": 60, "note": "Espacio libre para rodillas"},
        "leg_clearance_width": {"min": 50, "note": "Espacio libre para piernas"},
        "keyboard_tray_height": {"default": 65, "note": "6-8cm debajo de superficie"},
        "notes": [
            "Superficie a 75cm del piso es el estándar ergonómico",
            "Monitor a 50-70cm de los ojos, borde superior al nivel de ojos",
            "Espacio para rodillas mínimo 60cm de alto x 50cm de ancho",
        ],
    },
    "vanity": {
        "name": "Vanitorio / mueble de baño",
        "height": {"min": 80, "max": 90, "default": 85},
        "depth": {"min": 45, "max": 55, "default": 50},
        "width": {"min": 40, "max": 120, "default": 80},
        "mirror_bottom_clearance": {"default": 105, "note": "Desde el piso"},
        "notes": [
            "Considerar la altura del lavabo empotrado (15-20cm)",
            "Material resistente a humedad (melamina, MDF hidrófugo)",
            "Verificar paso de tuberías en el diseño del respaldo",
        ],
    },
    "general": {
        "name": "Reglas generales",
        "standard_sheet_sizes_cm": [
            {"width": 244, "height": 122, "note": "4x8 pies — más común"},
            {"width": 183, "height": 244, "note": "6x8 pies"},
        ],
        "common_thicknesses_mm": [9, 12, 15, 16, 18, 25],
        "edge_banding_mm": [0.4, 1, 2],
        "notes": [
            "Tableros de 16mm y 18mm son los más usados para estructura",
            "9mm y 12mm para fondos y respaldos",
            "Cantos de 2mm PVC para bordes visibles, 0.4mm para no visibles",
        ],
    },
}
