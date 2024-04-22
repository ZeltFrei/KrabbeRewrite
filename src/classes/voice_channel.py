import asyncio
import random
from asyncio import Task
from enum import Enum
from logging import getLogger
from typing import Optional, TYPE_CHECKING, Callable

import disnake
from disnake import Member, NotFound, VoiceState
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.classes.guild_settings import GuildSettings
from src.classes.mongo_object import MongoObject

if TYPE_CHECKING:
    from src.bot import Krabbe


class VoiceChannelState(Enum):
    READY = 0
    USING = 1
    OWNER_DISCONNECTED = 2
    EMPTY = 3


class VoiceChannel(MongoObject):
    collection_name = "voice_channels"
    logger = getLogger("krabbe.voice_channel")

    def __init__(
            self, bot: "Krabbe",
            database: AsyncIOMotorDatabase,
            channel_id: int,
            owner_id: int
    ):
        super().__init__(bot, database)

        self.channel_id: int = channel_id
        self.owner_id: int = owner_id

        self._channel: Optional[disnake.VoiceChannel] = None
        self._owner: Optional[disnake.Member] = None

        self.resolved: bool = False

        self.state: VoiceChannelState = VoiceChannelState.READY
        self.loop: Optional[Task] = None

    def unique_identifier(self) -> dict:
        return {"channel_id": self.channel_id}

    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "owner_id": self.owner_id
        }

    async def apply_settings(self):
        """
        Applies the settings to the channel.
        """
        # TODO: Apply the settings to the channel
        pass

    async def transfer_ownership(self, new_owner: Member):
        """
        Transfers the ownership of the channel to the new owner.
        :param new_owner: The new owner of the channel.
        """
        self.owner_id = new_owner.id

        await self.resolve()

        # TODO: Apply the settings of new owner to the channel

        await self.upsert()

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

    async def wait_for(self,
                       user_id: Optional[int] = None,
                       timeout: int = 5,
                       escape: Optional[Callable[..., bool]] = lambda: False) -> bool:
        """
        Waits for a specific user to join the channel.
        :param user_id: The user id to wait, any if not specified.
        :param timeout: The times to wait, 5 if not specified.
        :param escape: If the escape function returned True at any moment, directly return False
        :return: Whether the user has joined the channel in time.
        """
        while timeout > 0:
            if user_id in [m.id for m in self.channel.members]:
                return True

            if not user_id and len(self.channel.members) > 0:
                return True

            if escape():
                return False

            timeout -= 1
            await asyncio.sleep(1)

        return False

    async def on_member_join(self, member: Member, voice_state: VoiceState):
        pass

    async def on_member_leave(self, member: Member, voice_state: VoiceState):
        pass

    async def process_state(self):
        if self.state == VoiceChannelState.READY:
            self.logger.info(f"Channel {self.channel.name} is ready! Waiting for owner to join...")
            owner_joined = await self.wait_for(self.owner_id, 5)

            if not owner_joined:
                self.logger.info(f"The owner of {self.channel.name} didn't join within 5 seconds, removing...")
                await self.remove()
                return

            self.logger.info(f"The owner of {self.channel.name} has joined!")
            self.state = VoiceChannelState.USING
            return

        if self.state == VoiceChannelState.USING:
            if self.owner not in self.channel.members:
                self.state = VoiceChannelState.OWNER_DISCONNECTED
            return

        if self.state == VoiceChannelState.OWNER_DISCONNECTED:
            self.logger.info(f"The owner of {self.channel.name} has disconnected, waiting him to rejoin...")
            owner_joined = await self.wait_for(self.owner_id, 5)

            if owner_joined:
                self.logger.info(f"The owner of {self.channel.name} has joined back.")
                self.state = VoiceChannelState.USING
                return

            if len(self.channel.members) == 0:
                self.logger.info(f"{self.channel.name} has no members can be chose as new owner, escaping...")
                self.state = VoiceChannelState.EMPTY
                return

            await self.transfer_ownership(random.choice(self.channel.members))
            return

        if self.state == VoiceChannelState.EMPTY:
            self.logger.info(f"{self.channel.name} has entered EMPTY state, pending deletion...")
            member_joined = await self.wait_for(None, 5)

            if not member_joined:
                await self.remove()
                return

            self.logger.info(f"Someone has joined {self.channel.name}, reviving channel...")
            await self.transfer_ownership(self.channel.members[0])

            self.state = VoiceChannelState.USING
            return

    async def state_loop(self):
        while True:
            await self.process_state()

            await asyncio.sleep(1)

    async def setup(self):
        """
        Sets up the channel.
        """
        self.start()

        await self.apply_settings()

    def start(self):
        """
        Register the listeners then start the state loop.
        """
        self.bot.add_listener(self.on_member_join, "on_voice_channel_join")
        self.bot.add_listener(self.on_member_leave, "on_voice_channel_leave")

        self.loop = self.bot.loop.create_task(self.state_loop())

    def stop(self):
        """
        Remove the listeners and stop the state loop.
        :return:
        """
        self.bot.remove_listener(self.on_member_join, "on_voice_channel_join")
        self.bot.remove_listener(self.on_member_leave, "on_voice_channel_leave")

        if self.loop:
            self.loop.cancel()

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

        self.stop()

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

        cls.logger.info(f"Creating a new voice channel for {owner.name} in {guild_settings.guild.name}.")

        # TODO: Load owner's channel settings here for initial settings for channel creation

        created_channel = await guild_settings.category_channel.create_voice_channel(
            name=f"{owner.display_name}'s Channel"
        )

        voice_channel = cls(
            bot=bot,
            database=database,
            channel_id=created_channel.id,
            owner_id=owner.id,
        )

        await voice_channel.resolve()
        await voice_channel.upsert()

        await voice_channel.setup()

        bot.voice_channels[voice_channel.channel_id] = voice_channel

        return voice_channel

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
