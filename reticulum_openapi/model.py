# reticulum_openapi/model.py
from dataclasses import dataclass, asdict, is_dataclass, fields
import json
import zlib
from typing import Type, TypeVar, get_origin, get_args, Union
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

__all__ = [
    "dataclass_to_json",
    "dataclass_from_json",
    "BaseModel",
    "create_async_engine",
    "async_sessionmaker",
]

T = TypeVar('T')

# not a fan of the design of this file and compromises it makes
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
    # shouldn't this be done at the edge, also probably not great to have the compression logic baked into 
    # the logic to go to/from json
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

        # Using exception handling as a fallback for an inconsistent and/or 
        # poorly defined interface is bad practice
        json_bytes = data
    json_str = json_bytes.decode('utf-8')
    obj_dict = json.loads(json_str)

    def _construct(tp, value):
        origin = get_origin(tp)
        if origin is Union:
            for sub in get_args(tp):
                try:
                    return _construct(sub, value)
                except Exception:
                    continue
            raise ValueError(f"No matching type for Union {tp}")
        if is_dataclass(tp):
            kwargs = {}
            for f in fields(tp):
                if isinstance(value, dict) and f.name in value:
                    kwargs[f.name] = _construct(f.type, value[f.name])
            return tp(**kwargs)  # type: ignore
        if origin is list and isinstance(value, list):
            item_type = get_args(tp)[0]
            return [_construct(item_type, v) for v in value]
        return value

    return _construct(cls, obj_dict)


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

    def to_orm(self):
        """Create an ORM instance from this dataclass."""
        if self.__orm_model__ is None:
            raise NotImplementedError(
                "Subclasses must define __orm_model__ for persistence"
            )
        return self.__orm_model__(**asdict(self))

    @classmethod
    def from_orm(cls: Type[T], orm_obj) -> T:
        """Instantiate a dataclass from an ORM row."""
        kwargs = {f.name: getattr(orm_obj, f.name) for f in fields(cls)}
        return cls(**kwargs)

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> T:
        """
        Create and persist a new record using the associated ORM model.
        Returns the dataclass instance.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        obj = cls.__orm_model__(**kwargs)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return cls.from_orm(obj)

    @classmethod
    async def get(cls, session: AsyncSession, id_):
        """
        Retrieve a record by primary key using the ORM model.
        Returns the ORM instance or None.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        orm_obj = await session.get(cls.__orm_model__, id_)
        if orm_obj is None:
            return None
        return cls.from_orm(orm_obj)

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
        return [cls.from_orm(obj) for obj in result.scalars().all()]

    @classmethod
    async def update(cls, session: AsyncSession, id_, **kwargs):
        """
        Update fields of a record identified by primary key.
        Returns the updated ORM instance or None if not found.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        orm_obj = await session.get(cls.__orm_model__, id_)
        if orm_obj is None:
            return None
        for attr, value in kwargs.items():
            setattr(orm_obj, attr, value)
        session.add(orm_obj)
        await session.commit()
        await session.refresh(orm_obj)
        return cls.from_orm(orm_obj)

    @classmethod
    async def delete(cls, session: AsyncSession, id_):
        """
        Delete a record by primary key.
        Returns True if deleted, False if not found.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError("Subclasses must define __orm_model__ for persistence")
        orm_obj = await session.get(cls.__orm_model__, id_)
        if orm_obj is None:
            return False
        await session.delete(orm_obj)
        await session.commit()
        return True
