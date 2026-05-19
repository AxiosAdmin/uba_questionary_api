import random

from src.helpers.biologia_questionary_text import (
    BIOLOGIA_CELULAR_Y_MOLECULAR_DESCRIPTIONS,
    GENETICA_DESCRIPTIONS,
)
from src.helpers.questions_text import (
    LOCOMOTOR_DESCRIPTIONS,
    SPLACHNOLOGY_DESCRIPTIONS,
    NEURO_DESCRIPTIONS,
)


def _pick_subtopic(descriptions):
    key = random.choice(list(descriptions.keys()))
    return [key, descriptions[key]]


def check_anatomy_sub_topic(parameter):
    if parameter == "Locomotor":
        return _pick_subtopic(LOCOMOTOR_DESCRIPTIONS)

    if parameter == "Neuroanatomy":
        return _pick_subtopic(NEURO_DESCRIPTIONS)

    if parameter == "Splanchnology":
        return _pick_subtopic(SPLACHNOLOGY_DESCRIPTIONS)

    raise ValueError(f"Unsupported anatomy topic: {parameter}")


def check_biology_sub_topic(parameter):
    if parameter == "Biologia Celular y Molecular":
        return _pick_subtopic(BIOLOGIA_CELULAR_Y_MOLECULAR_DESCRIPTIONS)

    if parameter == "Genetica":
        return _pick_subtopic(GENETICA_DESCRIPTIONS)

    raise ValueError(f"Unsupported biology topic: {parameter}")
