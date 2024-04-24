from typing import Optional, TYPE_CHECKING

from disnake import Guild, CategoryChannel, VoiceChannel, Role
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.classes.mongo_object import MongoObject
from src.errors import FailedToResolve

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
            root_channel_id: int,
            base_role_id: int
    ):
        super().__init__(bot, database)

        self.guild_id: int = guild_id
        self.category_channel_id: int = category_channel_id
        self.root_channel_id: int = root_channel_id
        self.base_role_id: int = base_role_id

        self._guild: Optional[Guild] = None
        self._category_channel: Optional[CategoryChannel] = None
        self._root_channel: Optional[VoiceChannel] = None
        self._base_role: Optional[Role] = None

    def unique_identifier(self) -> dict:
        return {"guild_id": self.guild_id}

    def to_dict(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "category_channel_id": self.category_channel_id,
            "root_channel_id": self.root_channel_id,
            "base_role_id": self.base_role_id
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
