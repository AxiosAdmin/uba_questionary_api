from uuid import UUID
from pydantic import BaseModel


class InstitutionBase(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"id": "uuid_aqui", "name": "Universidade de São Paulo"}
        }
