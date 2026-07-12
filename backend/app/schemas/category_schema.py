from datetime import datetime
import re
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class CategoryBase(BaseModel):
    category_name: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None


class CreateCategorySchema(CategoryBase):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "category_name": "Phones",
                    "parent_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                    "description": "Mobile hardware, smart cellular devices, and telephony systems.",
                }
            ]
        }
    }


class UpdateCategorySchema(BaseModel):
    category_name: Optional[str] = Field(None, min_length=2, max_length=20)
    slug: Optional[str] = Field(None, max_length=20)
    parent_id: Optional[UUID] = None
    description: Optional[str] = None

    @field_validator("slug")
    def validate_slug_format(cls, v: Optional[str]):
        if v is not None:
            if not v.islower() or not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError("Slug must contain only lowercase alphanumeric characters and hyphens")
        return v
    


class CategoryPublic(CategoryBase):
    category_id: UUID
    slug: str = Field(..., max_length=20)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "category_id": "4a3b2c1d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
                    "category_name": "Phones",
                    "slug": "phones",
                    "description": "Mobile hardware, smart cellular devices, and telephony systems.",
                    "parent_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
                }
            ]
        }
    }


