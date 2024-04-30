from logging import getLogger
from typing import Optional, TYPE_CHECKING, Dict, AsyncIterator

from disnake import Guild, CategoryChannel, VoiceChannel, Role, Webhook, ForumChannel
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.results import UpdateResult, DeleteResult

from src.classes.mongo_object import MongoObject
from src.errors import FailedToResolve

if TYPE_CHECKING:
    from src.bot import Krabbe


class GuildSettings(MongoObject):
    collection_name = "guild_settings"
    __logger = getLogger("krabbe.mongo")

    __caches: Dict[int, "GuildSettings"] = {}

    def __init__(
            self,
            bot: "Krabbe",
            database: AsyncIOMotorDatabase,
            guild_id: int,
            category_channel_id: int,
            root_channel_id: int,
            base_role_id: int,
            logging_channel_id: int,
            logging_webhook_url: str
    ):
        super().__init__(bot, database)

        self.guild_id: int = guild_id
        self.category_channel_id: int = category_channel_id
        self.root_channel_id: int = root_channel_id
        self.base_role_id: int = base_role_id
        self.logging_channel_id: int = logging_channel_id
        self.logging_webhook_url: str = logging_webhook_url

        self._guild: Optional[Guild] = None
        self._category_channel: Optional[CategoryChannel] = None
        self._root_channel: Optional[VoiceChannel] = None
        self._base_role: Optional[Role] = None
        self._logging_channel: Optional[VoiceChannel] = None
        self._logging_webhook: Optional[Webhook] = None

    def unique_identifier(self) -> dict:
        return {"guild_id": self.guild_id}

    def to_dict(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "category_channel_id": self.category_channel_id,
            "root_channel_id": self.root_channel_id,
            "base_role_id": self.base_role_id,
            "logging_channel_id": self.logging_channel_id,
            "logging_webhook_url": self.logging_webhook_url
        }

    @property
    def guild(self) -> Optional[Guild]:
        if self._guild is None:
            self._guild = self.bot.get_guild(self.guild_id)

        elif self._guild.id != self.guild_id:
            self._guild = self.bot.get_guild(self.guild_id)

        return self._guild

    @property
    def category_channel(self) -> Optional[CategoryChannel]:
        if self._category_channel is None:
            self._category_channel = self.guild.get_channel(self.category_channel_id)

        elif self._category_channel.id != self.category_channel_id:
            self._category_channel = self.guild.get_channel(self.category_channel_id)

        if self._category_channel:
            return self._category_channel

        raise FailedToResolve(f"Failed to resolve category channel {self.category_channel_id}")

    @property
    def root_channel(self) -> VoiceChannel:
        if self._root_channel is None:
            self._root_channel = self.guild.get_channel(self.root_channel_id)

        elif self._root_channel.id != self.root_channel_id:
            self._root_channel = self.guild.get_channel(self.root_channel_id)

        if self._root_channel:
            return self._root_channel

        raise FailedToResolve(f"Failed to resolve root channel {self.root_channel_id}")

    @property
    def base_role(self) -> Optional[Role]:
        if self._base_role is None:
            self._base_role = self.guild.get_role(self.base_role_id)

        elif self._base_role.id != self.base_role_id:
            self._base_role = self.guild.get_role(self.base_role_id)

        if self._base_role:
            return self._base_role

        raise FailedToResolve(f"Failed to resolve base role {self.base_role_id}")

    @property
    def logging_channel(self) -> Optional[ForumChannel]:
        if self._logging_channel is None:
            self._logging_channel = self.guild.get_channel(self.logging_channel_id)

        elif self._logging_channel.id != self.logging_channel_id:
            self._logging_channel = self.guild.get_channel(self.logging_channel_id)

        if self._logging_channel:
            return self._logging_channel

        raise FailedToResolve(f"Failed to resolve logging channel {self.logging_channel_id}")

    @property
    def logging_webhook(self) -> Webhook:
        try:
            self._logging_webhook = Webhook.from_url(self.logging_webhook_url, session=self.bot.webhooks_client_session)
        except ValueError:
            raise FailedToResolve(f"Failed to resolve logging webhook {self.logging_webhook_url}")

        return self._logging_webhook

    async def upsert(self) -> UpdateResult:
        """
        Updates or inserts a document in the collection.

        :return: The UpdateResult of the update operation.
        """
        self.__logger.info(
            f"Upserting {self.__class__.collection_name} document: {self.to_dict()}"
        )

        data = self.to_dict()

        self.__caches[self.guild_id] = self

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

        del self.__caches[self.guild_id]

        return await self.database.get_collection(self.__class__.collection_name).delete_one(
            self.unique_identifier()
        )

    @classmethod
    async def find_one(cls, bot: "Krabbe", database: AsyncIOMotorDatabase, **kwargs) -> Optional["GuildSettings"]:
        """
        Find a document in the collection that matches the specified query.
        """
        cls.__logger.info(f"Finding one {cls.collection_name} document: {kwargs}")

        if guild_id := kwargs.get("guild_id"):
            cached = cls.__caches.get(guild_id)
            if cached:
                return cached

        document = await database.get_collection(cls.collection_name).find_one(kwargs)

        if not document:
            return None

        # noinspection PyUnresolvedReferences
        del document["_id"]

        guild_settings = cls(bot=bot, database=database, **document)

        cls.__cache[guild_settings.guild_id] = guild_settings

        return guild_settings

    @classmethod
    async def find(cls, bot: "Krabbe", database: AsyncIOMotorDatabase, **kwargs) -> AsyncIterator["GuildSettings"]:
        """
        Find all documents in the collection that match the specified query.
        """
        cls.__logger.info(f"Finding {cls.collection_name} documents: {kwargs}")

        cursor = database.get_collection(cls.collection_name).find(kwargs)

        async for document in cursor:
            del document["_id"]

            guild_settings = cls(bot=bot, database=database, **document)
            
cls.__cache[guild_settings.guild_id] = guild_settings
            yield guild_settings