from typing import Optional, TYPE_CHECKING

from disnake import Guild, CategoryChannel, VoiceChannel
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.classes.mongo_object import MongoObject

if TYPE_CHECKING:
    from src.bot import Krabbe


class GuildSettings(MongoObject):
    collection_name = "guild_settings"

    def __init__(
            self,
            bot: "Krabbe",
            database: AsyncIOMotorDatabase,
            guild_id: int,
            category_channel_id: int,
            root_channel_id: int
    ):
        super().__init__(bot, database)

        self.guild_id: int = guild_id
        self.category_channel_id: int = category_channel_id
        self.root_channel_id: int = root_channel_id

        self._guild: Optional[Guild] = None
        self._category_channel: Optional[CategoryChannel] = None
        self._root_channel: Optional[VoiceChannel] = None

        self.resolved: bool = False

    def unique_identifier(self) -> dict:
        return {"guild_id": self.guild_id}

    def to_dict(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "category_channel_id": self.category_channel_id,
            "root_channel_id": self.root_channel_id
        }

    @property
    def guild(self) -> Guild:
        if self._guild is None:
            raise ValueError("Guild is not resolved yet. Consider calling the resolve method.")
        return self._guild

    @property
    def category_channel(self) -> CategoryChannel:
        if self._category_channel is None:
            raise ValueError("Category channel is not resolved yet. Consider calling the resolve method.")
        return self._category_channel

    @property
    def root_channel(self) -> VoiceChannel:
        if self._root_channel is None:
            raise ValueError("Root channel is not resolved yet. Consider calling the resolve method.")
        return self._root_channel

    def is_resolved(self) -> bool:
        """
        Returns whether the guild, category channel, and root channel objects are resolved.
        :return: Boolean indicating whether the objects are resolved.
        """
        return self.resolved

    async def resolve(self) -> "GuildSettings":
        """
        Resolves the guild, category channel, and root channel objects.

        :return: The resolved GuildSettings object.
        """
        self._guild = self.bot.get_guild(self.guild_id)
        self._category_channel = self._guild.get_channel(self.category_channel_id)
        self._root_channel = self._guild.get_channel(self.root_channel_id)

        if any([not self._guild, not self._category_channel, not self._root_channel]):
            raise ValueError("One or more objects could not be resolved.")

        self.resolved = True

        return self
