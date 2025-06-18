# reticulum_openapi/model.py
from dataclasses import dataclass, asdict, is_dataclass
import json, zlib
from typing import Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar('T')

def dataclass_to_json(data_obj: T) -> bytes:
    """
    Serialize a dataclass instance to a compressed JSON byte string.
    """
    # Convert dataclass to dict, then to JSON string
    if is_dataclass(data_obj):
        data_dict = asdict(data_obj)
    else:
        # If it's already a dict (or primitive), use as is
        data_dict = data_obj
    json_str = json.dumps(data_dict)
    # Compress the JSON bytes to minimize payload size
    json_bytes = json_str.encode('utf-8')
    compressed = zlib.compress(json_bytes)
    return compressed

def dataclass_from_json(cls: Type[T], data: bytes) -> T:
    """
    Deserialize a dataclass instance from a compressed JSON byte string.
    """
    try:
        json_bytes = zlib.decompress(data)
    except zlib.error:
        # Data might not be compressed; use raw bytes if decompression fails
        json_bytes = data
    json_str = json_bytes.decode('utf-8')
    obj_dict = json.loads(json_str)
    # Instantiate dataclass by unpacking dict (assumes keys match field names)
    return cls(**obj_dict)  # type: ignore

@dataclass
class BaseModel:
    """
    Base data model providing serialization utilities and generic CRUD operations
    if __orm_model__ is defined on subclasses.
    """
    # Subclasses should set this to their SQLAlchemy ORM model class
    __orm_model__ = None

    def to_json_bytes(self) -> bytes:
        """Serialize this dataclass to compressed JSON bytes."""
        return dataclass_to_json(self)

    @classmethod
    def from_json_bytes(cls: Type[T], data: bytes) -> T:
        """Deserialize compressed JSON bytes to a dataclass instance."""
        return dataclass_from_json(cls, data)

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs):
        """
        Create and persist a new record using the associated ORM model.
        Returns the ORM instance.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        obj = cls.__orm_model__(**kwargs)
        session.add(obj)
        await session.commit()
        return obj

    @classmethod
    async def get(cls, session: AsyncSession, id_):
        """
        Retrieve a record by primary key using the ORM model.
        Returns the ORM instance or None.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        return await session.get(cls.__orm_model__, id_)

    @classmethod
    async def list(cls, session: AsyncSession, **filters):
        """
        List records matching given filters using the ORM model.
        Filters should correspond to model attributes.
        Returns a list of ORM instances.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        stmt = select(cls.__orm_model__)
        for attr, value in filters.items():
            stmt = stmt.where(getattr(cls.__orm_model__, attr) == value)
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def update(cls, session: AsyncSession, id_, **kwargs):
        """
        Update fields of a record identified by primary key.
        Returns the updated ORM instance or None if not found.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        obj = await cls.get(session, id_)
        if obj is None:
            return None
        for attr, value in kwargs.items():
            setattr(obj, attr, value)
        session.add(obj)
        await session.commit()
        return obj

    @classmethod
    async def delete(cls, session: AsyncSession, id_):
        """
        Delete a record by primary key.
        Returns True if deleted, False if not found.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        obj = await cls.get(session, id_)
        if obj is None:
            return False
        await session.delete(obj)
        await session.commit()
        return True
