import datetime
from logging import getLogger
from typing import Optional, TYPE_CHECKING, Dict, AsyncIterator, Union

from disnake import Guild, CategoryChannel, VoiceChannel, Role, Webhook, ForumChannel, Message, Thread, AllowedMentions, \
    Embed, Color
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.results import UpdateResult, DeleteResult

from src.classes.mongo_object import MongoObject
from src.errors import FailedToResolve
from src.utils import is_same_day

if TYPE_CHECKING:
    from src.bot import Krabbe
    from src.classes.voice_channel import VoiceChannel as KrabbeVoiceChannel


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
            settings_event_logging_thread_id: int,
            voice_event_logging_thread_id: int,
            message_logging_channel_id: int,
            message_logging_webhook_url: str,
            allow_nsfw: bool,
            lock_message_dm: bool
    ):
        super().__init__(bot, database)

        self.guild_id: int = guild_id
        self.category_channel_id: int = category_channel_id
        self.root_channel_id: int = root_channel_id
        self.base_role_id: int = base_role_id

        self.event_logging_channel_id: int = event_logging_channel_id
        self.settings_event_logging_thread_id: int = settings_event_logging_thread_id
        self.voice_event_logging_thread_id: int = voice_event_logging_thread_id

        self.message_logging_channel_id: int = message_logging_channel_id
        self.message_logging_webhook_url: str = message_logging_webhook_url

        self.allow_nsfw: bool = allow_nsfw
        self.lock_message_dm: bool = lock_message_dm

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
            "settings_event_logging_thread_id": self.settings_event_logging_thread_id,
            "voice_event_logging_thread_id": self.voice_event_logging_thread_id,
            "message_logging_channel_id": self.message_logging_channel_id,
            "message_logging_webhook_url": self.message_logging_webhook_url,
            "allow_nsfw": self.allow_nsfw,
            "lock_message_dm": self.lock_message_dm
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

    @property
    def settings_event_logging_thread(self) -> Optional[Thread]:
        if self.settings_event_logging_thread_id is None:
            return None

        thread = self.guild.get_thread(self.settings_event_logging_thread_id)

        if thread:
            return thread

        raise FailedToResolve(
            f"Failed to resolve settings event logging thread {self.settings_event_logging_thread_id}"
        )

    @property
    def voice_event_logging_thread(self) -> Optional[Thread]:
        if self.voice_event_logging_thread_id is None:
            return None

        thread = self.guild.get_thread(self.voice_event_logging_thread_id)

        if thread:
            return thread

        raise FailedToResolve(f"Failed to resolve voice event logging thread {self.voice_event_logging_thread_id}")

    def as_embed(self) -> Embed:
        """
        Generate a visual presentation as an embed for this guild settings object.

        :return: The embed object.
        """
        embed = Embed(
            title="⚙️ | 伺服器設定",
            color=Color.blurple(),
            description="這是這個伺服器的設定"
        )

        embed.add_field(name="📦 類別頻道", value=self.category_channel.mention)
        embed.add_field(name="➕ 根頻道", value=self.root_channel.mention)
        embed.add_field(name="👥 基礎身分組", value=self.base_role.mention)
        embed.add_field(name="📃 事件紀錄頻道", value=self.event_logging_channel.mention)
        embed.add_field(name="📃 設定事件紀錄討論串", value=self.settings_event_logging_thread.mention)
        embed.add_field(name="📃 語音事件紀錄討論串", value=self.voice_event_logging_thread.mention)
        embed.add_field(name="💬 訊息紀錄頻道", value=self.message_logging_channel.mention)
        embed.add_field(name="🔞 NSFW 允許", value="是" if self.allow_nsfw else "否")
        embed.add_field(name="🔒 鎖定訊息 DM", value="是" if self.lock_message_dm else "否")

        return embed

    @staticmethod
    async def ensure_divider(thread: Thread) -> Optional[Message]:
        """
        Ensure the divider of the day is created in the specific logging thread.

        :param thread: The event logging thread.
        :return: The divider message.
        """
        now = datetime.datetime.now()

        if thread.last_message is None:
            last_created_at = thread.created_at
        else:
            last_created_at = thread.last_message.created_at

        if is_same_day(last_created_at, now):
            return None

        message = await thread.send(
            f"> 以下為 **{now.strftime('%Y-%m-%d')}** 的事件記錄",
            allowed_mentions=AllowedMentions.none()
        )

        return message

    async def log_settings_event(
            self, prefix: str, channel: "KrabbeVoiceChannel", message: str, wait: bool = False
    ) -> Optional[Message]:
        """
        Log a message to the settings logging thread.

        :param prefix: The prefix of the message. Usually a emoji.
        :param channel: The voice channel.
        :param wait: Whether to wait for the message to be sent.
        :param message: The message to log.
        """
        await self.ensure_divider(self.settings_event_logging_thread)

        log_string = f"{prefix} | **{channel.channel.name}** | {message}"

        if wait:
            return await self.settings_event_logging_thread.send(log_string, allowed_mentions=AllowedMentions.none())

        _ = self.bot.loop.create_task(
            self.settings_event_logging_thread.send(log_string, allowed_mentions=AllowedMentions.none())
        )

        return None

    async def log_voice_event(
            self, prefix: str, channel: "KrabbeVoiceChannel", message: str, wait: bool = False
    ) -> Optional[Message]:
        """
        Log a message to the voice logging thread.

        :param prefix: The prefix of the message. Usually a emoji.
        :param channel: The voice channel.
        :param wait: Whether to wait for the message to be sent.
        :param message: The message to log.
        """
        await self.ensure_divider(self.voice_event_logging_thread)

        log_string = f"{prefix} | **{channel.channel.name}** | {message}"

        if wait:
            return await self.voice_event_logging_thread.send(log_string, allowed_mentions=AllowedMentions.none())

        _ = self.bot.loop.create_task(
            self.voice_event_logging_thread.send(log_string, allowed_mentions=AllowedMentions.none())
        )

        return None

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
    def get_from_cache(cls, **kwargs) -> Optional["GuildSettings"]:
        """
        Get the cached document that matches the specified query.

        :param kwargs: The query to match. Only guild_id is supported to query from cache.
        :return: The cached document.
        """
        if not kwargs.get("guild_id"):
            return None

        cached = cls._caches.get(kwargs["guild_id"])

        if not cached:
            return None

        for key, value in kwargs.items():
            if getattr(cached, key) != value:
                return None

        return cached

    @classmethod
    async def find_one(cls, bot: "Krabbe", database: AsyncIOMotorDatabase, **kwargs) -> Optional["GuildSettings"]:
        """
        Find a document in the collection that matches the specified query.
        """
        cls.__logger.info(f"Finding one {cls.collection_name} document: {kwargs}")

        if cached := cls.get_from_cache(**kwargs):
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
