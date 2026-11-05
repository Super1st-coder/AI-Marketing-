"""Mock Sinergia data for local development.

Activate by setting USE_MOCK_SINERGIA=true in your .env file.
The mock uses real-shaped data from adset 295 (Nike Total 90 retro soccer campaign).

Usage:
    # .env
    USE_MOCK_SINERGIA=true

These mocks replace campaign_tools.py functions so the full ADK pipeline can run
locally without a running Sinergia instance.
"""

from typing import Any
import itertools
import json


# ---------------------------------------------------------------------------
# Mock payloads  (real-shaped data from adset 295 — Total 90 retro campaign)
# ---------------------------------------------------------------------------

_MOCK_ADSET = {
    "ok": True,
    "adset": {
        "data": {
        "id": 173,
        "name": "Ad Set 1",
        "audience": {
            "name": "Hombres élite SUV híbrida CDMX",
            "description": "Hombres en CDMX con alto poder adquisitivo interesados en camionetas híbridas y SUVs modernas con estilo y tecnología avanzada.",
            "gender": "Male",
            "age": [
                "35-44",
                "45-54"
            ],
            "income": "High-income, enjoying premium lifestyles.",
            "location": [
                "Ciudad de México",
                "Del Valle Centro"
            ],
            "interests": [
                "Automóviles híbridos",
                "Automóviles",
                "SUV",
                "Vehículos",
                "Compra de auto",
                "Artículos de lujo",
                "Viajes",
                "Familia"
            ]
        },
        "creative_angle": {
            "type": "static",
            "name": "The \"Power Move\" Action",
            "description": "Freezing the moment of peak performance or mastery enabled by the product.\n\nE.g.,: \"A golfer at the exact moment of a perfect swing drive.\""
        },
        "campaign": {
            "name": "Tiggo 8 Pro: Para Todos tus Mundos",
            "language": "Spanish",
            # Umbrella "Big Idea" section — the creative heart (N0) SHARED across every ad.
            # Shape mirrors the REAL Sinergia /adset/{id} umbrella payload (per Luis):
            # user-selected `title`/`description` + a consolidated `summary` (the canonical,
            # internally-consistent thread the Phase-A step anchors ads to; we read `summary`).
            # Ref: Arquitectura del Módulo Ads Assembly — v2, §6 (umbrella thread) + §10.
            "umbrella": {
                "title": "Para Todos tus Mundos",
                "description": "🌆 Ana y Enrique equilibran mil roles cada día y sienten que ningún SUV está hecho para todos ellos a la vez.\n🚗 Cada compromiso —espacio o tecnología, precio o seguridad— les recuerda que aún no encuentran el auto que viva a su ritmo.",
                "summary": {
                    "hero_story": "🏙️ Ana y Enrique son una familia urbana de CDMX que se mueve entre el trabajo, la escuela y los viajes de fin de semana.\n🚸 Buscan un SUV que acompañe cada faceta de su vida sin pedirles renunciar a nada.\n✨ En el fondo, quieren un auto que se sienta hecho para todos sus mundos.",
                    "customer_reality": "💸 Comparan SUVs por meses y siempre topan con el mismo muro: o espacio, o tecnología, o precio.\n🔍 Investigan en línea y en concesionarios, pero cada opción les pide sacrificar algo importante.\n🚦 Avanzan con dudas, sintiendo que ninguna camioneta cubre de verdad su vida multifacética.",
                    "emotional_conflict": "😟 Temen pagar de más por un SUV premium o quedarse cortos con uno accesible.\n🔄 Quieren tecnología y seguridad de punta sin renunciar al espacio para 7 pasajeros.\n🤯 La tensión: sienten que deben elegir entre sus mundos en lugar de tenerlos todos.",
                    "concept_reality_resonance": "🚙 El Tiggo 8 Pro se presenta como el SUV que se adapta a cada escenario mexicano de su vida.\n💡 Su espacio para 7, motor turbo y conectividad total responden justo a los compromisos que temían.\n📐 La promesa 'Para Todos tus Mundos' resuena con su necesidad de un solo auto para todo.",
                    "customer_journey": "🗺️ Del primer video en redes a la prueba de manejo, descubren un SUV que encaja en cada faceta.\n🧭 Cada característica confirma que no tienen que elegir entre espacio, tecnología o precio.\n🚀 Con el tiempo el Tiggo 8 Pro se vuelve el aliado que vive a su ritmo.",
                    "solution": "✅ El Tiggo 8 Pro resuelve el dilema: 7 pasajeros, motor turbo de 183 HP, garantía de 10 años y conectividad total, a un precio accesible.\n🤝 Un solo SUV que acompaña todos sus mundos sin sacrificios.",
                    "big_idea": "Para Todos tus Mundos — un solo SUV que se transforma para cada rol, escenario y momento de Ana y Enrique, sin pedirles renunciar a nada.",
                    "core_message": "El Tiggo 8 Pro es el único SUV que equilibra espacio, tecnología y precio para acompañarte en todos tus mundos.",
                    "hook": "¿Y si un solo auto pudiera con todos tus mundos?",
                },
            },
            "preferred_campaign": {
                "id": 0,
                "campaign": {
                    "title": "Explora Todos tus Mundos"
                },
                "sections": {
                    "cta": {
                        "text": "¡Conoce el SUV que se adapta a todos tus mundos!",
                        "title": "CTA"
                    },
                    "budget": {
                        "text": "💰💰 😰",
                        "title": "Budget & Effort"
                    },
                    "funnel_flow": {
                        "text": "🎥 Videos IG para Visibilidad → 🌐 Landing con Galería y Comentarios → 🔗 Compartir Hashtag para Engagement",
                        "title": "Funnel Flow – Path to Reach Goals"
                    },
                    "creative_types": {
                        "text": "🎥 Videos de IG, 📸 Fotos Interactivas, 🗨️ Comentarios de Usuarios, 🔗 Compartir con Hashtag",
                        "title": "Creative Types"
                    },
                    "execution_steps": {
                        "text": "- Graba videos de IG en locaciones icónicas\n- Diseña landing con galería interactiva\n- Activa sección de comentarios\n- Crea CTA para compartir con hashtag",
                        "title": "Execution Steps"
                    },
                    "campaign_details": {
                        "text": "Esta campaña posiciona al Tiggo 8 Pro como el SUV ideal para familias modernas en México. La narrativa se enfoca en la elegancia y funcionalidad de su diseño, su capacidad para siete pasajeros, y su conectividad tecnológica, presentado a través de locaciones como playas, ciudades coloniales y zonas arqueológicas, familiar para el mercado mexicano.",
                        "title": "Campaign Details"
                    },
                    "short_description": {
                        "text": "Muestra la versatilidad del Tiggo 8 Pro en escenarios mexicanos icónicos, generando interacción y resonancia cultural.",
                        "title": "Short Description"
                    }
                },
                "preferred": 1
            },
            "summary": {
                "bperson": {
                    "persona_journey": "🚗 Exploran opciones a través de visitas y pruebas en concesionarios locales para experiencia tangible.\n📈 Investigan en línea, valorando las reseñas y experiencias de otros usuarios sobre el Tiggo 8 Pro.\n📱 La decisión final se ve influenciada por recomendaciones de amigos y familiares de confianza.\n🔑 Finalmente, eligen un vehículo que equilibra tecnología, espacio y precio—elementos claves para su elección.",
                    "persona_profile": "🌆 Ana y Enrique residen en áreas urbanas de México, buscando vehículos que se adapten a su estilo de vida activo.\n👨‍👩‍👧‍👦 Buscan espacio para toda la familia, priorizando la comodidad y capacidad para 7 pasajeros.\n🏢 Sus profesiones demandan tecnología avanzada para mantenerse conectados mientras se desplazan.\n🎨 Son culturalmente ricos, valorando un diseño que hable de buen gusto y funcionalidad.",
                    "persona_challenges": "💸 Encuentran altos los costos de SUV tradicionales, lo que complica encontrar un vehículo accesible.\n🔍 No hay muchas opciones disponibles con garantía extendida, lo que aumenta sus preocupaciones.\n🚫 Faltan opciones de SUV con tercera fila de asientos que no comprometan otros aspectos importantes.\n🏃‍♂️ Se adaptan a soluciones actuales enfocándose en aplicaciones y herramientas tecnológicas.",
                    "persona_motivation": "🔄 Ana y Enrique desean un vehículo que se adapte a sus múltiples roles y responsabilidades diarias.\n🌟 Valoran la sofisticación que se completa con características avanzadas y seguridad mejorada.\n🌿 Buscan la paz mental que ofrece un coche confiable sin comprometer sus valores y estilo.\n🎯 La motivación final es la movilidad inteligente que se alinea con sus aspiraciones familiares."
                },
                "product": {
                    "core_incentive_offer": "🚙 Ofrece un SUV que combina espacio funcional y elegante, adecuado para estilos de vida múltiples.\n🔍 Centra su comunicación en el balance entre coste accesible y características premium.\n🔑 Condiciones claras de venta resaltan garantía y valor a largo plazo.\n📜 El mensaje invita a experimentar el Tiggo 8 Pro como símbolo de movilidad integral.",
                    "problem_solution_fit": "🔧 Aborda costos elevados sin comprometer el espacio o la tecnología.\n💬 Responde a la falta de garantías extendidas con ofertas y soporte postventa.\n🚀 Demuestra adaptabilidad a la vida multifacética de Ana y Enrique, integrándose sin esfuerzo.\n🎨 Atrae con diseño moderno que resuena con el gusto por lo sofisticado pero accesible.",
                    "emotional_outcome_payoff": "❤️ La campaña establece una conexión emocional al mostrar que la innovación acompaña al usuario.\n🌟 Refuerza la confianza en el Tiggo 8 Pro como elección que cuida y asombra.\n😊 Proporciona satisfacción al resolver necesidades reales con soluciones prácticas.\n🔄 Genera lealtad y preferencia continua hacia la marca mediante experiencias positivas.",
                    "unique_value_proposition": "🌐 El Tiggo 8 Pro equilibra diseño, espacio y tecnología, destacándose entre opciones tradicionales.\n💡 Ofrece un paquete de beneficios que aborda todas las etapas de la vida familiar.\n🚗 Su propuesta se define por un precio competitivo sin escatimar en funciones esenciales.\n🔋 La confiabilidad del producto refuerza la percepción de una inversión inteligente."
                },
                "campaign": {
                    "campaign_kpis": "Paid Social\n-Cost per visitor: 20 $ cost per visitor",
                    "campaign_goals": "Paid Social\n-Reach: 500000  Total Reach\n-Site Visits: 20000  Total Site Visits",
                    "campaign_resources": "Paid Social\n-Ad Budget: 50000 $ Total Budget\n-Production Budget: 20000 $ Total Production Budget",
                    "campaign_concept_timing": "🎥 Concepto centrado en versatilidad del Tiggo 8 Pro en icónicos escenarios mexicanos; muestra adaptabilidad.\n🍂 Lanzamiento en otoño aprovecha el cambio de temporada para resaltar su comodidad y espacio.\n🏺 La narrativa abraza herencia cultural mexicana, reflejando autenticidad y resonancia local.\n⏳ Entre octubre y diciembre de 2025, optimizando la relevancia cultural y efecto estacional."
                }
            },
            "product_details": {
                "benefits": [
                    "Interior amplio con capacidad para 7 pasajeros",
                    "Tecnología avanzada con conectividad completa",
                    "Seguridad mejorada con sistemas ADAS"
                ],
                "features": [],
                "keywords": [],
                "warranties": [],
                "value_proposition": [],
                "competitive_advantage": []
            },
            "bperson_details": {
                "hometown": [],
                "age_range": [],
                "pain_points": [
                    "Costos de SUV tradicionales son muy altos.",
                    "No hay garantía extendida disponible.",
                    "Falta SUV con tercera fila de asientos."
                ],
                "customer_goal": [],
                "fears_and_worries": [],
                "name_and_nickname": [],
                "how_they_solve_it_now": [],
                "income_level_brackets": [],
                "barriers_to_making_a_change": [],
                "problem_with_current_solution": []
            }
        },
        "brand": {
            "id": 69,
            "name": "Chirey",
            "identity": {
                "values": {
                    "value": [],
                    "source": []
                },
                "vision": {
                    "value": "",
                    "source": []
                },
                "mission": {
                    "value": "",
                    "source": []
                },
                "about_us": {
                    "value": "",
                    "source": []
                },
                "tone_voice": {
                    "value": [],
                    "source": []
                }
            },
            "logos": [],
            "colors": [],
            "typography": [],
            "dos_donts": [],
            "website": "https://www.chirey.mx/"
        },
        "buyer": {
            "id": 103,
            "name": "Ana y Enrique, los Guardianes del Estilo",
            "story": "Ana y Enrique viven la realidad de muchas familias urbanas en CDMX, buscando un equilibrio entre confort, seguridad y eficiencia para sus trayectos diarios. Quieren un vehículo que les permita viajar cómodamente en familia y les ofrezca las últimas tecnologías de seguridad. Sin embargo, las alternativas actuales presentan desafíos como precios elevados y la falta de características avanzadas, como motores turbo potentes y garantías extendidas. En su proceso de búsqueda, han recurrido a investigar SUVs en línea, consultar foros, y comparar opciones en los concesionarios, pero la frustración persiste ante compromisos inevitables.\n\nEn su camino, Ana y Enrique enfrentan diversas barreras emocionales y financieras. Dudas sobre el rendimiento de nuevas tecnologías, el miedo a costos de mantenimiento desconocidos, y el temor a devaluaciones futuras frenan su decisión. Al mismo tiempo, la carencia de modelos con tercera fila y acabados premium agravan su dilema. A pesar de estas dificultades, su compromiso emocional con su SUV actual los mantiene en un mar de indecisiones, aumentando su frustración y manteniéndolos en un ciclo que parece no tener fin.\n\nSin embargo, un destello de esperanza surge con la llegada del Tiggo 8 Pro, que promete romper con estas restricciones. Con su motor turbo de 183 HP, una garantía de 10 años, y un interior espacioso para siete pasajeros, parece ser la SUV perfecta para ellos. La conectividad total y la seguridad avanzadas de esta SUV ofrecen lo que ninguna otra opción ha logrado. A medida que evalúan esta nueva oportunidad, la posibilidad de dar un paso hacia un futuro con libertad y satisfacción en cada viaje se vislumbra. ¿Se atreverán Ana y Enrique a tomar esta decisión, dejando atrás lo familiar para abrazar un cambio positivo?",
            "attributes": {
                "hometown": [
                    "Ciudad de México | Del Valle Centro | Media"
                ],
                "age_range": [
                    "35-44",
                    "45-54"
                ],
                "pain_points": [
                    "Costos de SUV tradicionales son muy altos.",
                    "No hay garantía extendida disponible.",
                    "Falta SUV con tercera fila de asientos.",
                    "Opciones limitadas en el mercado local.",
                    "Sacrificio de acabados premium en SUV."
                ],
                "customer_goal": [
                    "Transportar cómodamente a su familia extendida en viajes y traslados diarios.",
                    "Asegurar la máxima seguridad con tecnologías ADAS avanzadas.",
                    "Facilitar traslados escolares eficientemente y sin las limitaciones e incomodidad de un coche pequeño e incómodo.",
                    "Garantizar visibilidad plena con visión panorámica 360°."
                ],
                "fears_and_worries": [
                    "Inseguridad de protección infantil.",
                    "Fallos en tecnología vehicular.",
                    "Costos inesperados en el futuro.",
                    "Pérdida de inversión si cambia el modelo."
                ],
                "name_and_nickname": [
                    "Ana y Enrique, los Guardianes del Estilo"
                ],
                "how_they_solve_it_now": [
                    "Investigación de modelos SUV en internet.",
                    "Consulta de experiencias en foros online.",
                    "Uso de préstamos para financiamiento.",
                    "Comparación de precios en concesionarios."
                ],
                "income_level_brackets": [
                    "Finanzas equilibradas, gustos ocasionales."
                ],
                "barriers_to_making_a_change": [
                    "Arriesgarse a adoptar nueva tecnología.",
                    "Dudas sobre rendimiento a largo plazo.",
                    "Compromiso emocional con SUV actual.",
                    "Temor en costos ocultos de mantenimiento.",
                    "Preocupaciones sobre la devaluación.",
                    "Problemas de refacciones"
                ],
                "problem_with_current_solution": [
                    "SUV supera fácil los 700 mil pesos.",
                    "No integra motor turbo potente.",
                    "Opciones tradicionales no tienen ADAS.",
                    "Garantía extendida es inexistente."
                ]
            }
        },
        "product": {
            "id": 114,
            "name": "Tiggo 8 Pro",
            "description": "🔧 Ficha Técnica — Chirey Tiggo 8 Pro (México)\nInformación General\nMarca / Modelo: Chirey Tiggo 8 Pro (también conocido como Tiggo 8 Pro Max en algunos mercados).\n\nAño del Modelo: 2025 (actualización recientemente incorporada en México).\n\n\nSegmento / Tipo de SUV: SUV mediana (segmento D), 7 plazas, ideal para familias urbanas.\n\n\nMotorización y Tren Motriz\nMotor: 1.6 L Turbo (1,598 cc)\n\n\nPotencia: 183 HP @ 5,500 rpm\n\n\nTorque máximo: 202 lb-ft (≈ 275 Nm) @ 2,000–4,000 rpm\n\n\nTransmisión: DCT de 7 velocidades con palanca e-shift\n\n\nTracción: Delantera (Luxury); AWD opcional (Premium Max).\n\n\nRendimiento\nCombustible: Gasolina de 91 octanos\n\n\nRendimiento (km/L): Ciudad: 12.97 – Carretera: 17.68 – Combinado: 14.73 .\nDimensiones y Capacidades\nLargo: 4,722 mm | Ancho: 1,860 mm | Alto: ~1,705 mm\n\n\nDistancia entre ejes: 2,710 mm\n\n\nCapacidad de tanque: 51 litros\n\n\nCapacidad de cajuela:\n\n\n7 plazas activas: 889 L\n\n\nAsientos abatidos (segunda y tercera fila): hasta 1,930 L.\n\n\nNeumáticos: 235/55 R18 con rines de aluminio de 18″\n\n\nSuspensión: Delantera McPherson; trasera independiente multibrazo; dirección eléctrica asistida.\n\n\nSeguridad y ADAS\nAirbags: 2 frontales, 2 laterales, 2 tipo cortina (6 en total)\n\n\nFrenos: ABS + EBD, frenos de disco ventilado delante y sólidos atrás, EPB con Auto Hold\n\n\nAsistencias de seguridad: ESP, BAS, EBA, HAC, HDC, TPMS, bloqueo infantil, recordatorio de cinturón.\n\n\nADAS (versión Premium):\n\n\nLDW – Advertencia de abandono de carril\n\n\nDOW – Alerta de puerta trasera abierta\n\n\nRCTA – Alerta de tráfico cruzado posterior\n\n\nICA / ACC – Asistente de crucero inteligente / adaptativo\n\n\nLKA – Asistencia de mantenimiento de carril\n\n\nTJA – Asistencia en tráfico pesado\n\n\nBSD – Detector de punto ciego\n\n\nAEB – Frenado autónomo de emergencia\n\n\nRCW – Advertencia de colisión trasera.\n\n\nEquipamiento Exterior\nIluminación: Faros LED automáticos, DRL, luz de niebla, luces traseras LED en “T”\n\n\nEspejos laterales: Color carrocería, calefactables, direccionales; plegables eléctricos en versión Premium\n\n\nTecho panorámico: Sí (Premium)\n\n\nCámara 360° HD: Incluye sensores delanteros y traseros\n\n\nElementos estéticos: Parrilla estilizada con acentos cromados, escape doble salida, rieles de techo.\n\n\nInterior y Conectividad\nPantallas: Panel digital + pantalla central 12.3″, pantalla control de A/C de 8″\n\n\nSistema de sonido: 8 bocinas premium\n\n\nConectividad: Android Auto, Apple CarPlay, carga inalámbrica, USB traseros\n\n\nOtras comodidades: Asientos calefactables delanteros, asiento del copiloto eléctrico, control por voz, purificador de aire, cámara 540° en versiones e+.\n\n\nGarantía y Servicios\nGarantía: 10 años o 150,000 km, según primera contingencia\n\n\nPostventa: Red nacional de distribuidores, ensamble parcial local para reducción de costos y mayor disponibilidad de piezas.\n\n\n📌 Esta ficha está diseñada para profesionales de producto o marketing automotriz: clara, funcional y con información confiable basada en fuentes oficiales y especializados en México. Si necesitas versión para el modelo híbrido enchufable (Tiggo 8 Pro e+), o gráfica de equipamiento por versión, con gusto la preparo.\n",
            "story": "En un mundo en constante avance, los conductores enfrentan el desafío de encontrar vehículos que no solo ofrezcan rendimiento, sino también integración tecnológica y seguridad a largo plazo. Chirey identifica estas necesidades y presenta el Tiggo 8 Pro, diseñado para llenar estos vacíos. Con un robusto motor turbo 1.6L de 183 HP, ofrece potencia sin compromisos. Además, equipada con una doble pantalla curva de 24.6” para conectividad completa y una garantía extendida de 10 años, el Tiggo 8 Pro es una inversión inteligente para quienes buscan tecnología avanzada y durabilidad.\n\nEl Tiggo 8 Pro se destaca por características únicas que lo hacen el vehículo ideal para familias modernas. Su motor 1.6L Turbo con transmisión DCT de 7 velocidades garantiza una conducción suave y eficiente. Con capacidad para 7 pasajeros, el interior espacioso y su techo panorámico ofrecen una experiencia de viaje cómoda y lujosa. La tecnología de Apple CarPlay y la cámara 360° proporcionan un control total y seguro. Resaltando el compromiso de Chirey con el cambio significativo, esta SUV combina innovación y confiabilidad para adaptarse a las necesidades del mercado mexicano.\n\nEl impacto del Tiggo 8 Pro es transformador: ofrece un interior amplio, tecnología innovadora para una conectividad avanzada y sistemas ADAS para una conducción segura. Los asientos calefactables añaden un toque de confort, mientras que su eficiente consumo de combustible resulta ideal para viajes familiares. Chirey redefine la experiencia automotriz, fomentando un futuro sostenible y conectado. Con el Tiggo 8 Pro, cada viaje es una oportunidad para avanzar en la misión de Chirey de ofrecer accesibilidad y sostenibilidad junto a una experiencia sin igual.",
            "attributes": {
                "benefits": [
                    "Interior amplio con capacidad para 7 pasajeros",
                    "Tecnología avanzada con conectividad completa",
                    "Seguridad mejorada con sistemas ADAS",
                    "Confort elevado con asientos calefactables",
                    "Eficiencia de combustible ideal para familias"
                ],
                "features": [
                    "Motor 1.6L Turbo de 183 HP",
                    "Transmisión DCT de 7 velocidades",
                    "Asientos para 7 pasajeros con 3 filas",
                    "Pantalla de 12.3\" con Apple CarPlay",
                    "Cámara 360° con sensores avanzados"
                ],
                "keywords": [
                    "SUV mediana",
                    "tiggo 8 pro",
                    "camionetas tiggo"
                ],
                "value_proposition": [
                    "Disfruta de la potencia de un motor turbo 1.6L con 183 HP y control total.",
                    "Experimenta conectividad total con doble pantalla curva de 24.6”.",
                    "Asegura tu inversión con una garantía extendida de 10 años."
                ],
                "competitive_advantage": [
                    "Amplia garantía de 10 años o 150,000 km",
                    "Disfruta de un interior espacioso con tres filas, ideal para familias grandes.",
                    "El techo panorámico da una sensación de amplitud y elegancia única.",
                    "Sistema de sonido premium de 8 bocinas para una experiencia envolvente.",
                    "Pantallas digitales dobles de 24.6” para un control total del vehículo."
                ]
            }
        }
    }
    },
}

_MOCK_BRAND = {
    "ok": True,
    "brand": {
        "data": {
            "id": 43,
            "attributes": {
                "name": "Nike Total 90",
                "tone_of_voice": (
                    "Bold, nostalgic, and community-driven. Speaks to the passion of the game. "
                    "Evokes golden-era football memories with modern energy. Direct and inspiring."
                ),
                "color_palette": [
                    {"name": "Classic White", "hex": "#FFFFFF"},
                    {"name": "Nike Black", "hex": "#111111"},
                    {"name": "Field Green", "hex": "#2E7D32"},
                    {"name": "Gold Accent", "hex": "#FFD600"},
                ],
                "do_donts": [
                    "DO: Highlight the retro football heritage",
                    "DO: Show the product in street/casual context",
                    "DO: Use nostalgia and community language",
                    "DON'T: Use overly technical sports jargon",
                    "DON'T: Show competitor logos or stadiums",
                    "DON'T: Use aggressive or polarizing political content",
                ],
                "visual_restrictions": [
                    "No competitor brand logos",
                    "No real athlete endorsements without contract",
                    "Product must be visible in at least 60% of banner",
                ],
            },
        }
    },
}

_MOCK_AUDIENCES = {
    "ok": True,
    "audiences": {
        "data": [
            {
                "id": 497,
                "attributes": {
                    "name": "Retro Football Lifestyle Males",
                    "gender": "Male",
                    "age": ["25-34"],
                    "income": "High-income, enjoying premium lifestyles.",
                    "location": ["São Paulo, Brazil", "Mexico City, Mexico", "Barcelona, Spain"],
                    "interests": ["Fútbol", "Fitness", "Zapatos", "Ropa de hombre", "Artículos de lujo"],
                    "description": "Men 25–34 in key football cities wanting authentic 2000s-inspired soccer style adapted for daily streetwear use.",
                    "psychographic_insights": (
                        "Nostalgic about the early-2000s football era. Value authenticity and heritage. "
                        "Influenced by community and peer style. Shop online for limited-edition items."
                    ),
                },
            },
            {
                "id": 498,
                "attributes": {
                    "name": "Global Football Lifestyle Seekers",
                    "gender": "All",
                    "age": ["18-24", "25-34"],
                    "income": "Balanced finances, occasional treats.",
                    "location": ["Brazil", "Mexico", "Spain"],
                    "interests": ["Fútbol", "Fitness", "Zapatos", "Compras en internet"],
                    "description": "Broad football and lifestyle audience 18–34 open to sporty casual footwear.",
                    "psychographic_insights": (
                        "Aspire to the football lifestyle without being professional players. "
                        "Follow football culture on social media. Price-conscious but will splurge on iconic items."
                    ),
                },
            },
        ]
    },
}

_MOCK_TEMPLATES = {
  "ok": True,
  "templates": [
  {
    "id": "f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4",
    "name": "Awareness",
    "type": "static",
    "template_id": "f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4",
    "formats": [
      {
        "id": "facebook-post",
        "uid": "75582bab-c355-4375-959d-8fa215d0c7e4",
        "width": 1200,
        "height": 1200,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/3f31bd27-d498-4842-af30-1fa550fa3a12.png"
      },
      {
        "id": "facebook-feed",
        "uid": "9f082e18-ad9d-4d2c-901d-0673b7162e06",
        "width": 1200,
        "height": 628,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/3f31bd27-d498-4842-af30-1fa550fa3a12-facebook-feed.png"
      },
      {
        "id": "instagram-portrait",
        "uid": "fb749874-a87f-44f7-8898-da186d119cdd",
        "width": 1080,
        "height": 1350,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/3f31bd27-d498-4842-af30-1fa550fa3a12-instagram-portrait.png"
      },
      {
        "id": "instagram-story",
        "uid": "df86bfc9-1d83-41e4-af2f-33fd634b6a00",
        "width": 1080,
        "height": 1920,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/3f31bd27-d498-4842-af30-1fa550fa3a12-instagram-story.png"
      }
    ],
    "elements": [
      {
        "name": "root",
        "type": "container",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "background_color",
            "help": "6 or 8 digits hexadecimal background color (i.e. #F3F3F3) of the banner ",
            "values": {
              "facebook-post": "#FFFFFF",
              "facebook-feed": "#FFFFFF",
              "instagram-portrait": "#FFFFFF",
              "instagram-story": "#FFFFFF"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 0,
            "y": 0,
            "width": 1200,
            "height": 1200
          },
          "facebook-feed": {
            "x": 0,
            "y": 0,
            "width": 1200,
            "height": 628
          },
          "instagram-portrait": {
            "x": 0,
            "y": 0,
            "width": 1080,
            "height": 1350
          },
          "instagram-story": {
            "x": 0,
            "y": 0,
            "width": 1080,
            "height": 1920
          }
        }
      },
      {
        "name": "background",
        "type": "image",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "image_url",
            "help": "Public HTTP(s) URL of the image (i.e. https://photo.com/image.png)",
            "values": {
              "facebook-post": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_a1296d7d-b9c5-4058-8f0e-7a745bde840e.png",
              "facebook-feed": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_a1296d7d-b9c5-4058-8f0e-7a745bde840e.png",
              "instagram-portrait": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_a1296d7d-b9c5-4058-8f0e-7a745bde840e.png",
              "instagram-story": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_a1296d7d-b9c5-4058-8f0e-7a745bde840e.png"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": -5,
            "y": -5,
            "width": 1210,
            "height": 1210
          },
          "facebook-feed": {
            "x": 0,
            "y": 0,
            "width": 1200,
            "height": 628
          },
          "instagram-portrait": {
            "x": 0,
            "y": 0,
            "width": 1080,
            "height": 1350
          },
          "instagram-story": {
            "x": 0,
            "y": 0,
            "width": 1080,
            "height": 1920
          }
        }
      },
      {
        "name": "no_tiggo-7-phev-logo",
        "type": "logo",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "image_url",
            "help": "Public HTTP(s) URL of the image (i.e. https://photo.com/image.png)",
            "values": {
              "facebook-post": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_129c74c8-5d5b-4e1a-90d0-c6e430e2d5da.png",
              "facebook-feed": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_3b9d7e80-3127-4e24-abac-6c70bfb0b2d4.png",
              "instagram-portrait": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_01183cf4-91c8-4d06-abc6-844b40803bfc.png",
              "instagram-story": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_01183cf4-91c8-4d06-abc6-844b40803bfc.png"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 411,
            "y": 64,
            "width": 378,
            "height": 48
          },
          "facebook-feed": {
            "x": 921,
            "y": 30,
            "width": 255,
            "height": 32
          },
          "instagram-portrait": {
            "x": 350,
            "y": 74,
            "width": 380,
            "height": 49
          },
          "instagram-story": {
            "x": 313,
            "y": 106,
            "width": 454,
            "height": 57
          }
        }
      },
      {
        "name": "no_logo_de_chirey",
        "type": "logo",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "image_url",
            "help": "Public HTTP(s) URL of the image (i.e. https://photo.com/image.png)",
            "values": {
              "facebook-post": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_6db73a9d-3b04-4b0b-b30e-9653087d42ca.png",
              "facebook-feed": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_6db73a9d-3b04-4b0b-b30e-9653087d42ca.png",
              "instagram-portrait": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_6db73a9d-3b04-4b0b-b30e-9653087d42ca.png",
              "instagram-story": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4/v2_6db73a9d-3b04-4b0b-b30e-9653087d42ca.png"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 963,
            "y": 1082,
            "width": 133,
            "height": 53
          },
          "facebook-feed": {
            "x": 1000,
            "y": 556,
            "width": 96,
            "height": 39
          },
          "instagram-portrait": {
            "x": 848,
            "y": 1140,
            "width": 134,
            "height": 53
          },
          "instagram-story": {
            "x": 822,
            "y": 1646,
            "width": 160,
            "height": 63
          }
        }
      },
      {
        "name": "04_text_legal",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 ",
              "facebook-feed": "Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 ",
              "instagram-portrait": "Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 ",
              "instagram-story": "Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 Text 01... Max Char. 200 "
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#ffffff",
              "facebook-feed": "#ffffff",
              "instagram-portrait": "#ffffff",
              "instagram-story": "#ffffff"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 114,
            "y": 1091,
            "width": 807,
            "height": 44
          },
          "facebook-feed": {
            "x": 113,
            "y": 560,
            "width": 860,
            "height": 37
          },
          "instagram-portrait": {
            "x": 98,
            "y": 1144,
            "width": 726,
            "height": 66
          },
          "instagram-story": {
            "x": 98,
            "y": 1641,
            "width": 726,
            "height": 73
          }
        }
      },
      {
        "name": "03_text",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "Text 03... Max Char. 30",
              "facebook-feed": "Text 03... Max Char. 30",
              "instagram-portrait": "Text 03... Max Char. 30",
              "instagram-story": "Text 03... Max Char. 30"
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#ffffff",
              "facebook-feed": "#ffffff",
              "instagram-portrait": "#ffffff",
              "instagram-story": "#ffffff"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 142,
            "y": 952,
            "width": 916,
            "height": 48
          },
          "facebook-feed": {
            "x": 113,
            "y": 494,
            "width": 916,
            "height": 33
          },
          "instagram-portrait": {
            "x": 128,
            "y": 1042,
            "width": 824,
            "height": 54
          },
          "instagram-story": {
            "x": 115,
            "y": 1485,
            "width": 850,
            "height": 144
          }
        }
      },
      {
        "name": "02_text",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "Text 02... Max Char. 40",
              "facebook-feed": "Text 02... Max Char. 40",
              "instagram-portrait": "Text 02... Max Char. 40",
              "instagram-story": "Text 02... Max Char. 40"
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#ffffff",
              "facebook-feed": "#ffffff",
              "instagram-portrait": "#ffffff",
              "instagram-story": "#ffffff"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 142,
            "y": 903,
            "width": 916,
            "height": 40
          },
          "facebook-feed": {
            "x": 113,
            "y": 459,
            "width": 916,
            "height": 29
          },
          "instagram-portrait": {
            "x": 128,
            "y": 989,
            "width": 824,
            "height": 45
          },
          "instagram-story": {
            "x": 128,
            "y": 1421,
            "width": 824,
            "height": 64
          }
        }
      },
      {
        "name": "01_title",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "Text 01... \nMax Char. 45",
              "facebook-feed": "Text 01... \nMax Char. 45",
              "instagram-portrait": "Text 01... \nMax Char. 45",
              "instagram-story": "Text 01... \nMax Char. 45"
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#ffffff",
              "facebook-feed": "#ffffff",
              "instagram-portrait": "#ffffff",
              "instagram-story": "#ffffff"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 142,
            "y": 293,
            "width": 916,
            "height": 249
          },
          "facebook-feed": {
            "x": 113,
            "y": 62,
            "width": 629,
            "height": 105
          },
          "instagram-portrait": {
            "x": 128,
            "y": 330,
            "width": 824,
            "height": 280
          },
          "instagram-story": {
            "x": 128,
            "y": 469,
            "width": 824,
            "height": 398
          }
        }
      }
    ],
    "created_at": 1758651206,
    "updated_at": 1758662723,
    "category_name": "Chirey - Tiggo 7 PHEV CSH 2026"
  },
  {
    "id": "612e957c-44f7-4d6c-be98-5ecd8392673d",
    "name": "Temp",
    "type": "static",
    "template_id": "612e957c-44f7-4d6c-be98-5ecd8392673d",
    "formats": [
      {
        "id": "facebook-post",
        "uid": "98c8f076-a642-4835-aee9-c030478a4c29",
        "width": 1200,
        "height": 1200,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/2d560e05-c41b-4168-b89c-e4f9c4d96e25.png"
      },
      {
        "id": "facebook-feed",
        "uid": "b285ec68-bd6f-46fc-acd8-9149f35fbb84",
        "width": 1200,
        "height": 628,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/2d560e05-c41b-4168-b89c-e4f9c4d96e25-facebook-feed.png"
      },
      {
        "id": "instagram-story",
        "uid": "03c87702-d543-4129-bba3-e06b30abaa37",
        "width": 1080,
        "height": 1920,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/2d560e05-c41b-4168-b89c-e4f9c4d96e25-instagram-story.png"
      }
    ],
    "elements": [
      {
        "name": "root",
        "type": "container",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "background_color",
            "help": "6 or 8 digits hexadecimal background color (i.e. #F3F3F3) of the banner ",
            "values": {
              "facebook-post": "#63152d",
              "facebook-feed": "#63152d",
              "instagram-story": "#63152d"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 0,
            "y": 0,
            "width": 1200,
            "height": 1200
          },
          "facebook-feed": {
            "x": 0,
            "y": 0,
            "width": 1200,
            "height": 628
          },
          "instagram-story": {
            "x": 0,
            "y": 0,
            "width": 1080,
            "height": 1920
          }
        }
      },
      {
        "name": "bg_image",
        "type": "image",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "image_url",
            "help": "Public HTTP(s) URL of the image (i.e. https://photo.com/image.png)",
            "values": {
              "facebook-post": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/612e957c-44f7-4d6c-be98-5ecd8392673d/v2_c85cb08d-dae3-4698-8b8f-c50eaf2c4a94.png",
              "facebook-feed": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/612e957c-44f7-4d6c-be98-5ecd8392673d/v2_c85cb08d-dae3-4698-8b8f-c50eaf2c4a94.png",
              "instagram-story": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/612e957c-44f7-4d6c-be98-5ecd8392673d/v2_c85cb08d-dae3-4698-8b8f-c50eaf2c4a94.png"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 620,
            "y": -249,
            "width": 580,
            "height": 1449
          },
          "facebook-feed": {
            "x": 602,
            "y": -148,
            "width": 600,
            "height": 803
          },
          "instagram-story": {
            "x": -18,
            "y": 779,
            "width": 1116,
            "height": 1171
          }
        }
      },
      {
        "name": "no-shape-0",
        "type": "shape",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "background_color",
            "help": "6 or 8 digits Hexadecimal color (i.e. #F3F3F3) of the shape",
            "values": {
              "facebook-post": "#c49466",
              "facebook-feed": "#c49466",
              "instagram-story": "#c49466"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": -416,
            "y": 831,
            "width": 1200,
            "height": 200
          },
          "facebook-feed": {
            "x": -71,
            "y": 375,
            "width": 730,
            "height": 223
          },
          "instagram-story": {
            "x": -160,
            "y": 583,
            "width": 1137,
            "height": 480
          }
        }
      },
      {
        "name": "no-shape-1",
        "type": "shape",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "background_color",
            "help": "6 or 8 digits Hexadecimal color (i.e. #F3F3F3) of the shape",
            "values": {
              "facebook-post": "#f3f3f3",
              "facebook-feed": "#f3f3f3",
              "instagram-story": "#f3f3f3"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": -83,
            "y": 497,
            "width": 867,
            "height": 429
          },
          "facebook-feed": {
            "x": -51,
            "y": 216,
            "width": 710,
            "height": 310
          },
          "instagram-story": {
            "x": -83,
            "y": 500,
            "width": 1060,
            "height": 450
          }
        }
      },
      {
        "name": "text_2",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "“Aumenté\nmi producción en 17%”",
              "facebook-feed": "“Aumenté\nmi producción en 17%”",
              "instagram-story": "“Aumenté\nmi producción en 17%”"
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#252525",
              "facebook-feed": "#252525",
              "instagram-story": "#252525"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 54,
            "y": 559,
            "width": 721,
            "height": 306
          },
          "facebook-feed": {
            "x": 50,
            "y": 248,
            "width": 639,
            "height": 255
          },
          "instagram-story": {
            "x": 82,
            "y": 546,
            "width": 863,
            "height": 368
          }
        }
      },
      {
        "name": "text_1",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "Unidos invertimos en Hidalgo",
              "facebook-feed": "Unidos invertimos en Hidalgo",
              "instagram-story": "Unidos invertimos en Hidalgo"
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#c49466",
              "facebook-feed": "#c49466",
              "instagram-story": "#c49466"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 54,
            "y": 345,
            "width": 565,
            "height": 117
          },
          "facebook-feed": {
            "x": 50,
            "y": 166,
            "width": 602,
            "height": 30
          },
          "instagram-story": {
            "x": 82,
            "y": 421,
            "width": 858,
            "height": 50
          }
        }
      },
      {
        "name": "text_0",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "Semillas de Independencia",
              "facebook-feed": "Semillas de Independencia",
              "instagram-story": "Semillas de Independencia"
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#f3f3f3",
              "facebook-feed": "#f3f3f3",
              "instagram-story": "#f3f3f3"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 54,
            "y": 960,
            "width": 713,
            "height": 46
          },
          "facebook-feed": {
            "x": 50,
            "y": 547,
            "width": 555,
            "height": 36
          },
          "instagram-story": {
            "x": 82,
            "y": 984,
            "width": 828,
            "height": 56
          }
        }
      },
      {
        "name": "no-logo",
        "type": "logo",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "image_url",
            "help": "Public HTTP(s) URL of the image (i.e. https://photo.com/image.png)",
            "values": {
              "facebook-post": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/612e957c-44f7-4d6c-be98-5ecd8392673d/v2_51b66ab6-d405-475b-bf88-695a2592303e.png",
              "facebook-feed": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/612e957c-44f7-4d6c-be98-5ecd8392673d/v2_51b66ab6-d405-475b-bf88-695a2592303e.png",
              "instagram-story": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/612e957c-44f7-4d6c-be98-5ecd8392673d/v2_51b66ab6-d405-475b-bf88-695a2592303e.png"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 54,
            "y": 98,
            "width": 345,
            "height": 100
          },
          "facebook-feed": {
            "x": 50,
            "y": 51,
            "width": 600,
            "height": 65
          },
          "instagram-story": {
            "x": 82,
            "y": 228,
            "width": 326,
            "height": 110
          }
        }
      }
    ],
    "created_at": 1752801747,
    "updated_at": 1752804531,
    "category_name": "Cuauhtémoc Hidalgo"
  },
  {
    "id": "6fa81fc3-8591-4e12-9ee1-1b5fca9b06ca",
    "name": "Template 03",
    "type": "static",
    "template_id": "6fa81fc3-8591-4e12-9ee1-1b5fca9b06ca",
    "formats": [
      {
        "id": "facebook-post",
        "uid": "c3891e6b-970d-4fbf-8b87-5eb2316ed693",
        "width": 1200,
        "height": 1200,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/9c6af556-fa0d-498c-a2bc-ba70474b4705.png"
      },
      {
        "id": "facebook-feed",
        "uid": "493f5743-faaf-43f1-9162-30151d235472",
        "width": 1200,
        "height": 628,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/9c6af556-fa0d-498c-a2bc-ba70474b4705-facebook-feed.png"
      },
      {
        "id": "instagram-story",
        "uid": "58809f3b-9240-4c64-92fa-d847e83defc2",
        "width": 1080,
        "height": 1920,
        "unit": "px",
        "preview_url": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/c7f8a281-b153-43cd-a45a-a669890ceaf9/9c6af556-fa0d-498c-a2bc-ba70474b4705-instagram-story.png"
      }
    ],
    "elements": [
      {
        "name": "root",
        "type": "container",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "background_color",
            "help": "6 or 8 digits hexadecimal background color (i.e. #F3F3F3) of the banner ",
            "values": {
              "facebook-post": "#f3f3f3",
              "facebook-feed": "#f3f3f3",
              "instagram-story": "#f3f3f3"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 0,
            "y": 0,
            "width": 1200,
            "height": 1200
          },
          "facebook-feed": {
            "x": 0,
            "y": 0,
            "width": 1200,
            "height": 628
          },
          "instagram-story": {
            "x": 0,
            "y": 0,
            "width": 1080,
            "height": 1920
          }
        }
      },
      {
        "name": "text_0",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "Unidos Invertimos en tu futuro",
              "facebook-feed": "Unidos Invertimos en tu futuro",
              "instagram-story": "Unidos Invertimos en tu futuro"
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#63152d",
              "facebook-feed": "#63152d",
              "instagram-story": "#63152d"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 60,
            "y": 689,
            "width": 1073,
            "height": 50
          },
          "facebook-feed": {
            "x": 559,
            "y": 95,
            "width": 544,
            "height": 32
          },
          "instagram-story": {
            "x": 69,
            "y": 1159,
            "width": 929,
            "height": 48
          }
        }
      },
      {
        "name": "quote",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "\"Aumenté mi margen en 15%\"",
              "facebook-feed": "\"Aumenté mi margen en 15%\"",
              "instagram-story": "\"Aumenté mi margen en 15%\""
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#252525",
              "facebook-feed": "#252525",
              "instagram-story": "#252525"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 60,
            "y": 760,
            "width": 1073,
            "height": 252
          },
          "facebook-feed": {
            "x": 559,
            "y": 155,
            "width": 601,
            "height": 320
          },
          "instagram-story": {
            "x": 69,
            "y": 1229,
            "width": 951,
            "height": 231
          }
        }
      },
      {
        "name": "picture",
        "type": "image",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "image_url",
            "help": "Public HTTP(s) URL of the image (i.e. https://photo.com/image.png)",
            "values": {
              "facebook-post": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/6fa81fc3-8591-4e12-9ee1-1b5fca9b06ca/v2_87c1bb50-4faf-4015-abaf-d73be5309e71.png",
              "facebook-feed": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/6fa81fc3-8591-4e12-9ee1-1b5fca9b06ca/v2_040cba42-0010-4751-8c6c-e740e5592151.jpeg",
              "instagram-story": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/6fa81fc3-8591-4e12-9ee1-1b5fca9b06ca/v2_c74b6b11-bbb0-42a4-98b8-dfe2878b32cd.jpeg"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 60,
            "y": 1,
            "width": 1079,
            "height": 640
          },
          "facebook-feed": {
            "x": -37,
            "y": -154,
            "width": 547,
            "height": 705
          },
          "instagram-story": {
            "x": 50,
            "y": -4,
            "width": 980,
            "height": 1098
          }
        }
      },
      {
        "name": "no-shape-0",
        "type": "shape",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "background_color",
            "help": "6 or 8 digits Hexadecimal color (i.e. #F3F3F3) of the shape",
            "values": {
              "facebook-post": "#63152d",
              "facebook-feed": "#63152d",
              "instagram-story": "#63152d"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": -1,
            "y": 1060,
            "width": 1202,
            "height": 140
          },
          "facebook-feed": {
            "x": 0,
            "y": 548,
            "width": 1200,
            "height": 80
          },
          "instagram-story": {
            "x": 0,
            "y": 1520,
            "width": 1080,
            "height": 400
          }
        }
      },
      {
        "name": "rating-text",
        "type": "text",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "payload",
            "help": "Text content (i.e. Lorem ipsum)",
            "values": {
              "facebook-post": "Semillas de Independencia",
              "facebook-feed": "Semillas de Independencia",
              "instagram-story": "Semillas de Independencia"
            }
          },
          {
            "id": "color",
            "help": "6 or 8 digits hexadecimal color (i.e. #EAEAEA) of the text",
            "values": {
              "facebook-post": "#c49466",
              "facebook-feed": "#c49466",
              "instagram-story": "#c49466"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 60,
            "y": 1109,
            "width": 809,
            "height": 48
          },
          "facebook-feed": {
            "x": 41,
            "y": 572,
            "width": 906,
            "height": 36
          },
          "instagram-story": {
            "x": 69,
            "y": 1574,
            "width": 702,
            "height": 45
          }
        }
      },
      {
        "name": "no-logo",
        "type": "logo",
        "settings": {
          "is_mandatory": False
        },
        "attributes": [
          {
            "id": "image_url",
            "help": "Public HTTP(s) URL of the image (i.e. https://photo.com/image.png)",
            "values": {
              "facebook-post": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/6fa81fc3-8591-4e12-9ee1-1b5fca9b06ca/v2_91b4c1b1-f647-4c3f-bfd4-47ddce8e10bc.png",
              "facebook-feed": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/6fa81fc3-8591-4e12-9ee1-1b5fca9b06ca/v2_91b4c1b1-f647-4c3f-bfd4-47ddce8e10bc.png",
              "instagram-story": "https://production-banners.s3-eu-west-1.amazonaws.com/templates/v2/c7f8a281-b153-43cd-a45a-a669890ceaf9/6fa81fc3-8591-4e12-9ee1-1b5fca9b06ca/v2_91b4c1b1-f647-4c3f-bfd4-47ddce8e10bc.png"
            }
          }
        ],
        "layout": {
          "facebook-post": {
            "x": 869,
            "y": 1095,
            "width": 271,
            "height": 70
          },
          "facebook-feed": {
            "x": 813,
            "y": 566,
            "width": 347,
            "height": 45
          },
          "instagram-story": {
            "x": 816,
            "y": 1559,
            "width": 185,
            "height": 70
          }
        }
      }
    ],
    "created_at": 1752798132,
    "updated_at": 1752799459,
    "category_name": "Cuauhtémoc Hidalgo"
  }
]
}

_MOCK_CTAS = ["CHAT_NOW","SEE_MORE","DONATE","JOIN_CHANNEL","AUDIO_CALL","VISIT_PAGES_FEED","SHARE","BUY_TICKETS","WHATSAPP_MESSAGE","SHOP_WITH_AI","PAY_TO_ACCESS","SAY_THANKS","ASK_ABOUT_SERVICES","BUY_VIA_MESSAGE","GET_A_QUOTE","EVENT_RSVP","TRY_ON_WITH_AI","START_ORDER","CALL","GET_PROMOTIONS","START_A_CHAT","LISTEN_NOW","ASK_A_QUESTION","BOOK_TRAVEL","MAKE_AN_APPOINTMENT","SWIPE_UP_SHOP","ASK_FOR_MORE_INFO","MESSAGE_PAGE","UPDATE_APP","LIKE_PAGE","FOLLOW_USER","VISIT_WEBSITE","SIGN_UP","DOWNLOAD","PURCHASE_GIFT_CARDS","NO_BUTTON","GET_DIRECTIONS","SWIPE_UP_PRODUCT","WOODHENGE_SUPPORT","GET_QUOTE","REQUEST_TIME","WATCH_MORE","VIEW_CHANNEL","APPLY_NOW","FIND_YOUR_GROUPS","REFER_FRIENDS","CONTACT","OPEN_INSTANT_APP","CONTACT_US","VIEW_IN_CART","INQUIRE_NOW","DONATE_NOW","GET_SHOWTIMES","USE_MOBILE_APP","RAISE_MONEY","VIEW_PRODUCT","GET_STARTED","TRY_DEMO","BUY","SEND_UPDATES","USE_APP","BOOK_NOW","VIDEO_CALL","PLAY_GAME_ON_FACEBOOK","ADD_TO_CART","ASK_US","CALL_NOW","BROWSE_SHOP","OPEN_LINK","BOOK_A_CONSULTATION","VIDEO_ANNOTATION","GET_OFFER_VIEW","SEND_A_GIFT","FIND_A_GROUP","SELL_NOW","CONFIRM","RECORD_NOW","VIEW_CART","ORDER_NOW","BUY_NOW","FOLLOW_PAGE","SHOP_NOW","GET_OFFER","LISTEN_MUSIC","INSTALL_APP","WATCH_VIDEO","CALL_ME","PLAY_GAME","FOLLOW_NEWS_STORYLINE","WATCH_LIVE_VIDEO","SEE_SHOP","GET_IN_TOUCH","SUBSCRIBE","INSTALL_MOBILE_APP","SEND_GIFT_MONEY","SOTTO_SUBSCRIBE","FIND_OUT_MORE","CHAT_WITH_US","GET_DETAILS","LEARN_MORE","MOBILE_DOWNLOAD"]
# ---------------------------------------------------------------------------
# Mock tool functions (same signature as campaign_tools.py originals)
# ---------------------------------------------------------------------------

async def get_adset_context(id_adset: int) -> dict[str, Any]:
    """Mock: returns pre-built adset 295 data regardless of id_adset."""
    print(f"Mock get_adset_context called with id_adset={id_adset}")
    return _MOCK_ADSET


async def get_brand_context(brand_id: str) -> dict[str, Any]:
    """Mock: returns Nike Total 90 brand guidelines."""
    return _MOCK_BRAND


async def get_audience_context(id_adset: str) -> dict[str, Any]:
    """Mock: returns two pre-built audience segments."""
    return _MOCK_AUDIENCES


async def get_template_context(project_id: str) -> dict[str, Any]:
    """Mock: returns two Abyssale template definitions."""
    return _MOCK_TEMPLATES


async def get_a_template_definition(template_id: str) -> dict[str, Any]:
    """Mock: returns a Abyssale template definition."""
    print(f"Mock get_a_template_definition called with project_id={template_id}")
    return next((template for template in _MOCK_TEMPLATES.get('templates', []) if template['id'] == template_id), {})


async def get_ctas() -> list[str]:
    """Mock: returns CTAs.
    """
    return _MOCK_CTAS

async def update_ad_channel_with_batch_id(id_ad: int, batch_id: str, image_ids: list[dict]) -> dict[str, Any]:
    """Mock: simulates updating an ad with a batch ID."""
    print(f"Mock update_ad_channel_with_batch_id called with id_ad={id_ad}, batch_id={batch_id}")
    return {"ok": True, "id_ad": id_ad, "batch_id": batch_id}


async def get_image_from_library(product_id: str) -> dict[str, Any]:
    """Mock: returns Image URL."""
    print(f"Mock get_image_from_library called with product_id={product_id}")
    return ["https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/Chirey_Tiggo_7_PHEV_CSH_124536.png", "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/Chirey_Tiggo_7_PHEV_CSH_34456.png",
            "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/Chirey_Tiggo_7_PHEV_CSH_536.png", "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/Chirey_Tiggo_7_PHEV_CSH_89675.png",
            "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/Chirey_Tiggo_7_PHEV_CSH_Precio_MEX_LaCochera_08.png", "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/Chirey_Tiggo_7_PHEV_CSH_Precio_MEX_LaCochera_09.png",
            "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/Chirey_Tiggo_7_PHEV_CSH_Precio_MEX_LaCochera_11.png", "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/Chirey_Tiggo_7_PHEV_CSH_Precio_MEX_LaCochera_13.png",
            "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/t7p-eplus_Spoiler.jpg", "https://hiluca-images-dev.s3.us-east-2.amazonaws.com/Imagenes_Tigo/T7PHEV_2026_RINES.jpg"]


async def get_person_main_image(id_buyer_persona: int, image_id: str) -> dict[str, Any]:
    """Mock: returns a specific image from the library by ID."""
    print(f"Mock get_person_main_image called with id_buyer_persona={id_buyer_persona}, image_id={image_id}")
    return {
        "id": image_id,
        "url": "https://hiluca-assets-dev.s3.us-east-2.amazonaws.com/1/IMG_71aa78ff-9ca9-4715-a7d4-917b136aaf8d_persona_146_v1.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIA4RCAOHP6JI44OTFD%2F20260519%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20260519T173834Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEBIaCXVzLWVhc3QtMiJHMEUCIH6H6m4GUtJMHIDv0I7DBLZRjDYf0CXbI32RBywoAMRuAiEA6F%2BXtRT%2FWpZfcsE5y2h7LwAU1OQcwqS8Ay4k8AaKhgsq%2BwMI2%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw4NjEyNzYwOTM0MzYiDKbOcy3H4EG7mf0vpSrPA6ILyp70qX6IRcUk%2BSjLgMR53NPnaXO30ium5GMDpCY9wMPHty47RLjky18%2B3LHMGN6BUTTBu60Mze5BkN9qM%2FdjRi8CTP4C9zw6qtn6EoSiuqqA5HwM0Sn%2Fr8GoLCtpYDs4IRY9IlvHghryzFlqtaHrfcZpBb7UIT44UM6qXz64FVB%2B7vJrFXuuT2hHA%2FQv5LtPETQvHliBYJD5MK8jUocLfh6rSRnOjcyA8gKj2osXVBURtM2LZbxjefnH9xztcZr4NlOchm1u1%2F%2F7kXbuI4RRCmFolNKLYUiTxNehvQAVw7eKAOOBcH0FRIRYvsxjr3XcQzcrJwUOuhyA%2BeV6vIsKCR6o7uKe04bzmDh8vCKIgAuciNMVGpH2HHjKVjYWi85YIQQ6K2wIjzJgSYdGNNPjD1ERcuhRF5MCNCmJYiQDMhOEEfqGm3jN49rE8Fss2zMoe60pDaPIlcjVa3DtkRQn1o%2BaUa4%2Bct74BNzd%2FzemF4S1WiCyDRS2eSM9pTym0vQfyV2bhHglGKfwGPBTQh6nRsFkqBvKVL9pSzYMQyViuAv39P6xwr%2FRNMIOxTq9QazT1GWLK6ms8jztNfiCz6ZfECBTe3Ce09k1LTmwP5Ewxr2y0AY6oQFW8HPSld0FvRcmqZ%2FJUI%2BU0h%2BTXU9kE85MglH%2BpEhxdhQb1ULJnSH1pwbJPovMRkWG5yOSEY5tOsnaoPxA5rPeI9NW9L4OUdgpAd3wLpwKpR1guhujgyzpheWitL29FfccrWBVtnuFTaEbKaguwhdUeFfRemrU6YyiEphlPJNcTKwiHr%2B6c2r9jVLaKrj1mKY1UXwvG%2F9VA57wbHbk8rM29w%3D%3D&X-Amz-Signature=83e5e76ef7f5d45c89b2b7a7040fb7d3ca3148a04827aa49ec4cccdb2ddcb82a&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject",
        "prompt": "Soft natural morning daylight filters into a vibrant urban coffee shop, illuminating Anna, a realistic 21-year-old tech enthusiast in casual streetwear. Captured as an eye-level portrait with an 85mm f/1.8 lens, the shallow depth of field beautifully blurs the background while keeping her focused expression sharp. She leans slightly forward, interacting with a sleek modern smartphone on the table, embodying her aspiration for seamless connectivity. Cinematic 8k, photorealistic, environmental candid style, with absolutely no text, logos, or brand elements."
    }


async def get_persona_variant_image(id_buyer_persona: int, image_id: str) -> dict[str, Any]:
    """Mock: returns a specific image from the library by UUID."""
    print(f"Mock get_persona_variant_image called with id_buyer_persona={id_buyer_persona}, image_id={image_id}")
    return {
        "id": image_id,
        "url": "https://hiluca-assets-dev.s3.us-east-2.amazonaws.com/1/IMG_71aa78ff-9ca9-4715-a7d4-917b136aaf8d_persona_146_v1.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIA4RCAOHP6JI44OTFD%2F20260519%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20260519T173834Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEBIaCXVzLWVhc3QtMiJHMEUCIH6H6m4GUtJMHIDv0I7DBLZRjDYf0CXbI32RBywoAMRuAiEA6F%2BXtRT%2FWpZfcsE5y2h7LwAU1OQcwqS8Ay4k8AaKhgsq%2BwMI2%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw4NjEyNzYwOTM0MzYiDKbOcy3H4EG7mf0vpSrPA6ILyp70qX6IRcUk%2BSjLgMR53NPnaXO30ium5GMDpCY9wMPHty47RLjky18%2B3LHMGN6BUTTBu60Mze5BkN9qM%2FdjRi8CTP4C9zw6qtn6EoSiuqqA5HwM0Sn%2Fr8GoLCtpYDs4IRY9IlvHghryzFlqtaHrfcZpBb7UIT44UM6qXz64FVB%2B7vJrFXuuT2hHA%2FQv5LtPETQvHliBYJD5MK8jUocLfh6rSRnOjcyA8gKj2osXVBURtM2LZbxjefnH9xztcZr4NlOchm1u1%2F%2F7kXbuI4RRCmFolNKLYUiTxNehvQAVw7eKAOOBcH0FRIRYvsxjr3XcQzcrJwUOuhyA%2BeV6vIsKCR6o7uKe04bzmDh8vCKIgAuciNMVGpH2HHjKVjYWi85YIQQ6K2wIjzJgSYdGNNPjD1ERcuhRF5MCNCmJYiQDMhOEEfqGm3jN49rE8Fss2zMoe60pDaPIlcjVa3DtkRQn1o%2BaUa4%2Bct74BNzd%2FzemF4S1WiCyDRS2eSM9pTym0vQfyV2bhHglGKfwGPBTQh6nRsFkqBvKVL9pSzYMQyViuAv39P6xwr%2FRNMIOxTq9QazT1GWLK6ms8jztNfiCz6ZfECBTe3Ce09k1LTmwP5Ewxr2y0AY6oQFW8HPSld0FvRcmqZ%2FJUI%2BU0h%2BTXU9kE85MglH%2BpEhxdhQb1ULJnSH1pwbJPovMRkWG5yOSEY5tOsnaoPxA5rPeI9NW9L4OUdgpAd3wLpwKpR1guhujgyzpheWitL29FfccrWBVtnuFTaEbKaguwhdUeFfRemrU6YyiEphlPJNcTKwiHr%2B6c2r9jVLaKrj1mKY1UXwvG%2F9VA57wbHbk8rM29w%3D%3D&X-Amz-Signature=83e5e76ef7f5d45c89b2b7a7040fb7d3ca3148a04827aa49ec4cccdb2ddcb82a&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject",
        "prompt": "Soft natural morning daylight filters into a vibrant urban coffee shop, illuminating Anna, a realistic 21-year-old tech enthusiast in casual streetwear. Captured as an eye-level portrait with an 85mm f/1.8 lens, the shallow depth of field beautifully blurs the background while keeping her focused expression sharp. She leans slightly forward, interacting with a sleek modern smartphone on the table, embodying her aspiration for seamless connectivity. Cinematic 8k, photorealistic, environmental candid style, with absolutely no text, logos, or brand elements."
    }


async def save_ads(id_adset: int, id_ad: int, payloads: list[dict]) -> dict[str, Any]:
    """Mock: simulates saving multiple ads to Sinergia."""
    print(f"Mock save_ads called with id_adset={id_adset}, {len(payloads)} payloads")
    print(f"Payloads to be saved in Sinergia: {json.dumps(payloads, indent=2, ensure_ascii=False)}")
    return {"ok": True, "ads": {"ok": True, "data": {"ad_set_id": 295, "ad_id": 678, "created": [{"id": 1310}, {"id": 1311}, {"id": 1312}]}}}

_mock_library_upload_counter = itertools.count(1)


async def upload_image_to_library(ad_id: int, image_data: dict) -> str:
    """Mock: simulates uploading an image to the library; returns a distinct ID per call (D13).

    Args:
        ad_id: Ad ID in Strapi.
        image_data: Dict with image_data (base64 data-URI or URL), image_name, mime_type,
            plan_id and image_prompt (prompt that produced the image; may be ""). Any
            extra keys are accepted; only the keys are printed.

    Returns:
        Mock image ID in the form IMG_mock_{ad_id}_{n}.
    """
    print(f"Mock upload_image_to_library called with ad_id={ad_id}, image_data keys={list(image_data.keys())}")
    n = next(_mock_library_upload_counter)
    return f"IMG_mock_{ad_id}_{n}"

async def delete_variants(variant_ids: list[int]) -> bool:
    """Mock: simulates deleting variants."""
    print(f"Mock delete_variants called with variant_ids={variant_ids}")
    return True

async def get_products_by_brand(brand_id: str) -> dict[str, Any]:
    """Mock: returns a single product for the brand."""
    return {
        "ok": True,
        "products": {
            "data": [
                {
                    "id": 8,
                    "attributes": {
                        "name": "Nike Total 90",
                        "description": "Retro football sneaker inspired by the iconic Total 90 boot.",
                    },
                }
            ]
        },
    }


async def get_product_context(product_id: int) -> dict[str, Any]:
    """Mock: returns full product context for Nike Total 90."""
    return {
        "ok": True,
        "product": {
            "data": {
                "id": product_id,
                "attributes": {
                    "name": "Nike Total 90",
                    "benefits": [
                        "Showcase iconic football design while staying casual",
                        "Enjoy secure fit with original asymmetrical lacing",
                        "Versatile — from the street to the living room",
                    ],
                    "features": [
                        "Padded upper offering authentic football aesthetics",
                        "Rubber outsole for street-ready grip",
                        "Memory foam insole for all-day comfort",
                    ],
                    "rtbs": [
                        "Inspired by the legendary Total 90 boot worn by iconic 2000s players",
                        "Available in limited colorways — collector appeal",
                    ],
                    "price": "USD 120",
                    "positioning": "Heritage football streetwear for the nostalgic generation",
                },
            }
        },
    }


# ---------------------------------------------------------------------------
# Mock tools for persona_data_collector_agent
# ---------------------------------------------------------------------------

_MOCK_BUYER_PERSONA = {
    "ok": True,
    "buyer_persona": {
        "id": 103,
        "name": "Ana y Enrique, los Guardianes del Estilo",
        "story": (
            "Ana y Enrique viven la realidad de muchas familias urbanas en CDMX, buscando un "
            "equilibrio entre confort, seguridad y eficiencia para sus trayectos diarios. Quieren "
            "un vehículo que les permita viajar cómodamente en familia y les ofrezca las últimas "
            "tecnologías de seguridad."
        ),
        "attributes": {
            "age_range": ["35-44", "45-54"],
            "gender": "Mixed (Male/Female couple)",
            "hometown": ["Ciudad de México | Del Valle Centro | Media"],
            "income_level_brackets": ["Finanzas equilibradas, gustos ocasionales."],
            "pain_points": [
                "Costos de SUV tradicionales son muy altos.",
                "No hay garantía extendida disponible.",
                "Falta SUV con tercera fila de asientos.",
            ],
            "customer_goal": [
                "Transportar cómodamente a su familia extendida en viajes y traslados diarios.",
                "Asegurar la máxima seguridad con tecnologías ADAS avanzadas.",
            ],
            "fears_and_worries": [
                "Inseguridad de protección infantil.",
                "Fallos en tecnología vehicular.",
                "Costos inesperados en el futuro.",
            ],
            "barriers_to_making_a_change": [
                "Arriesgarse a adoptar nueva tecnología.",
                "Dudas sobre rendimiento a largo plazo.",
                "Compromiso emocional con SUV actual.",
            ],
        },
    },
}


async def get_buyer_persona_context(id_buyer_persona: int) -> dict:
    """Mock: return real-shaped buyer persona data."""
    return _MOCK_BUYER_PERSONA


async def upload_persona_main_image(persona_id: int, image_data: dict) -> str:
    """Mock: pretend upload succeeded and return a fake image_id."""
    variation_id = image_data.get("variation_id", "v0")
    fake_id = f"mock_persona_{persona_id}_{variation_id}"
    return fake_id

async def upload_persona_image_variant(persona_id: int, image_base_id: str, image_data: dict, label: str) -> str:
    """Mock: pretend upload succeeded and return a fake image_id."""
    variation_id = image_data.get("variation_id", "v0")
    fake_id = f"mock_persona_{persona_id}_{image_base_id}_{variation_id}"
    return fake_id


# ---------------------------------------------------------------------------
# Ad variant image edit (mirrors campaign_tools.get_ad_variant_image with an
# identical signature; edited images are uploaded via upload_image_to_library)
# ---------------------------------------------------------------------------

# Signed on purpose to exercise _strip_signed_urls and the fresh-URL refresh (D4).
_MOCK_AD_VARIANT_BASE_IMAGE_URL = (
    "https://hiluca-assets-dev.s3.us-east-2.amazonaws.com/mock/ad_variant_base.png"
    "?X-Amz-Credential=MOCK&X-Amz-Security-Token=MOCK&X-Amz-Signature=MOCK"
)
_MOCK_AD_VARIANT_BASE_IMAGE_PROMPT = (
    "Mock base prompt: product hero shot on a clean studio background, soft lighting."
)


async def get_ad_variant_image(
    brand_id: int,
    campaign_id: int,
    ad_id: int,
    channel_id: int,
    variant_id: int,
    image_name: str,
    id_base_image: str,
) -> dict[str, Any]:
    """Mock (deterministic): {"id": id_base_image, "url": <signed mock URL>, "prompt": <fixed text>}."""
    return {
        "id": id_base_image,
        "url": _MOCK_AD_VARIANT_BASE_IMAGE_URL,
        "prompt": _MOCK_AD_VARIANT_BASE_IMAGE_PROMPT,
    }
