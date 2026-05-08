from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InstitutionBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {"id": "uuid_aqui", "name": "Universidade de SÃ£o Paulo"}
        },
    )

    id: UUID
    name: str
