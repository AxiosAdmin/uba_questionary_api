from enum import Enum

from pydantic import BaseModel, ConfigDict


class BiologyParameterEnum(str, Enum):
    """Enumeration of allowed biology topics for question generation."""

    BIOLOGIA_CELULAR_Y_MOLECULAR = "Biologia Celular y Molecular"
    GENETICA = "Genetica"


class BiologySchema(BaseModel):
    """Schema for biology question generation request."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "parameter": "Biologia Celular y Molecular | Genetica"
            }
        },
    )

    parameter: BiologyParameterEnum
