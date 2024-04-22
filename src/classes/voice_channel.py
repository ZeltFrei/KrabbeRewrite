from typing import Optional

import disnake
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.bot import Krabbe
from src.classes.mongo_object import MongoObject


class VoiceChannel(MongoObject):
    collection_name = "voice_channels"

    def __init__(self, bot: Krabbe, database: AsyncIOMotorDatabase, channel_id: int, owner_id: int):
        super().__init__(bot, database)

        self.channel_id: int = channel_id
        self.owner_id: int = owner_id

        self._channel: Optional[disnake.VoiceChannel] = None
        self._owner: Optional[disnake.Member] = None

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

    async def remove(self) -> None:
        """
        Remove the voice channel from both bot memory and the database. And delete the channel.
        :return: None
        """
        await self.delete()

    async def resolve(self, bot: Krabbe) -> "VoiceChannel":
        """
        Resolves the channel and owner objects.

        :param bot: The Krabbe bot instance.
        :return: The resolved VoiceChannel object.
        """
        self._channel = bot.get_channel(self.channel_id)
        self._owner = self.channel.guild.get_member(self.owner_id)

        return self
