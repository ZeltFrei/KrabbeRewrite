from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.results import UpdateResult, DeleteResult

from src.bot import Krabbe

T = TypeVar("T", bound="MongoObject")


class MongoObject(ABC, Generic[T]):
    collection_name: str

    def __init__(self, database: AsyncIOMotorDatabase):
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
        return await self.database.get_collection(self.__class__.collection_name).delete_one(
            self.unique_identifier()
        )

    @classmethod
    async def find_one(cls: Type[T], database: AsyncIOMotorDatabase, **kwargs) -> Optional[T]:
        """
        Find a document in the collection that matches the specified query.
        """
        document = await database.get_collection(cls.collection_name).find_one(kwargs)
        if document:
            return cls(database=database, **document)
        return None

    @classmethod
    async def find(cls: Type[T], database: AsyncIOMotorDatabase, **kwargs) -> List[T]:
        """
        Find all documents in the collection that match the specified query.
        """
        cursor = database.get_collection(cls.collection_name).find(kwargs)
        return [cls(database=database, **doc) async for doc in cursor]
