import asyncio
from asyncio import Event
from enum import Enum
from logging import getLogger
from typing import Optional, TYPE_CHECKING

import disnake
from disnake import Member, NotFound, VoiceState, Message
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.classes.guild_settings import GuildSettings
from src.classes.mongo_object import MongoObject
from src.embeds import SuccessEmbed, WarningEmbed

if TYPE_CHECKING:
    from src.bot import Krabbe


class VoiceChannelState(Enum):
    PREPARING = 0
    ACTIVE = 1
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

        self.state: VoiceChannelState = VoiceChannelState.PREPARING
        self.state_change_event: Event = Event()

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
        Does nothing if the new owner is the same as the current owner.
        :param new_owner: The new owner of the channel.
        """
        if self.owner_id == new_owner.id:
            return

        self.owner_id = new_owner.id

        await self.resolve()

        # TODO: Apply the settings of new owner to the channel

        await self.upsert()

        await self.notify(
            embed=SuccessEmbed(
                title="轉移所有權",
                description=f"{new_owner.mention} 成為了頻道的新擁有者！"
            )
        )

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

    async def notify(self, wait: bool = False, *args, **kwargs) -> Optional[Message]:
        """
        Sends a message to the channel
        :param wait: Whether to wait the message to be sent.
        :param args: The args to pass to the `send()` method.
        :param kwargs: The kwargs to pass to the `send()` method.
        :return: The message sent. None if wait is False
        """
        if wait:
            return await self.channel.send(*args, **kwargs)

        _ = self.bot.loop.create_task(
            self.channel.send(*args, **kwargs)
        )

    async def check_state(self):
        """
        Manually checks and update the state of the channel. Useful when launching the bot.
        """
        if any(m.id == self.owner_id for m in self.channel.members):  # Owner is in the channel
            await self.update_state(VoiceChannelState.ACTIVE)
            return

        if len(self.channel.members) == 0:  # Channel is empty
            await self.update_state(VoiceChannelState.EMPTY)
            return

        await self.update_state(VoiceChannelState.OWNER_DISCONNECTED)  # Owner is not in the channel but someone else is

    async def update_state(self, new_state: VoiceChannelState):
        """
        Updates the state of the channel.
        """
        self.state = new_state

        _ = self.bot.loop.create_task(self.on_state_change(new_state))

        self.state_change_event.set()
        self.state_change_event.clear()

    async def wait_for_state(self, state: Optional[VoiceChannelState], timeout: int) -> bool:
        """
        Waits for the channel to reach the specified state. If no state is specified, it waits for the channel to reach any state.
        :param state:
        :param timeout:
        :return: Boolean indicating whether the channel reached the specified state within the timeout.
        """
        end_time = asyncio.get_running_loop().time() + timeout
        while True:
            try:
                remaining_time = end_time - asyncio.get_running_loop().time()

                if remaining_time <= 0:
                    return False

                await asyncio.wait_for(self.state_change_event.wait(), timeout=remaining_time)
            except asyncio.TimeoutError:
                return False

            if not state or self.state == state:
                return True

    async def wait_for_user(self, user_id: Optional[int], timeout: int) -> bool:
        """
        Waits for the user to join the channel.
        :param user_id: The user ID to wait for. If not specified, waits for any user to join.
        :param timeout: The timeout in seconds.
        :return: Boolean indicating whether the user joined the channel.
        """
        if user_id and self.channel.members and any(m.id == user_id for m in self.channel.members):
            return True

        if not user_id and self.channel.members:
            return True

        try:
            await self.bot.wait_for(
                "voice_channel_join",
                check=lambda m, v: (m.id == user_id if user_id else True) and v.channel.id == self.channel_id,
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return False

        return True

    async def on_state_change(self, new_state: VoiceChannelState):
        """
        Called when the state of the channel changes.
        """
        self.logger.info(f"State of {self.channel.name} updated to {new_state}")

        if new_state == VoiceChannelState.ACTIVE:
            pass

        elif new_state == VoiceChannelState.OWNER_DISCONNECTED:
            await self.notify(
                embed=WarningEmbed(
                    title="擁有者離開",
                    description=f"頻道的擁有者 {self.owner.mention} 離開了頻道！\n"
                                f"如果他沒有在 60 秒內加入，頻道所有權將被轉移給頻道內的隨機成員"
                )
            )

            is_owner_back = await self.wait_for_user(self.owner_id, timeout=60)

            if is_owner_back:
                await self.notify(
                    embed=SuccessEmbed(
                        title="擁有者回歸",
                        description=f"頻道的擁有者 {self.owner.mention} 回到了頻道內！"
                    )
                )

                await self.update_state(VoiceChannelState.ACTIVE)
                return

            if len(self.channel.members) == 0:
                await self.update_state(VoiceChannelState.EMPTY)
                return

            await self.notify(
                embed=WarningEmbed(
                    title="擁有者離開",
                    description=f"頻道的原擁有者 {self.owner.mention} 沒有在 60 秒內回來"
                )
            )

            await self.transfer_ownership(self.channel.members[0])

        elif new_state == VoiceChannelState.EMPTY:
            await self.notify(
                embed=WarningEmbed(
                    title="頻道是空的",
                    description="所有成員都離開了頻道！\n"
                                "如果再 60 秒內沒有人加入這個頻道，這個頻道將會被刪除"
                )
            )

            is_anyone_joined = await self.wait_for_user(None, timeout=60)

            if is_anyone_joined:
                await self.notify(
                    embed=WarningEmbed(
                        title="頻道重生",
                        description=f"{self.channel.members[0]} 在頻道垂死之際加入了頻道！"
                    )
                )

                await self.transfer_ownership(self.channel.members[0])
                await self.update_state(VoiceChannelState.ACTIVE)
                return

            await self.remove()

    async def on_member_join(self, member: Member, voice_state: VoiceState):
        if voice_state.channel.id != self.channel_id:
            return

    async def on_member_leave(self, member: Member, voice_state: VoiceState):
        if voice_state.channel.id != self.channel_id:
            return

        if member.id == self.owner_id:
            await self.update_state(VoiceChannelState.OWNER_DISCONNECTED)
            return

    async def setup(self):
        """
        Apply the settings, start the listeners, then wait for owner to join and set state to ACTIVE.
        Note that if owner didn't join in 60 seconds, the channel will be removed.
        """
        await self.apply_settings()

        if not await self.wait_for_user(self.owner_id, timeout=60):
            await self.remove()
            return

        await self.update_state(VoiceChannelState.ACTIVE)

        self.start_listeners()

    def start_listeners(self):
        """
        Register the listeners then start the state loop.
        """
        self.bot.add_listener(self.on_member_join, "on_voice_channel_join")
        self.bot.add_listener(self.on_member_leave, "on_voice_channel_leave")

    def stop_listeners(self):
        """
        Remove the listeners and stop the state loop.
        :return:
        """
        self.bot.remove_listener(self.on_member_join, "on_voice_channel_join")
        self.bot.remove_listener(self.on_member_leave, "on_voice_channel_leave")

    async def remove(self) -> None:
        """
        Remove the voice channel from both bot memory and the database. And delete the channel.
        Note that `delete` method only deletes the document from the database. While this method deletes the whole channel.

        :return: None
        """
        self.stop_listeners()

        try:
            self.bot.voice_channels.pop(self.channel_id)
        except KeyError:  # Forgive the channel if it's not in the bot's memory
            pass

        try:
            await self.channel.delete()
        except (NotFound, ValueError):  # Forgive the channel if it's already deleted or not resolved
            pass

        await self.delete()

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

        bot.voice_channels[voice_channel.channel_id] = voice_channel

        _ = bot.loop.create_task(voice_channel.setup())

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
