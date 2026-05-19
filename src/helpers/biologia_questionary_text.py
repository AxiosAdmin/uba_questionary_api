"""
Prompt templates for AI-generated biology questions.

Bibliography used on prompt and topics generation:

- Cooper GM. "La Celula". 2021, 8th Edition, Editorial Marban
- Alberts, Bray, Lewis, Raff y Watson. "Biologia Molecular de la Celula".
  2017, 6th Edition, Editorial Omega
- Lodish H y col. "Biologia celular y molecular". 2023, 9th Edition,
  Editorial Panamericana
- Turnpenny P. "Elementos de Genetica Medica". 2022, 16th Edition,
  Editorial Elsevier
- Jorde L., Carey J., Bamshad M. "Genetica Medica". 2020, 6th Edition,
  Editorial Elsevier
- Nussbaum R. "Genetica en Medicina". 2016, 8th Edition, Editorial Elsevier
- Krebs J., Goldstein E., Kilpatrick S. "Genes. Fundamentos". 2013,
  2nd Edition, Editorial Panamericana
- Strachan T. "Genetica molecular humana". 2018, 5th Edition,
  Editorial McGraw-Hill Interamericana
"""

BIOLOGY_DIVERSITY_MODES = [
    "definition",
    "mechanism",
    "comparison",
    "sequence",
    "regulation",
    "application",
    "consequence",
]

BIOLOGIA_CELULAR_Y_MOLECULAR_DESCRIPTIONS = {
    "replicacion_adn": "caracteristicas, fases y fidelidad de la replicacion del ADN",
    "reparacion_adn": "sistemas y mecanismos de reparacion del ADN nuclear",
    "mutaciones_y_variabilidad": (
        "mutaciones, variabilidad del ADN, mutaciones somaticas y germinales"
    ),
    "recombinacion_y_transposicion": (
        "recombinacion homologa, recombinacion sitio especifica y transposicion"
    ),
    "amplificacion_genica": "amplificacion genica como mecanismo de variabilidad",
    "pcr_y_rt_qpcr": "PCR y RT-qPCR como modelos de replicacion y analisis molecular",
    "proliferacion_celular": "poblaciones celulares, proliferacion, citometria e indice mitotico",
    "ciclo_celular": "etapas del ciclo celular, mitosis y meiosis",
    "control_ciclo_celular": (
        "ciclinas, quinasas, puntos de control, punto de restriccion y factores de crecimiento"
    ),
    "division_celular_fase_m": "mecanismos moleculares de la division celular en fase M",
    "oncogenes_y_supresores": (
        "perdida del control del crecimiento, protooncogenes y genes supresores"
    ),
    "flujo_informacion_genetica": "flujo de la informacion genetica desde ADN a ARN y proteina",
    "transcripcion_y_maduracion_arn": (
        "mecanismos de transcripcion y maduracion de los ARN"
    ),
    "traduccion_arnm": "mecanismos de traduccion del ARNm",
    "control_pretranscripcional_transcripcional": (
        "control pretranscripcional y transcripcional en eucariotas"
    ),
    "remodelacion_cromatina": "estructura cromatinica, remodelacion y transcripcion",
    "codigo_histonas_y_metilacion_adn": (
        "acetilacion, desacetilacion de histonas y metilacion del ADN"
    ),
    "control_combinatorio_transcripcion": (
        "factores especificos, cofactores y control combinatorio de la transcripcion"
    ),
    "splicing_alternativo": "splicing alternativo y su regulacion",
    "arns_no_codificantes_y_microarns": (
        "ARN no codificantes, microARNs y regulacion de la expresion genica"
    ),
    "vida_media_arns_y_proteinas": (
        "regulacion de la vida media de ARNm y proteinas"
    ),
    "fraccionamiento_subcelular": "fraccionamiento subcelular y extraccion de ADN",
    "electroforesis": "electroforesis de acidos nucleicos y proteinas",
    "inmunohistoquimica_e_inmunofluorescencia": (
        "localizacion y estudio funcional de proteinas por tecnicas inmunologicas"
    ),
    "western_blot": "fundamentos y utilidad del Western blot",
    "adn_recombinante_y_vectores": (
        "proteinas de fusion, vectores de expresion y herramientas de ADN recombinante"
    ),
    "crispr_cas_y_animales_transgenicos": (
        "CRISPR-Cas y animales transgenicos como herramientas de estudio"
    ),
    "compartimentalizacion_celular": (
        "membrana plasmatica, nucleo, citosol, endomembranas, peroxisomas y mitocondrias"
    ),
    "membrana_y_transporte": (
        "permeabilidad, transporte y pasaje de macromoleculas entre compartimientos"
    ),
    "sistema_endomembranas": "composicion y funciones del sistema de endomembranas",
    "sintesis_y_distribucion_macromoleculas": (
        "senales de distribucion y trafico de macromoleculas"
    ),
    "procesamiento_postraduccional": (
        "procesamiento postraduccional y regulacion de la funcionalidad proteica"
    ),
    "nanotubos": "ultraestructura y dinamica de nanotubos celulares",
    "exosomas": "ultraestructura y dinamica de exosomas",
    "microtubulos": (
        "polimerizacion, despolimerizacion, proteinas asociadas y transporte"
    ),
    "microfilamentos": (
        "polimerizacion, despolimerizacion, proteinas asociadas y funciones"
    ),
    "filamentos_intermedios": (
        "resistencia mecanica, anclaje, adhesion y envoltura nuclear"
    ),
    "golgi_endosomas_reciclado": (
        "aparato de Golgi, endosomas y reciclado de membranas"
    ),
    "exocitosis_y_endocitosis": "dinamica de exocitosis y endocitosis",
    "migracion_celular": (
        "migracion celular direccional, adhesion y remodelacion del citoesqueleto"
    ),
    "contraccion_muscular": (
        "senalizacion, calcio, microfilamentos, miosina y desmina en la contraccion"
    ),
    "polaridad_epitelial": (
        "polaridad celular, centrosoma, microtubulos y resistencia mecanica epitelial"
    ),
    "fecundacion": (
        "reaccion acrosomica, reaccion cortical y fusion de membranas"
    ),
    "citocinesis_y_huso_mitotico": (
        "huso mitotico, citocinesis y reorganizacion de biomembranas"
    ),
    "bioenergetica_celular": (
        "obtencion de energia, carriers de alta energia y fuerza proton-motriz"
    ),
    "mitocondrias": "estructura, funcion y compartimientos mitocondriales",
    "fusion_y_fision_mitocondrial": (
        "fusion, fision y relacion con la funcionalidad mitocondrial"
    ),
    "mitocondrias_en_calcio_apoptosis_esteroidogenesis": (
        "rol mitocondrial en calcio, apoptosis y esteroidogenesis"
    ),
    "peroxisomas": "estructura y funciones de peroxisomas",
    "nicho_celular_y_matriz_extracelular": (
        "nicho celular, matriz extracelular e integracion tisular"
    ),
    "adhesiones_celulares": "adhesiones celula-celula y celula-matriz",
    "remodelacion_matrices": "remodelacion de matrices y metaloproteasas",
    "senalizacion_intercelular": (
        "senalizacion autocrina, yuxtacrina, paracrina y endocrina"
    ),
    "receptores_y_transduccion": (
        "tipos de receptores, adaptadores, cascadas, redes y retroalimentacion"
    ),
    "senalizacion_localizada_y_balsas_lipidicas": (
        "microdominios de membrana y senalizaciones focales"
    ),
    "camp_pka_creb": "via de senalizacion cAMP-PKA-CREB",
    "plc_ip3_dag": "via de senalizacion PLC-IP3-DAG",
    "ras_mapk_erk": "via de senalizacion Ras-MAPKinasas (Erk)",
    "pi3k_akt": "via de senalizacion PI3K-Akt",
    "hormonas_esteroideas_hre": (
        "vias de hormonas esteroideas y dominios HRE en genes diana"
    ),
    "epha_ephrin": "senalizacion bidireccional EphA/B-EphrinA/B",
    "diferenciacion_celular": (
        "regulacion de la expresion genica en la diferenciacion celular"
    ),
    "potencialidad_evolutiva": "totipotencialidad, pluripotencialidad y destinos celulares",
    "divisiones_simetricas_y_asimetricas": (
        "divisiones simetricas y asimetricas y su relacion con destinos celulares"
    ),
    "stem_cells_y_clonacion": "stem cells y clonacion",
    "morfogenos_e_identidad_posicional": (
        "compromiso, especificacion, morfogenos e identidad de posicion"
    ),
    "apoptosis": "muerte celular programada y rol de caspasas",
    "biologia_celula_tumoral": (
        "fenotipo tumoral, neoplasia, invasion y control del crecimiento"
    ),
    "angiogenesis_y_metastasis": (
        "angiogenesis tumoral, metastasis y tropismo celular metastasico"
    ),
}

GENETICA_DESCRIPTIONS = {
    "genoma_humano": "tamano y organizacion del genoma humano nuclear y mitocondrial",
    "secuencias_adn": "ADN repetitivo, de secuencia unica, codificante y no codificante",
    "gen_locus_alelo": "conceptos de gen, locus, alelo, genotipo y fenotipo",
    "secuenciacion_sanger": "fundamentos y utilidad del metodo de Sanger",
    "secuenciacion_alto_rendimiento": (
        "metodos de secuenciacion de alto rendimiento y sus aplicaciones"
    ),
    "rnaseq_y_transcriptoma": (
        "RNA-seq y caracterizacion del transcriptoma"
    ),
    "encode_y_poblar": "aportes de los proyectos ENCODE y POBLAR Argentina",
    "mutaciones": "definicion, clasificacion y mecanismos mutacionales",
    "mutagenos": "agentes mutagenicos y mutaciones en la evolucion",
    "variantes_y_polimorfismos": (
        "wild type, variantes patogenicas, significado incierto y polimorfismos"
    ),
    "familias_genicas_y_pseudogenes": "familias genicas y pseudogenes",
    "mutaciones_somaticas_y_germinales": (
        "mutaciones somaticas, germinales y sus efectos fenotipicos"
    ),
    "mosaicismo": "concepto de mosaicismo",
    "anomalias_congenitas": (
        "anomalias congenitas monogenicas, cromosomicas, multifactoriales y ambientales"
    ),
    "heterogeneidad_y_fenocopias": "heterogeneidad genetica y fenocopias",
    "extraccion_adn": "extraccion de ADN aplicada a investigacion y diagnostico",
    "enzimas_restriccion_y_electroforesis": (
        "enzimas de restriccion y electroforesis de acidos nucleicos"
    ),
    "southern_blot": "fundamentos y utilidad del Southern blot",
    "pcr_alelo_especifico_y_rflp": (
        "PCR, PCR alelo especifico y RFLP"
    ),
    "haplotipos": "concepto de haplotipo",
    "bibliotecas_genicas_y_vectores": (
        "bibliotecas genicas y vectores en investigacion biomedica"
    ),
    "crispr_knockout_knockin": (
        "ratones knock-out y knock-in mediante CRISPR/Cas"
    ),
    "herencia_mendeliana": "bases de la herencia monogenica mendeliana",
    "autosomica_dominante": (
        "patron autosomico dominante y mecanismos moleculares asociados"
    ),
    "autosomica_recesiva": (
        "patron autosomico recesivo y mecanismos moleculares asociados"
    ),
    "correlacion_genotipo_fenotipo": "correlacion genotipo-fenotipo",
    "homocigota_heterocigota_hemicigota": (
        "homocigota, heterocigota, heterocigota compuesta y hemicigota"
    ),
    "penetrancia_expresividad_genes_modificadores": (
        "penetrancia incompleta, expresividad variable y genes modificadores"
    ),
    "consanguinidad_endogamia_y_pesquisa_neonatal": (
        "consanguinidad, endogamia y pesquisa neonatal"
    ),
    "diferenciacion_sexual_primaria": (
        "bases geneticas de la diferenciacion sexual primaria"
    ),
    "recombinacion_cromosomas_sexuales": (
        "recombinacion meiotica de cromosomas sexuales en individuos XY"
    ),
    "inactivacion_cromosoma_x": (
        "lyonizacion, XIC, XIST, fases de inactivacion y mantenimiento"
    ),
    "mosaico_y_escape_x": (
        "mosaico de inactivacion y regiones que escapan a la inactivacion del X"
    ),
    "herencia_ligada_x": "patrones de herencia ligada al X",
    "herencia_ligada_y": "patron de herencia ligada al cromosoma Y",
    "expansion_tripletes_y_anticipacion": (
        "mutaciones dinamicas por expansion de tripletes y anticipacion"
    ),
    "premutacion_y_mutacion_completa": (
        "alelos premutados y con mutacion completa"
    ),
    "impronta_genomica": (
        "imprinting, conversion de improntas y mecanismos moleculares"
    ),
    "disomia_uniparental": "disomia uniparental y alteraciones de impronta",
    "genoma_mitocondrial_y_herencia_mitocondrial": (
        "diferencias entre genoma mitocondrial y nuclear y herencia mitocondrial"
    ),
    "heteroplasmia_segregacion_umbral": (
        "heteroplasmia, segregacion replicativa y efecto umbral"
    ),
    "herencia_multifactorial": "caracteristicas de la herencia multifactorial",
    "poligenia_y_regresion_media": (
        "poligenia en rasgos continuos y regresion a la media"
    ),
    "hipotesis_umbral": "hipotesis del umbral",
    "snp_y_loci_predisponentes": (
        "SNP y estudio de loci predisponentes"
    ),
    "genetica_tumoral_esporadica_y_hereditaria": (
        "bases geneticas de tumores esporadicos y hereditarios"
    ),
    "cariotipo_humano_y_nomenclatura": "cariotipo humano y nomenclatura citogenetica",
    "cromatina_y_ciclo_celular": "estados de cromatina, cromosomas y ciclo celular",
    "tipos_de_cromosomas": (
        "cromosomas metacentricos, submetacentricos y acrocentricos"
    ),
    "bandeo_g_y_alta_resolucion": (
        "cariotipo con bandeo G y cariotipo de alta resolucion"
    ),
    "fish": "hibridacion in situ fluorescente (FISH)",
    "cgh_arrays": "micromatrices de ADN (CGH-arrays)",
    "mlpa": "MLPA como tecnica de citogenetica molecular",
    "anomalias_cromosomicas_numericas": (
        "aneuploidias y poliploidias"
    ),
    "no_disyuncion_y_mosaicismo_cromosomico": (
        "no disyuncion meiotica o mitotica y mosaicismos cromosomicos"
    ),
    "edad_materna_y_trisomias": (
        "edad materna avanzada y riesgo de trisomias"
    ),
    "poliploidias": "triploidias, tetraploidias y mecanismos involucrados",
    "anomalias_cromosomicas_estructurales": (
        "rearreglos balanceados y desbalanceados"
    ),
    "translocaciones_e_inversiones": (
        "translocaciones reciprocas, robertsonianas e inversiones"
    ),
    "deleciones_duplicaciones_e_isocromosomas": (
        "deleciones, duplicaciones, isocromosomas y cromosomas marcadores"
    ),
    "microdeleciones": "sindromes por microdelecion",
    "prevencion_en_genetica": (
        "prevencion primaria, secundaria, terciaria y opciones reproductivas"
    ),
    "pesquisa_portadores_y_test_presintomaticos": (
        "pesquisa de portadores y test presintomaticos"
    ),
    "diagnostico_prenatal": "diagnostico prenatal en genetica medica",
    "tratamientos_y_terapia_genica": (
        "tratamientos sintomaticos y basados en el defecto celular-molecular"
    ),
    "asesoramiento_genetico": "asesoramiento genetico y contexto sociocultural",
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

COMMON_BIOLOGY_QUESTION_TEMPLATE = (
    "You are a senior UBA professor specialized in Biology, Cell Biology, "
    "Molecular Biology, and Medical Genetics, and you write multiple-choice "
    "questions in the style of UBA exams.\n\n"
    "TASK:\n"
    "- Generate EXACTLY ONE high-quality biology multiple-choice question.\n"
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
    "- The stem must test only one concept.\n"
    "- Stay strictly inside the given subtopic and its description.\n"
    "- If the subtopic is narrow, adapt the question instead of expanding scope.\n"
    "- Do not output meta-text, warnings, placeholders, or error messages.\n"
    "- Do not write long clinical vignettes.\n"
    "- Short biomedical, experimental, or physiological contexts are allowed only when they directly support the concept being tested, as in UBA multiple-choice exams.\n"
    "- Prioritize pedagogical value in the explanations so the student learns the surrounding concept, not only the key.\n"
    "- Whenever a detection, study, amplification, sequencing, cytogenetic, or molecular biology technique appears, write its name in Spanish as used in Argentina.\n"
    "- If you use an acronym for a technique, the first mention must include the full term in Spanish followed by the acronym in parentheses.\n"
    "- Do not introduce English expansions of acronyms.\n"
    "- Do not use an English acronym when a clear Spanish wording is preferred; if the Spanish acronym is not reliably natural, write only the full term in Spanish.\n"
    "- If a disease, syndrome, or biomedical example appears, use it only when the "
    "subtopic explicitly supports it and ask about the biological or genetic basis, "
    "not about diagnosis, prognosis, or treatment details.\n\n"
    "UBA FORMAT RULES:\n"
    "- Mimic the wording style used in UBA Biology and Genetics multiple-choice exams.\n"
    "- Prefer stems such as: 'Respecto a...', 'Señale la afirmación correcta', 'Indique la opción incorrecta', '¿Cuál de las siguientes...?', or a short contextualized statement followed by a precise conceptual question.\n"
    "- The stem should usually be 1 sentence, or at most 2 short sentences if a brief context is needed.\n"
    "- When using context, make the final question explicit and concrete.\n"
    "- The answer options must look like UBA options: parallel in grammar, same conceptual level, and phrased as short statements or clauses rather than long paragraphs.\n"
    "- Avoid conversational phrasing, exaggerated didactic wording, and trivia-style formulations.\n"
    "- Do not use options such as 'todas las anteriores', 'ninguna de las anteriores', or overlapping alternatives.\n"
    "- Make distractors plausible in the same way UBA exams do: each one should be close to the topic but wrong because of one clear conceptual error.\n\n"
    "TECHNIQUE TERMINOLOGY EXAMPLES:\n"
    "- Prefer examples like 'reacción en cadena de la polimerasa (PCR)', 'retrotranscripción seguida de reacción en cadena de la polimerasa cuantitativa', 'hibridación fluorescente in situ', 'inmunofluorescencia', 'electroforesis', 'secuenciación automática por método de Sanger'.\n"
    "- Avoid formulations in English such as 'polymerase chain reaction', 'fluorescence in situ hybridization', 'western blot' expanded in English, or mixed Spanish-English names.\n\n"
    "DIVERSITY MODE HANDLING:\n"
    "- Use {DIVERSITY_MODE} only when it naturally fits the subtopic.\n"
    "- If {DIVERSITY_MODE} does not fit, silently convert it into the nearest valid "
    "biology angle inside the same subtopic.\n"
    "- Never force regulation, consequence, comparison, or application if the "
    "subtopic does not support it.\n\n"
    "OPTION DESIGN RULES:\n"
    "- There must be exactly one correct answer.\n"
    "- The 4 options must belong to the same conceptual category.\n"
    "- The 4 options must be mutually exclusive and non-overlapping.\n"
    "- The 4 options must match the grammar of the stem and read naturally as UBA-style alternatives.\n"
    "- No duplicated options, no partially correct options, and no controversial keys.\n"
    "- Distractors must be plausible but clearly incorrect.\n"
    "- Use precise biological terminology.\n\n"
    "EXPLANATION RULES:\n"
    "- Each explanation must explicitly mention the option it explains.\n"
    "- Correct option: explain why it is correct using biology-based reasoning and add the key contextual mechanism, sequence, structure-function relation, or conceptual background that helps the student understand the topic.\n"
    "- Incorrect options: explain why each one is incorrect in relation to the stem and, when useful, clarify what concept, process, structure, or inheritance pattern that option actually corresponds to.\n"
    "- Explanations must be more developed than a one-line justification, but still focused and directly tied to the question.\n"
    "- Prefer 2 to 4 sentences per explanation when needed for clarity.\n"
    "- Do not simply restate the option; teach the concept behind it.\n"
    "- The correct explanation must match the selected correct letter.\n\n"
    "QUESTION CONSTRUCTION ORDER:\n"
    "1. Choose one fact fully supported by the subtopic.\n"
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

BIOLOGIA_CELULAR_Y_MOLECULAR_TOPIC_RULES = (
    "- Limit content to UBA Cell Biology and Molecular Biology topics: DNA "
    "maintenance and variability, gene expression, experimental techniques, "
    "compartmentalization, biomembranes, cytoskeleton, transport, bioenergetics, "
    "extracellular matrix, signaling, differentiation, apoptosis, and tumor cell "
    "biology exactly when supported by the subtopic.\n"
    "- Prefer question angles such as stages, mechanisms, molecular participants, "
    "regulatory logic, compartment localization, transport route, pathway sequence, "
    "cytoskeletal role, organelle function, or experimental purpose when the "
    "subtopic allows it.\n"
    "- Do not ask about histology, embryology, or full clinical management.\n"
    "- For techniques, keep options within the same category of method, step, "
    "molecule detected, or application.\n"
    "- For signaling, keep options within the same category of receptor, messenger, "
    "kinase, transcription factor, or pathway output.\n"
    "- For organelles, cytoskeleton, and membranes, keep options within the same "
    "category of structure, function, transport mode, motor protein, or associated "
    "molecular event."
)

GENETICA_TOPIC_RULES = (
    "- Limit content to UBA Medical Genetics topics: human genome, mutations, "
    "molecular techniques, classical and non-classical inheritance, multifactorial "
    "inheritance, cytogenetics, chromosomopathies, prevention, counseling, and "
    "ethical aspects exactly when supported by the subtopic.\n"
    "- Prefer question angles such as inheritance mechanism, mutation class, "
    "molecular basis, genome organization, sequence interpretation, cytogenetic "
    "technique, chromosomal mechanism, recurrence risk principle, or counseling "
    "concept when the subtopic allows it.\n"
    "- Disease names may appear only when the subtopic explicitly supports them, "
    "and the stem must focus on the genetic mechanism or conceptual principle.\n"
    "- Do not ask about treatment protocols, prognosis details, or unrelated "
    "clinical management.\n"
    "- For inheritance questions, keep options within the same category of pattern, "
    "mechanism, allele state, or pedigree-compatible concept.\n"
    "- For cytogenetics and molecular techniques, keep options within the same "
    "category of method, detectable alteration, chromosomal event, or laboratory use."
)


def build_biology_question_prompt(topic_rules: str) -> str:
    """Build a topic-specific prompt from the common biology template."""
    return COMMON_BIOLOGY_QUESTION_TEMPLATE.replace("{TOPIC_RULES}", topic_rules)


BIOLOGIA_CELULAR_Y_MOLECULAR_QUESTION = build_biology_question_prompt(
    BIOLOGIA_CELULAR_Y_MOLECULAR_TOPIC_RULES
)
GENETICA_QUESTION = build_biology_question_prompt(GENETICA_TOPIC_RULES)

BIOLOGY_QUESTION_PROMPTS = {
    "Biologia Celular y Molecular": BIOLOGIA_CELULAR_Y_MOLECULAR_QUESTION,
    "Genetica": GENETICA_QUESTION,
}

BIOLOGY_QUESTION = BIOLOGIA_CELULAR_Y_MOLECULAR_QUESTION


def get_biology_question_prompt(parameter: str) -> str:
    """Return the prompt that best matches the requested biology topic."""
    return BIOLOGY_QUESTION_PROMPTS.get(parameter, BIOLOGY_QUESTION)
