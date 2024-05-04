import datetime
from logging import getLogger
from typing import Optional, TYPE_CHECKING, Dict, AsyncIterator

from disnake import Guild, CategoryChannel, VoiceChannel, Role, Webhook, ForumChannel, Message, ThreadArchiveDuration, \
    Thread, AllowedMentions
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.results import UpdateResult, DeleteResult

from src.classes.mongo_object import MongoObject
from src.errors import FailedToResolve
from src.utils import is_same_day

if TYPE_CHECKING:
    from src.bot import Krabbe


class GuildSettings(MongoObject):
    collection_name = "guild_settings"
    __logger = getLogger("krabbe.mongo")

    _caches: Dict[int, "GuildSettings"] = {}

    def __init__(
            self,
            bot: "Krabbe",
            database: AsyncIOMotorDatabase,
            guild_id: int,
            category_channel_id: int,
            root_channel_id: int,
            base_role_id: int,
            event_logging_channel_id: int,
            message_logging_channel_id: int,
            message_logging_webhook_url: str
    ):
        super().__init__(bot, database)

        self.guild_id: int = guild_id
        self.category_channel_id: int = category_channel_id
        self.root_channel_id: int = root_channel_id
        self.base_role_id: int = base_role_id
        self.event_logging_channel_id: int = event_logging_channel_id
        self.message_logging_channel_id: int = message_logging_channel_id
        self.message_logging_webhook_url: str = message_logging_webhook_url

        self._guild: Optional[Guild] = None
        self._category_channel: Optional[CategoryChannel] = None
        self._root_channel: Optional[VoiceChannel] = None
        self._base_role: Optional[Role] = None
        self._event_logging_channel: Optional[ForumChannel] = None
        self._message_logging_channel: Optional[VoiceChannel] = None
        self._message_logging_webhook: Optional[Webhook] = None

    def unique_identifier(self) -> dict:
        return {"guild_id": self.guild_id}

    def to_dict(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "category_channel_id": self.category_channel_id,
            "root_channel_id": self.root_channel_id,
            "base_role_id": self.base_role_id,
            "event_logging_channel_id": self.event_logging_channel_id,
            "message_logging_channel_id": self.message_logging_channel_id,
            "message_logging_webhook_url": self.message_logging_webhook_url
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
    def message_logging_channel(self) -> Optional[ForumChannel]:
        if self._message_logging_channel is None:
            self._message_logging_channel = self.guild.get_channel(self.message_logging_channel_id)

        elif self._message_logging_channel.id != self.message_logging_channel_id:
            self._message_logging_channel = self.guild.get_channel(self.message_logging_channel_id)

        if self._message_logging_channel:
            return self._message_logging_channel

        raise FailedToResolve(f"Failed to resolve logging channel {self.message_logging_channel_id}")

    @property
    def message_logging_webhook(self) -> Webhook:
        try:
            self._message_logging_webhook = Webhook.from_url(
                self.message_logging_webhook_url, session=self.bot.webhooks_client_session
            )
        except ValueError:
            raise FailedToResolve(f"Failed to resolve logging webhook {self.message_logging_webhook_url}")

        return self._message_logging_webhook

    @property
    def event_logging_channel(self) -> Optional[ForumChannel]:
        if self._event_logging_channel is None:
            self._event_logging_channel = self.guild.get_channel(self.event_logging_channel_id)

        elif self._event_logging_channel.id != self.event_logging_channel_id:
            self._event_logging_channel = self.guild.get_channel(self.event_logging_channel_id)

        if self._event_logging_channel:
            return self._event_logging_channel

        raise FailedToResolve(f"Failed to resolve event logging channel {self.event_logging_channel_id}")

    async def ensure_event_logging_thread(self) -> Thread:
        """
        Ensure the event logging thread is active.
        Create one if not found or expired.

        :return: The event logging thread.
        """
        thread = self.event_logging_channel.last_thread
        now = datetime.datetime.now()

        if not thread:
            thread = await self.event_logging_channel.create_thread(
                name=now.strftime("%Y-%m-%d"),
                auto_archive_duration=ThreadArchiveDuration.day
            )

        if not is_same_day(thread.created_at, now):
            await thread.edit(
                archived=True
            )

            thread = await self.event_logging_channel.create_thread(
                name=now.strftime("%Y-%m-%d"),
                auto_archive_duration=ThreadArchiveDuration.day
            )

        return thread

    async def log_event(self, message: str, wait: bool = False) -> Optional[Message]:
        """
        Log a message to the event logging channel.

        :param wait: Whether to wait for the message to be sent.
        :param message: The message to log.
        """
        thread = await self.ensure_event_logging_thread()

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_string = f"**{timestamp}**: {message}"

        if wait:
            return await thread.send(log_string, allowed_mentions=AllowedMentions.none())

        _ = self.bot.loop.create_task(
            thread.send(log_string, allowed_mentions=AllowedMentions.none())
        )

        return

    async def upsert(self) -> UpdateResult:
        """
        Updates or inserts a document in the collection.

        :return: The UpdateResult of the update operation.
        """
        self.__logger.info(
            f"Upserting {self.__class__.collection_name} document: {self.to_dict()}"
        )

        data = self.to_dict()

        self._caches[self.guild_id] = self

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

        del self._caches[self.guild_id]

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
            cached = cls._caches.get(guild_id)
            if cached:
                return cached

        document = await database.get_collection(cls.collection_name).find_one(kwargs)

        if not document:
            return None

        # noinspection PyUnresolvedReferences
        del document["_id"]

        guild_settings = cls(bot=bot, database=database, **document)

        cls._caches[guild_settings.guild_id] = guild_settings

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

            cls._caches[guild_settings.guild_id] = guild_settings

            yield guild_settings
