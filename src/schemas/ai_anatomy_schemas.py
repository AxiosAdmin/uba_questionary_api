from enum import Enum

from pydantic import BaseModel, ConfigDict


class ParameterEnum(str, Enum):
    """Enumeration of allowed anatomy topics for question generation."""

    NEURO = "Neuroanatomy"
    ESPLACNO = "Splanchnology"
    LOCOMOTOR = "Locomotor"


class AnatomySchema(BaseModel):
    """Schema for anatomy question generation request."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {"parameter": "Neuroanatomy | Splanchnology | Locomotor"}
        },
    )

    parameter: ParameterEnum
