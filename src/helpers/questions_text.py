"""
Prompt templates for AI-generated anatomy questions.

Bibliography used on prompt and topics generation:

- Anatomía Humana, 4th Edition by Latarjet & Ruiz Liard

- Mini-NETTER Atlas of Human Anatomy, 8th Edition by Frank H. Netter, MD

- Anatomía Humana Descriptiva, Topográfica y Funcional 11th Edition by
    Henri Rouvière & André Delmas

- Anatomía Clínica, 3rd Edition by Eduardo Pró
"""

UBA_DIVERSITY_MODES = [
    "identification",
    "relationship",
    "location",
    "function",
    "innervation",
    "vascularization",
    "exception",
]

LOCOMOTOR_DESCRIPTIONS = {
    "osteologia_general": "estructura, tipos de huesos, osificación, irrigación e inervación ósea",
    "osteologia_miembro_superior": "huesos del miembro superior, accidentes óseos, relaciones, relieves y funciones",  # pylint: disable=line-too-long
    "osteologia_miembro_inferior": "huesos del miembro inferior, accidentes óseos, relaciones, relieves y funciones",  # pylint: disable=line-too-long
    "osteologia_columna_vertebral": "vértebras, características regionales y articulación",
    "osteologia_torax": "esternón, costillas y su organización estructural",
    "osteologia_craneo": "huesos del cráneo, base y bóveda, forámenes",
    "articulaciones_general": "tipos articulares, movimientos y estructuras asociadas",
    "articulaciones_miembro_superior": "articulaciones del miembro superior y sus movimientos",
    "articulaciones_miembro_inferior": "articulaciones del miembro inferior y sus movimientos",
    "articulaciones_columna": "articulaciones vertebrales y discos intervertebrales",
    "articulaciones_craneo": "suturas y articulaciones craneales",
    "miologia_general": "tipos musculares, inserciones, irrigación e inervación",
    "musculos_miembro_superior": "músculos del miembro superior y sus funciones",
    "musculos_miembro_inferior": "músculos del miembro inferior y sus funciones",
    "musculos_espalda": "músculos superficiales y profundos del dorso y nuca",
    "compartimentos_brazo": "compartimentos anterior y posterior del brazo",
    "compartimentos_antebrazo": "compartimentos flexor y extensor",
    "compartimentos_mano": "compartimentos musculares de la mano",
    "compartimentos_muslo": "compartimentos del muslo",
    "compartimentos_pierna": "compartimentos de la pierna",
    "compartimentos_pie": "compartimentos del pie",
    "arterias_miembro_superior": "irrigación arterial del miembro superior",
    "arterias_miembro_inferior": "irrigación arterial del miembro inferior",
    "venas_miembro_superior": "drenaje venoso superficial y profundo superior",
    "venas_miembro_inferior": "drenaje venoso superficial y profundo miembro inferior",
    "plexo_braquial": "formación, ramos colaterales y profundos y territorios del plexo braquial",
    "nervios_miembro_superior": "inervación completa del miembro superior y recurridos de los nervios principales",  # pylint: disable=line-too-long
    "nervios_miembro_inferior": "inervación completa del miembro inferior y recurridos de los nervios principales",  # pylint: disable=line-too-long
    "axila": "límites, contenido y relaciones de la axila",
    "region_deltoidea": "limites y contenidos de la región deltoidea",
    "fosa_cubital": "límites y contenidos de la fosa cubital",
    "canal_carpiano": "contenidos y límites del túnel carpiano",
    "triangulo_femoral": "límites y contenido del triángulo femoral",
    "conducto_aductor": "trayecto, limites y contenido del conducto aductor",
    "fosa_poplitea": "límites y contenidos de la fosa poplítea",
    "regiones_topograficas_miembro_superior": "regiones del miembro superior",
    "regiones_topograficas_miembro_inferior": "regiones del miembro inferior",
    "linfaticos_miembro_superior": "drenaje linfático del miembro superior",
    "linfaticos_miembro_inferior": "drenaje linfático del miembro inferior",
    "linfaticos_dorso": "linfáticos del dorso",
    "linfaticos_nuca": "drenaje linfático de la región nucal",
    "planimetria": "division del cuerpo en ejes y planes",
}

SPLACHNOLOGY_DESCRIPTIONS = {
    "regiones_topograficas_cabeza": "división anatómica superficial de la cabeza",
    "regiones_topograficas_cuello": "triángulos cervicales y contenidos",
    "regiones_topograficas_tronco": "regiones del tronco y referencias anatómicas",
    "cavidad_oral": "estructura, límites y contenido de la cavidad oral",
    "lengua": "músculos, inervación y vascularización de la lengua",
    "glandulas_salivales": "glándulas mayores y menores, drenaje y función",
    "faringe": "divisiones, músculos, inervación e irrigación",
    "esofago": "trayecto, inervación, irrigación y relaciones",
    "estomago": "regiones, relaciones, irrigación e inervación",
    "intestino_delgado": "duodeno, yeyuno e íleon",
    "intestino_grueso": "colon, ciego y recto",
    "higado": "segmentación, irrigación y drenaje",
    "vias_biliares": "conductos biliares y drenaje",
    "vesicula_biliar": "estructura e irrigación",
    "pancreas": "regiones, función e irrigación",
    "cavidad_nasal": "estructura y límites",
    "senos_paranasales": "estructura y límites",
    "laringe": "cartílagos, músculos, irrigación e inervación",
    "traquea": "estructura y relaciones",
    "bronquios": "estructura y relaciones",
    "pulmones": "lóbulos, segmentación, relaciones, irrigación e inervación",
    "pleura": "hojas pleurales y cavidad",
    "rinon": "estructura, relaciones e irrigación",
    "ureter": "trayecto, relacionesl ley de lushka y estrechamientos",
    "vejiga": "estructura, irrigación, inervación y relaciones",
    "uretra": "porciones, musculos, inervación, irrigación y diferencias sexuales",
    "testiculo": "relaciones, irrigación e inervación",
    "epididimo": "trayecto y relaciones",
    "conducto_deferente": "trayecto y relaciones",
    "vesiculas_seminais": "relaciones y trayecto",
    "prostata": "estructura, irrigación e inervación",
    "pene": "periné, estructura, vascularización e inervación",
    "ovario": "relaciones, ligamentos, irrigación e inervación",
    "trompas_uterinas": "segmentos, relaciones, ligamentos, irrigación e inervación",
    "utero": "segmentos, relaciones, ligamentos, irrigación e inervación",
    "vagina": "estructura, relaciones, ligamentos, irrigación e inervación",
    "genitales_externos_femeninos": "periné, vulva, componentes, irrigación e inervación",
    "peritoneo": "hojas y cavidad peritoneal",
    "mesenterios": "fijación de vísceras",
    "epiplones": "omento mayor y menor",
    "retroperitoneo": "órganos retroperitoneales",
    "peritoneo_fascia_coalescencia": "fascias de coalescencia y fijación",
    "linfatico_abdominal": "drenaje linfático abdominal",
    "linfatico_toracico": "linfáticos torácicos",
    "conducto_toracico": "trayecto y drenaje",
    "ganglios_linfaticos_abdominales": "grupos ganglionares abdominales",
    "ganglios_linfaticos_toracicos": "ganglios torácicos",
    "linfaticos_cabeza_cuello": "drenaje linfático de cabeza y cuello",
    "linfaticos_pelvicos": "linfáticos de pelvis",
    "linfaticos_abdominales_detallados": "red linfática abdominal detallada",
    "linfaticos_toracicos_detallados": "red linfática torácica",
    "drenaje_venoso_superficial_abdominal": "venas superficiales abdominales",
    "drenaje_venoso_profundo_abdominal": "sistema venoso profundo abdominal",
    "drenaje_venoso_superficial_pelvico": "venas superficiales pélvicas",
    "drenaje_venoso_profundo_pelvico": "drenaje venoso profundo pélvico",
    "irrigacion_digestivo": "arterias del sistema digestivo",
    "irrigacion_respiratorio": "vascularización respiratoria",
    "irrigacion_pelvico": "arterias pélvicas",
    "musculos_cabeza": "músculos faciales y masticadores",
    "musculos_cuello": "músculos cervicales y sus funciones",
    "musculos_torax": "músculos intercostales y respiratorios",
    "musculos_abdomen": "músculos de la pared abdominal",
    "musculatura_abdominal": "función y organización muscular abdominal",
    "musculatura_respiratoria": "músculos respiratorios",
    "musculatura_pelvica": "suelo pélvico",
    "plexo_lumbar": "formation de nervios, ramas y sus recurridos del plexo lumbar",
    "plexo_sacro": "formación de nervios, ramas y sus recurridos del plexo sacro",
}

NEURO_DESCRIPTIONS = {
    "medula_espinal": "LCR, segmentos, sustancia gris y blanca",
    "tronco_encefalico": "mesencéfalo, puente y bulbo",
    "bulbo_raquideo": "núcleos y funciones",
    "puente": "estructura y conexiones",
    "mesencefalo": "pedúnculos y colículos",
    "cerebelo": "lóbulos y funciones",
    "diencefalo": "tálamo e hipotálamo",
    "talamus": "núcleos y funciones",
    "hipotalamo": "control autonómico",
    "telencefalo": "hemisferios cerebrales",
    "corteza_cerebral": "áreas funcionales, giros y surcos",
    "lobulos_cerebrales": "división cortical",
    "ganglios_basales": "núcleos profundos",
    "vias_motoras": "vías descendentes",
    "vias_piramidales": "tracto corticoespinal",
    "vias_extrapiramidales": "control motor involuntario",
    "vias_sensitivas": "vías ascendentes",
    "nervios_craneales": "pares craneales, trayectos y funciones",
    "nervio_olfatorio": "via, trayectos y funciones",
    "nervio_optico": "via, trayectos y funciones",
    "nervio_oculomotor": "via, trayectos y funciones",
    "nervio_troclear": "via, trayectos y funciones",
    "nervio_trigemino": "via, trayectos y funciones",
    "nervio_abducens": "via, trayectos y funciones",
    "nervio_facial": "via, trayectos y funciones",
    "nervio_vestibulococlear": "via, trayectos y funciones",
    "nervio_glosofaringeo": "via, trayectos y funciones",
    "nervio_vago": "via, trayectos y funciones",
    "nervio_accesorio": "via, trayectos y funciones",
    "nervio_hipogloso": "via, trayectos y funciones",
    "sistema_nervioso_autonomo": "simpático y parasimpático",
    "simpatico": "respuestas de alerta",
    "parasimpatico": "funciones viscerales",
    "meninges": "duramadre, aracnoides y piamadre",
    "liquido_cefalorraquideo": "producción y circulación",
    "ventriculos_cerebrales": "sistema ventricular",
    "irrigacion_cerebral": "arterias cerebrales",
    "circulo_de_willis": "anastomosis arterial",
    "senos_venosos": "drenaje venoso",
    "ojo": "estructura ocular",
    "oido": "oído externo, medio e interno",
    "vias_opticas": "trayecto visual",
    "vias_auditivas": "trayecto auditivo",
    "drenaje_venoso_superficial_cerebral": "venas superficiales",
    "drenaje_venoso_profundo_cerebral": "sistema venoso profundo",
    "drenaje_linfatico_cerebral": "drenaje linfático encefálico",
    "sistema_vertebrobasilar": "arterias vertebrales y basilar",
    "irrigacion_cerebral_detallada": "ramas arteriales y sus porciones cerebrales detalladas",
}

QUESTION_OUTPUT_FORMAT = (
    "{\n"
    '"question": "...",\n'
    '"answer_a": "...",\n'
    '"answer_b": "...",\n'
    '"answer_c": "...",\n'
    '"answer_d": "...",\n'
    '"explanation_a": "...",\n'
    '"explanation_b": "...",\n'
    '"explanation_c": "...",\n'
    '"explanation_d": "...",\n'
    '"correct_answer": "A|B|C|D"\n'
    "}"
)

COMMON_ANATOMY_QUESTION_TEMPLATE = (
    "You are a senior medical professor specialized in Human Anatomy and an expert "
    "in writing multiple-choice questions that follow the style of UBA exams.\n\n"
    "TASK:\n"
    "- Generate EXACTLY ONE high-quality anatomy multiple-choice question.\n"
    "- Always generate a valid question.\n"
    "- Return JSON only.\n\n"
    "TOPIC:\n"
    "{TOPIC}\n\n"
    "SUBTOPIC:\n"
    "{SUB_TOPIC}\n\n"
    "SUBTOPIC DESCRIPTION:\n"
    "{SUBTOPIC_DESCRIPTION}\n\n"
    "DIVERSITY MODE:\n"
    "{DIVERSITY_MODE}\n\n"
    "RECENT QUESTIONS TO AVOID REPEATING:\n"
    "{RECENT_QUESTIONS}\n\n"
    "GLOBAL RULES:\n"
    "- Write in Rioplatense Spanish.\n"
    "- Use a concise academic tone.\n"
    "- The stem must be short, direct, and test only one concept.\n"
    "- Do not use clinical cases, vignettes, pathology, surgery, imaging, or histology.\n"
    "- Stay strictly inside the given subtopic and its description.\n"
    "- If the subtopic is narrow, adapt the question instead of expanding scope.\n"
    "- Never output meta-text, warnings, placeholders, or error messages.\n\n"
    "DIVERSITY MODE HANDLING:\n"
    "- Use {DIVERSITY_MODE} only when it naturally fits the subtopic.\n"
    "- If {DIVERSITY_MODE} does not fit, silently convert it into the nearest valid anatomy angle inside the same subtopic.\n"  # pylint: disable=line-too-long
    "- Never force innervation, vascularization, function, or exception if the subtopic does not support it.\n\n"
    "OPTION DESIGN RULES:\n"
    "- There must be exactly one correct answer.\n"
    "- The 4 options must belong to the same anatomical category.\n"
    "- The 4 options must be mutually exclusive and non-overlapping.\n"
    "- No duplicated options, no partially correct options, and no controversial keys.\n"
    "- Distractors must be plausible but clearly incorrect.\n"
    "- Use precise, standard anatomical terminology.\n\n"
    "EXPLANATION RULES:\n"
    "- Each explanation must explicitly mention the option it explains.\n"
    "- Correct option: explain why it is correct using anatomy-based reasoning.\n"
    "- Incorrect options: explain why each one is incorrect in relation to the stem.\n"
    "- Keep explanations brief and specific.\n"
    "- The correct explanation must match the selected correct letter.\n\n"
    "QUESTION CONSTRUCTION ORDER:\n"
    "1. Choose one fact that is fully supported by the subtopic.\n"
    "2. Build a stem that asks about only that fact.\n"
    "3. Create 3 distractors from the same category.\n"
    "4. Place the correct answer in position {CORRECT_LETTER}.\n"
    "5. Set correct_answer to {CORRECT_LETTER}.\n"
    "6. Perform a silent self-check to confirm scope, uniqueness, and JSON validity.\n\n"
    "TOPIC-SPECIFIC RULES:\n"
    "{TOPIC_RULES}\n\n"
    "OUTPUT FORMAT:\n"
    f"{QUESTION_OUTPUT_FORMAT}"
)

LOCOMOTOR_TOPIC_RULES = (
    "- Limit content to the locomotor system: bones, joints, ligaments, muscles, "
    "compartments, topographic regions, limb and back neurovascular anatomy, and "
    "related lymphatic drainage when explicitly supported by the subtopic.\n"
    "- Prefer question angles such as identification of bony landmarks, articular "
    "classification, movement, insertion, origin, muscle action, compartment "
    "content, regional limits, plexus branches, nerve territory, or arterial/venous "
    "course when the subtopic allows it.\n"
    "- Do not ask about viscera, cranial neuroanatomy, embryology, or physiology "
    "beyond direct anatomical function.\n"
    "- In osteology, keep options within the same kind of bone, part, process, "
    "surface, border, or foramen.\n"
    "- In arthrology, keep options within the same kind of joint, ligament, "
    "movement, or stabilizing structure.\n"
    "- In myology or compartments, keep options within the same kind of muscle, "
    "tendon, compartment content, or action."
)

SPLANCHNOLOGY_TOPIC_RULES = (
    "- Limit content to viscera and regional anatomy of digestive, respiratory, "
    "urinary, genital, peritoneal, cervical, cephalic, thoracic, abdominal, and "
    "pelvic splanchnology exactly when supported by the subtopic.\n"
    "- Prefer question angles such as limits, parts, segments, coverings, "
    "relations, contents, fixations, ducts, sphincters, arterial supply, venous "
    "drainage, lymphatic drainage, and innervation when the subtopic allows it.\n"
    "- Do not ask about limb musculoskeletal anatomy, cortical neuroanatomy, "
    "histology, embryology, or clinical syndromes.\n"
    "- For hollow viscera, keep options within the same category of wall segment, "
    "relation, opening, or content.\n"
    "- For glands and solid organs, keep options within the same category of lobe, "
    "segment, surface, ligament, hilum element, or vascular relation.\n"
    "- For peritoneum and topographic regions, keep options within the same category "
    "of fold, recess, fascia, boundary, or regional content."
)

NEUROANATOMY_TOPIC_RULES = (
    "- Limit content to the central and peripheral nervous system: spinal cord, "
    "brainstem, cerebellum, diencephalon, telencephalon, pathways, cranial nerves, "
    "autonomic nervous system, meninges, ventricles, cerebrospinal fluid, cerebral "
    "vascularization, and special sensory pathways exactly when supported by the "
    "subtopic.\n"
    "- Prefer question angles such as nuclei, origins, apparent origins, course, "
    "connections, functional components, cortical areas, tract direction, "
    "foramina, meningeal relations, ventricular communications, and arterial or "
    "venous territories when the subtopic allows it.\n"
    "- Do not ask about digestive, respiratory, urinary, or reproductive viscera, "
    "nor about limb musculoskeletal anatomy.\n"
    "- For cranial nerves and tracts, keep options within the same category of "
    "nerve, nucleus, tract, origin, branch, or target territory.\n"
    "- For encephalic regions, keep options within the same category of nucleus, "
    "gyrus, lobe, colliculus, peduncle, or commissure.\n"
    "- For meninges, ventricles, and vascular topics, keep options within the same "
    "category of sinus, artery, ventricle, cistern, layer, or communication."
)


def build_anatomy_question_prompt(topic_rules: str) -> str:
    """Build a topic-specific prompt from the common anatomy template."""
    return COMMON_ANATOMY_QUESTION_TEMPLATE.replace("{TOPIC_RULES}", topic_rules)


LOCOMOTOR_QUESTION = build_anatomy_question_prompt(LOCOMOTOR_TOPIC_RULES)
SPLANCHNOLOGY_QUESTION = build_anatomy_question_prompt(SPLANCHNOLOGY_TOPIC_RULES)
NEUROANATOMY_QUESTION = build_anatomy_question_prompt(NEUROANATOMY_TOPIC_RULES)

ANATOMY_QUESTION_PROMPTS = {
    "Locomotor": LOCOMOTOR_QUESTION,
    "Splanchnology": SPLANCHNOLOGY_QUESTION,
    "Neuroanatomy": NEUROANATOMY_QUESTION,
}

ANATOMY_QUESTION = LOCOMOTOR_QUESTION


def get_anatomy_question_prompt(parameter: str) -> str:
    """Return the prompt that best matches the requested anatomy topic."""
    return ANATOMY_QUESTION_PROMPTS.get(parameter, ANATOMY_QUESTION)
