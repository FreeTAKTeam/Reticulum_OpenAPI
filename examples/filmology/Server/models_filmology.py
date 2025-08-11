from dataclasses import dataclass
from typing import Optional

from reticulum_openapi.model import BaseModel
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MovieORM(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)


@dataclass
class Movie(BaseModel):
    """Representation of a film."""

    id: int
    title: str
    description: Optional[str] = None

    __orm_model__ = MovieORM


movie_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "auth_token": {"type": "string"},
    },
    "required": ["id", "title"],
}
