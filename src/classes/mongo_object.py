from abc import ABC, abstractmethod
from logging import getLogger
from typing import Generic, TypeVar, Type, Optional, AsyncIterator, TYPE_CHECKING

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.results import UpdateResult, DeleteResult

if TYPE_CHECKING:
    from src.bot import Krabbe

T = TypeVar("T", bound="MongoObject")


class MongoObject(ABC, Generic[T]):
    collection_name: str
    __logger = getLogger("krabbe.mongo")

    def __init__(self, bot: "Krabbe", database: AsyncIOMotorDatabase):
        self.bot: "Krabbe" = bot
        self.database: AsyncIOMotorDatabase = database

    @abstractmethod
    def unique_identifier(self) -> dict:
        """
        Returns a dictionary representing the unique identifier for the document.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the document to be upserted.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

    async def upsert(self) -> UpdateResult:
        """
        Updates or inserts a document in the collection.

        :return: The UpdateResult of the update operation.
        """
        self.__logger.info(
            f"Upserting {self.__class__.collection_name} document: {self.to_dict()}"
        )

        data = self.to_dict()

        return await self.database.get_collection(self.__class__.collection_name).update_one(
            self.unique_identifier(),
            {"$set": data},
            upsert=True
        )

    async def delete(self) -> DeleteResult:
        """
        Deletes this document from the collection.

        :return: The DeleteResult of the delete operation.
        """
        self.__logger.info(
            f"Deleting {self.__class__.collection_name} document: {self.unique_identifier()}"
        )

        return await self.database.get_collection(self.__class__.collection_name).delete_one(
            self.unique_identifier()
        )

    @classmethod
    async def find_one(cls: Type[T], bot: "Krabbe", database: AsyncIOMotorDatabase, **kwargs) -> Optional[T]:
        """
        Find a document in the collection that matches the specified query.
        """
        cls.__logger.info(f"Finding one {cls.collection_name} document: {kwargs}")

        document = await database.get_collection(cls.collection_name).find_one(kwargs)

        if not document:
            return None

        # noinspection PyUnresolvedReferences
        del document["_id"]

        return cls(bot=bot, database=database, **document)

    @classmethod
    async def find(cls: Type[T], bot: "Krabbe", database: AsyncIOMotorDatabase, **kwargs) -> AsyncIterator[T]:
        """
        Find all documents in the collection that match the specified query.
        """
        cls.__logger.info(f"Finding {cls.collection_name} documents: {kwargs}")

        cursor = database.get_collection(cls.collection_name).find(kwargs)

        async for document in cursor:
            del document["_id"]

            yield cls(bot=bot, database=database, **document)
