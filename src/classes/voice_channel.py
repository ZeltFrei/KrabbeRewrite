from enum import Enum
from logging import getLogger
from typing import Optional, TYPE_CHECKING

import disnake
from disnake import Member, NotFound
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.classes.guild_settings import GuildSettings
from src.classes.mongo_object import MongoObject

if TYPE_CHECKING:
    from src.bot import Krabbe


class VoiceChannelState(Enum):
    PREPARING = 0
    READY = 1
    OWNER_DISCONNECT = 2
    DELETING = 3


class VoiceChannel(MongoObject):
    collection_name = "voice_channels"
    __logger = getLogger("krabbe.voice_channel")

    def __init__(self, bot: "Krabbe", database: AsyncIOMotorDatabase, channel_id: int, owner_id: int):
        super().__init__(bot, database)

        self.channel_id: int = channel_id
        self.owner_id: int = owner_id

        self._channel: Optional[disnake.VoiceChannel] = None
        self._owner: Optional[disnake.Member] = None

        self.resolved: bool = False

        self.state: VoiceChannelState = VoiceChannelState.PREPARING

    def unique_identifier(self) -> dict:
        return {"channel_id": self.channel_id}

    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "owner_id": self.owner_id
        }

    async def dispatch(self):
        match self.state:
            case _:
                pass

    @property
    def channel(self):
        if self._channel is None:
            raise ValueError("Channel is not resolved yet. Consider calling the resolve method.")
        return self._channel

    @property
    def owner(self):
        if self._owner is None:
            raise ValueError("Owner is not resolved yet. Consider calling the resolve method.")
        return self._owner

    @classmethod
    async def new(
            cls,
            bot: "Krabbe",
            database: AsyncIOMotorDatabase,
            guild_settings: GuildSettings,
            owner: Member
    ) -> "VoiceChannel":
        """
        Creates a new voice channel in the guild with the given owner.
        This method will create the channel, upsert the document to the database,
        then add the channel to the bot's memory.

        :param bot: The bot object.
        :param database: The database object.
        :param guild_settings: The guild settings object.
        :param owner: The owner of the channel.
        :return: The created VoiceChannel object.
        """
        if not guild_settings.resolved:
            raise ValueError("Guild settings must be resolved before creating a voice channel.")

        cls.__logger.info(f"Creating a new voice channel for {owner.name} in {guild_settings.guild.name}.")

        # TODO: Load owner's channel settings here

        created_channel = await guild_settings.category_channel.create_voice_channel(f"{owner.name} 的頻道")

        voice_channel = cls(
            bot=bot,
            database=database,
            channel_id=created_channel.id,
            owner_id=owner.id
        )

        await voice_channel.resolve()

        bot.voice_channels[voice_channel.channel_id] = voice_channel
        await voice_channel.upsert()

        return voice_channel

    async def remove(self) -> None:
        """
        Remove the voice channel from both bot memory and the database. And delete the channel.
        Note that `delete` method only deletes the document from the database. While this method deletes the whole channel.

        :return: None
        """
        try:
            self.bot.voice_channels.pop(self.channel_id)
        except KeyError:  # Forgive the channel if it's not in the bot's memory
            pass

        try:
            await self.channel.delete()
        except (NotFound, ValueError):  # Forgive the channel if it's already deleted or not resolved
            pass

        await self.delete()

    def is_resolved(self) -> bool:
        """
        Returns whether the channel and owner objects are resolved.
        :return: Boolean indicating whether the objects are resolved.
        """
        return self.resolved

    async def resolve(self) -> "VoiceChannel":
        """
        Resolves the channel and owner objects.

        :return: The resolved VoiceChannel object.
        """
        self._channel = self.bot.get_channel(self.channel_id)

        if not self._channel:
            raise ValueError("Channel is not found. Please check if the channel is still in the guild.")

        self._owner = self._channel.guild.get_member(self.owner_id)

        if not self._owner:
            raise ValueError("Owner is not found. Please check if the owner is still in the guild.")

        self.resolved = True

        return self
