"""Structural rules for furniture design.

These rules prevent common failures: sagging shelves, wobbly cabinets,
racking under load, and material failure at joints.
"""

STRUCTURAL_RULES: list[dict] = [
    {
        "id": "back_panel_required",
        "rule": "Todo mueble debe tener respaldo (back panel)",
        "severity": "error",
        "description": (
            "El respaldo (MDF 3mm mínimo, 6mm recomendado) es la pieza que "
            "cuadra el mueble y evita que se deforme en rombo. Sin respaldo, "
            "el mueble se rackea (inclina lateralmente)."
        ),
        "fix": "Agregar panel trasero de MDF 3mm embutido en canal o clavado por detrás.",
        "check": "spec must have a part with role='back'",
    },
    {
        "id": "max_span_check",
        "rule": "Ningún estante debe exceder el tramo libre máximo del material",
        "severity": "error",
        "description": (
            "Un estante horizontal sin soporte intermedio se pandea (curva) con "
            "el tiempo bajo carga. El tramo máximo depende del material y espesor."
        ),
        "fix": "Agregar división vertical intermedia o listón de refuerzo bajo el estante.",
        "check": "shelf width <= material.max_span_no_support_cm",
    },
    {
        "id": "cross_rails_wide",
        "rule": "Muebles de más de 60cm de ancho necesitan travesaños",
        "severity": "error",
        "description": (
            "Sin travesaños horizontales (rails) en la parte superior y/o inferior, "
            "los laterales tienden a abrirse. Mínimo un travesaño trasero superior "
            "y uno inferior."
        ),
        "fix": "Agregar travesaños de 8-10cm de alto, mismo material que la estructura.",
        "check": "if width > 60: spec must have parts with role='rail'",
    },
    {
        "id": "vertical_divider_wide",
        "rule": "Secciones de más de 90cm de ancho necesitan división vertical",
        "severity": "error",
        "description": (
            "Un tramo de más de 90cm sin división vertical hará que las repisas "
            "se pandeen aunque el material lo soporte, porque la carga nunca "
            "es uniforme."
        ),
        "fix": "Agregar panel vertical intermedio (mismo material y espesor que laterales).",
        "check": "each section width <= 90cm",
    },
    {
        "id": "kickplate_floor_cabinet",
        "rule": "Gabinetes de piso deben tener zócalo o patas",
        "severity": "warning",
        "description": (
            "El zócalo protege la base del mueble de golpes y humedad del piso. "
            "Debe estar retranqueado 3-5cm del frente para que los pies no "
            "choquen al pararse frente al mueble."
        ),
        "fix": "Agregar zócalo de 10cm retranqueado 5cm, o patas ajustables.",
        "check": "if floor_standing: spec should have kickplate or legs",
    },
    {
        "id": "shelf_reinforcement",
        "rule": "Estantes de más de 80cm necesitan refuerzo anti-pandeo",
        "severity": "warning",
        "description": (
            "Incluso dentro del tramo libre máximo, estantes largos se benefician "
            "de un listón de refuerzo (hardwood strip) en el borde frontal o trasero. "
            "Esto triplica la resistencia al pandeo."
        ),
        "fix": "Agregar listón de 2x4cm en el borde trasero o frontal del estante.",
        "check": "if shelf_width > 80: should have reinforcement",
    },
    {
        "id": "tall_furniture_anchoring",
        "rule": "Muebles de más de 180cm de alto deben tener amarre superior",
        "severity": "warning",
        "description": (
            "Muebles altos pueden volcarse, especialmente closets y libreros. "
            "Necesitan un travesaño superior de amarre y/o anclaje a pared."
        ),
        "fix": "Agregar travesaño superior y escuadra de anclaje a pared.",
        "check": "if height > 180: should have top rail and wall anchor note",
    },
    {
        "id": "confirmat_edge_distance",
        "rule": "Tornillos confirmat a mínimo 5cm del borde del panel",
        "severity": "warning",
        "description": (
            "Si se atornilla muy cerca del borde, la melamina/MDF se fisura. "
            "Mínimo 5cm del borde y pre-taladrado siempre."
        ),
        "fix": "Verificar que todas las uniones tengan mínimo 5cm de distancia al borde.",
        "check": "all joint positions >= 5cm from panel edge",
    },
    {
        "id": "confirmat_spacing",
        "rule": "Espaciado máximo de 25cm entre tornillos confirmat",
        "severity": "warning",
        "description": (
            "Para uniones largas (como un piso de 60cm), los confirmats deben "
            "espaciarse cada 20-25cm para distribuir la carga uniformemente."
        ),
        "fix": "Distribuir confirmats cada 20-25cm a lo largo de la unión.",
        "check": "confirmat spacing <= 25cm along each joint",
    },
    {
        "id": "floor_panel_load_bearing",
        "rule": "Piso del mueble debe ser del mismo espesor que laterales si porta carga",
        "severity": "warning",
        "description": (
            "Un piso de material delgado (9mm, 12mm) no soporta peso. Si el "
            "mueble va sobre el piso y porta carga, el panel inferior debe ser "
            "del mismo espesor que la estructura (16-18mm)."
        ),
        "fix": "Usar mismo material y espesor que los laterales para el piso.",
        "check": "floor panel thickness >= side panel thickness",
    },
]
