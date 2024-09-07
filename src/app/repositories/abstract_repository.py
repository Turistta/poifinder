from abc import ABC, abstractmethod

from models.base_models import HexUUIDString


class AbstractDatabase(ABC):
    @abstractmethod
    async def test(self):
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        raise NotImplementedError


class AbstractRepository[T](ABC):
    @abstractmethod
    async def find_one(self, id: HexUUIDString) -> T:
        raise NotImplementedError

    @abstractmethod
    async def add(self, **kwargs: object) -> T:
        raise NotImplementedError

    @abstractmethod
    async def update(self, id: str, **kwargs: object) -> T:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: str) -> bool:
        raise NotImplementedError
