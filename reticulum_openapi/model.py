# reticulum_openapi/model.py
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import is_dataclass
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import get_args
from typing import get_origin

from .codec_msgpack import from_bytes as msgpack_from_bytes
from .codec_msgpack import to_canonical_bytes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

__all__ = [
    "dataclass_to_msgpack",
    "dataclass_from_msgpack",
    "dataclass_to_json",
    "dataclass_from_json",
    "dataclass_to_msgpack",
    "dataclass_from_msgpack",
    "BaseModel",
    "create_async_engine",
    "async_sessionmaker",
]

T = TypeVar("T")


def dataclass_to_json(data_obj: T) -> bytes:
    """Serialize a dataclass instance to compressed JSON bytes.

    Args:
        data_obj (T): Dataclass instance or primitive to serialise.

    Returns:
        bytes: Compressed JSON representation.
    """

    if is_dataclass(data_obj):
        data_dict = asdict(data_obj)
    else:
        data_dict = data_obj
    json_bytes = json.dumps(data_dict).encode("utf-8")
    return zlib.compress(json_bytes)


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


def dataclass_from_json(cls: Type[T], data: bytes) -> T:
    """Deserialize a dataclass instance from JSON bytes.


    Args:
        cls (Type[T]): Target dataclass type.
        data (bytes): JSON payload, optionally zlib-compressed.
    Returns:
        T: Deserialised dataclass instance.
    """
    if len(data) >= 2 and data[0] == 0x78:
        try:
            json_bytes = zlib.decompress(data)
        except zlib.error:
            json_bytes = data
    else:
        json_bytes = data
    obj_dict = json.loads(json_bytes.decode("utf-8"))
    return _construct(cls, obj_dict)


def dataclass_to_msgpack(data_obj: T) -> bytes:
    """Serialize a dataclass or primitive to canonical MessagePack bytes.

    Args:
        data_obj (T): Dataclass instance or primitive to serialise.

    Returns:
        bytes: Canonical MessagePack representation.
    """
    if is_dataclass(data_obj):
        data_obj = asdict(data_obj)
    return to_canonical_bytes(data_obj)


def dataclass_from_msgpack(cls: Type[T], data: bytes) -> T:
    """Deserialize a dataclass instance from MessagePack bytes.


    Args:
        cls (Type[T]): Target dataclass type.
        data (bytes): MessagePack-encoded payload.

    Returns:
        T: Deserialised dataclass instance.
    """
    obj_dict = msgpack_from_bytes(data)
    return _construct(cls, obj_dict)


def dataclass_from_json(cls: Type[T], data: bytes) -> T:
    """Deprecated wrapper for :func:`dataclass_from_msgpack`."""
    return dataclass_from_msgpack(cls, data)


@dataclass
class BaseModel:
    """
    Base data model providing serialization utilities and generic CRUD operations
    if __orm_model__ is defined on subclasses.
    """

    # Subclasses should set this to their SQLAlchemy ORM model class
    __orm_model__ = None

    def to_msgpack(self) -> bytes:
        """Serialize this dataclass to MessagePack bytes.

        Returns:
            bytes: MessagePack-encoded representation of this instance.
        """
        return dataclass_to_msgpack(self)

    def to_json_bytes(self) -> bytes:
        """Deprecated wrapper for :meth:`to_msgpack`."""
        return self.to_msgpack()

    @classmethod
    def from_msgpack(cls: Type[T], data: bytes) -> T:
        """Deserialize MessagePack bytes to a dataclass instance.

        Args:
            data (bytes): MessagePack-encoded payload.

        Returns:
            T: Instance of ``cls`` built from ``data``.
        """
        return dataclass_from_msgpack(cls, data)

    @classmethod
    def from_json_bytes(cls: Type[T], data: bytes) -> T:
        """Deprecated wrapper for :meth:`from_msgpack`."""
        return cls.from_msgpack(data)

    def to_msgpack_bytes(self) -> bytes:
        """Serialize this dataclass to MessagePack bytes."""
        return dataclass_to_msgpack(self)

    @classmethod
    def from_msgpack_bytes(cls: Type[T], data: bytes) -> T:
        """Deserialize MessagePack bytes to a dataclass instance."""
        return dataclass_from_msgpack(cls, data)

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
            raise NotImplementedError(
                "Subclasses must define __orm_model__ for persistence"
            )
        obj = cls.__orm_model__(**kwargs)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return cls.from_orm(obj)

    @classmethod
    async def get(cls, session: AsyncSession, id_) -> Optional[T]:
        """Retrieve a record by primary key.

        Args:
            session (AsyncSession): Database session.
            id_: Primary key of the record to fetch.

        Returns:
            Optional[T]: Dataclass instance or ``None`` if not found.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError(
                "Subclasses must define __orm_model__ for persistence"
            )
        orm_obj = await session.get(cls.__orm_model__, id_)
        if orm_obj is None:
            return None
        return cls.from_orm(orm_obj)

    @classmethod
    async def list(cls, session: AsyncSession, **filters) -> List[T]:
        """List records matching given filters.

        Filters should correspond to model attributes.

        Returns:
            List[T]: Dataclass instances matching the filters.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError(
                "Subclasses must define __orm_model__ for persistence"
            )
        stmt = select(cls.__orm_model__)
        for attr, value in filters.items():
            stmt = stmt.where(getattr(cls.__orm_model__, attr) == value)
        result = await session.execute(stmt)
        return [cls.from_orm(obj) for obj in result.scalars().all()]

    @classmethod
    async def update(cls, session: AsyncSession, id_, **kwargs) -> Optional[T]:
        """Update fields on a record by primary key.

        Args:
            session (AsyncSession): Database session.
            id_: Primary key of the record to update.
            **kwargs: Fields and values to set on the record.

        Returns:
            Optional[T]: Updated dataclass instance or ``None`` if not found.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError(
                "Subclasses must define __orm_model__ for persistence"
            )
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
    async def delete(cls, session: AsyncSession, id_) -> bool:
        """
        Delete a record by primary key.
        Returns True if deleted, False if not found.
        """
        if cls.__orm_model__ is None:
            raise NotImplementedError(
                "Subclasses must define __orm_model__ for persistence"
            )
        orm_obj = await session.get(cls.__orm_model__, id_)
        if orm_obj is None:
            return False
        await session.delete(orm_obj)
        await session.commit()
        return True
