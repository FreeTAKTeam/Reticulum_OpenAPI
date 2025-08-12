from dataclasses import dataclass

from reticulum_openapi.model import (
    dataclass_from_json,
    dataclass_from_msgpack,
    dataclass_to_json,
    dataclass_to_msgpack
)


@dataclass
class Item:
    name: str
    value: int


@dataclass
class ItemList:
    items: List[Item]


def test_serialization_roundtrip():
    item = Item(name="foo", value=42)
    data = dataclass_to_msgpack(item)
    obj = dataclass_from_msgpack(Item, data)
    assert obj == item


def test_list_of_items_roundtrip():
    obj = ItemList(items=[Item(name="a", value=1), Item(name="b", value=2)])
    data = dataclass_to_msgpack(obj)
    reconstructed = dataclass_from_msgpack(ItemList, data)
    assert reconstructed == obj


def test_msgpack_roundtrip():
    item = Item(name="foo", value=42)
    data = dataclass_to_msgpack(item)
    obj = dataclass_from_msgpack(Item, data)
    assert obj == item


@dataclass
class BaseVehicle:
    manufacturer: str


@dataclass
class Car(BaseVehicle):
    doors: int


@dataclass
class Bike:
    handlebar: str


Vehicle = Union[Car, Bike]


@dataclass
class TransportRecord:
    owner: str
    vehicle: Vehicle


def test_union_deserialization_root():
    data = dataclass_to_msgpack(Car(manufacturer="Acme", doors=2))
    obj = dataclass_from_msgpack(Vehicle, data)
    assert isinstance(obj, Car)
    assert obj.doors == 2


def test_union_deserialization_nested():
    record = TransportRecord(owner="bob", vehicle=Bike(handlebar="drop"))
    data = dataclass_to_msgpack(record)
    obj = dataclass_from_msgpack(TransportRecord, data)
    assert isinstance(obj.vehicle, Bike)


Base = declarative_base()


class ItemORM(Base):
    __tablename__ = "items_model"
    id = Column(Integer, primary_key=True)
    name = Column(String)


@dataclass
class ItemRecord(BaseModel):
    id: int
    name: str
    __orm_model__ = ItemORM


@pytest.mark.asyncio
async def test_update_returns_dataclass_instance():
    """Ensure ``update`` returns a dataclass instance."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await ItemRecord.create(session, id=1, name="old")
        updated = await ItemRecord.update(session, 1, name="new")
        assert isinstance(updated, ItemRecord)
        assert updated.name == "new"
