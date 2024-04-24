import asyncio
from asyncio import Event
from enum import Enum
from logging import getLogger
from typing import Optional, TYPE_CHECKING, AsyncIterator

import disnake
from disnake import Member, NotFound, VoiceState, Message, Interaction
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.classes.channel_settings import ChannelSettings
from src.classes.guild_settings import GuildSettings
from src.classes.mongo_object import MongoObject
from src.embeds import SuccessEmbed, WarningEmbed
from src.utils import generate_channel_metadata

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
            owner_id: int,
            channel_settings: ChannelSettings
    ):
        super().__init__(bot, database)

        self.channel_id: int = channel_id
        self.owner_id: int = owner_id

        self._channel: Optional[disnake.VoiceChannel] = None
        self._owner: Optional[disnake.Member] = None

        self.state: VoiceChannelState = VoiceChannelState.PREPARING
        self.state_change_event: Event = Event()

        self.channel_settings: ChannelSettings = channel_settings

        self.default_timeout: int = 5 if self.bot.debug else 60

    def unique_identifier(self) -> dict:
        return {"channel_id": self.channel_id}

    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "owner_id": self.owner_id
        }

    async def apply_settings(self, guild_settings: Optional[GuildSettings] = None) -> None:
        """
        Applies the settings to the channel.
        :param guild_settings: The guild settings object. If not specified, it will be fetched from the database.
        """
        guild_settings = guild_settings or await GuildSettings.find_one(
            self.bot, self.database, guild_id=self.channel.guild.id
        )

        await self.channel.edit(
            **generate_channel_metadata(
                owner=self.owner,
                channel_settings=self.channel_settings,
                guild_settings=guild_settings or await GuildSettings.find_one(
                    self.bot, self.database, guild_id=self.channel.guild.id
                )
            )
        )

    async def transfer_ownership(self, new_owner: Member) -> None:
        """
        Transfers the ownership of the channel to the new owner.
        Does nothing if the new owner is the same as the current owner.
        :param new_owner: The new owner of the channel.
        """
        if self.owner_id == new_owner.id:
            return

        self.owner_id = new_owner.id

        await self.upsert()

        self.channel_settings = await ChannelSettings.get_settings(self.bot, self.database, user_id=new_owner.id)
        await self.apply_settings()

        await self.notify(
            embed=SuccessEmbed(
                title="轉移所有權",
                description=f"{new_owner.mention} 成為了頻道的新擁有者！\n"
                            f"已套用新擁有者的頻道設定！"
            )
        )

    @property
    def channel(self) -> Optional[disnake.VoiceChannel]:
        if self._channel is None:
            self._channel = self.bot.get_channel(self.channel_id)

        if self._channel.id != self.channel_id:
            self._channel = self.bot.get_channel(self.channel_id)

        return self._channel

    @property
    def owner(self) -> Optional[Member]:
        if self._owner is None:
            self._owner = self.channel.guild.get_member(self.owner_id)

        if self._owner.id != self.owner_id:
            self._owner = self.channel.guild.get_member(self.owner_id)

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

    async def check_state(self) -> None:
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

    async def update_state(self, new_state: VoiceChannelState) -> None:
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

    async def on_state_change(self, new_state: VoiceChannelState) -> None:
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

            is_owner_back = await self.wait_for_user(self.owner_id, timeout=self.default_timeout)

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

            is_anyone_joined = await self.wait_for_user(None, timeout=self.default_timeout)

            if is_anyone_joined:
                await self.notify(
                    embed=WarningEmbed(
                        title="頻道重生",
                        description=f"{self.channel.members[0].mention} 在頻道垂死之際加入了頻道！"
                    )
                )

                await self.transfer_ownership(self.channel.members[0])
                await self.update_state(VoiceChannelState.ACTIVE)
                return

            await self.remove()

    async def on_member_join(self, member: Member, voice_state: VoiceState) -> None:
        if voice_state.channel.id != self.channel_id:
            return

    async def on_member_leave(self, member: Member, voice_state: VoiceState) -> None:
        if voice_state.channel.id != self.channel_id:
            return

        if member.id == self.owner_id:
            await self.update_state(VoiceChannelState.OWNER_DISCONNECTED)
            return

    async def add_member(self, member: Member) -> None:
        """
        Add a member to the channel. Like give them the permission to join the channel.
        :param member: The member to add.
        """
        if member.id == self.owner_id:
            return
        # TODO: Deal with the channel lock

    async def remove_member(self, member: Member) -> None:
        """
        Remove a member from the channel. Kick them from the channel and remove their permissions.
        :param member: The member to remove.
        """
        # TODO: Deal with the channel lock
        if member.id == self.owner_id:
            raise ValueError("Owner cannot be removed from the channel.")

        # noinspection PyTypeChecker
        await member.move_to(None)

    async def setup(self) -> None:
        """
        Apply the settings, start the listeners, then wait for owner to join and set state to ACTIVE.
        Note that if owner didn't join in the timeout period, the channel will be removed.
        """
        await self.apply_settings()

        if not await self.wait_for_user(self.owner_id, timeout=self.default_timeout):
            await self.remove()
            return

        await self.update_state(VoiceChannelState.ACTIVE)

        self.start_listeners()

    def start_listeners(self) -> None:
        """
        Register the listeners then start the state loop.
        """
        self.bot.add_listener(self.on_member_join, "on_voice_channel_join")
        self.bot.add_listener(self.on_member_leave, "on_voice_channel_leave")

    def stop_listeners(self) -> None:
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

        self.logger.info(f"Voice channel {self.channel_id} removed.")

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
        cls.logger.info(f"Creating a new voice channel for {owner.name} in {guild_settings.guild.name}.")

        channel_settings = await ChannelSettings.get_settings(bot, database, owner.id)

        created_channel = await guild_settings.category_channel.create_voice_channel(
            **generate_channel_metadata(owner, channel_settings, guild_settings)
        )

        voice_channel = cls(
            bot=bot,
            database=database,
            channel_id=created_channel.id,
            owner_id=owner.id,
            channel_settings=channel_settings
        )

        await voice_channel.upsert()

        await voice_channel.apply_settings()

        bot.voice_channels[voice_channel.channel_id] = voice_channel

        _ = bot.loop.create_task(voice_channel.setup())

        return voice_channel

    @classmethod
    async def get_active_channel_from_interaction(cls, interaction: Interaction) -> Optional["VoiceChannel"]:
        """
        Get the active voice channel object that the interaction author is in if any.
        :param interaction: The interaction object.
        :return: The voice channel object if found.
        """
        author_voice_state = interaction.guild.get_member(interaction.author.id).voice

        if not author_voice_state:
            return None

        # noinspection PyUnresolvedReferences
        return interaction.bot.voice_channels.get(author_voice_state.channel.id)

    @classmethod
    async def find_one(cls, bot: "Krabbe", database: AsyncIOMotorDatabase, **kwargs) -> Optional["VoiceChannel"]:
        """
        Find a document in the collection that matches the specified query.
        """
        cls.logger.info(f"Finding one {cls.collection_name} document: {kwargs}")

        document = await database.get_collection(cls.collection_name).find_one(kwargs)

        if not document:
            return None

        # noinspection PyUnresolvedReferences
        del document["_id"]

        channel_settings = await ChannelSettings.get_settings(bot, database, user_id=document["owner_id"])

        return cls(bot=bot, database=database, channel_settings=channel_settings, **document)

    @classmethod
    async def find(cls, bot: "Krabbe", database: AsyncIOMotorDatabase, **kwargs) -> AsyncIterator["VoiceChannel"]:
        """
        Find all documents in the collection that match the specified query.
        """
        cls.logger.info(f"Finding {cls.collection_name} documents: {kwargs}")

        cursor = database.get_collection(cls.collection_name).find(kwargs)

        async for document in cursor:
            del document["_id"]

            channel_settings = await ChannelSettings.get_settings(bot, database, user_id=document["owner_id"])

            yield cls(bot=bot, database=database, channel_settings=channel_settings, **document)
