from typing import Union

import disnake
from disnake import VoiceState, Member, Event
from disnake.abc import GuildChannel
from disnake.ext.commands import Cog

from src.bot import Krabbe
from src.classes.guild_settings import GuildSettings
from src.classes.voice_channel import VoiceChannel
from src.panels import LockChannel, ChannelRestored


class Channels(Cog):
    def __init__(self, bot: Krabbe):
        self.bot: Krabbe = bot

    @Cog.listener(name="on_voice_channel_join")
    async def on_voice_channel_join(self, member: Member, voice_state: VoiceState) -> None:
        guild_settings = await GuildSettings.find_one(
            self.bot, self.bot.database, root_channel_id=voice_state.channel.id
        )

        if guild_settings is None:
            return

        for active_voice_channel in VoiceChannel.active_channels.values():
            if not active_voice_channel.owner.id == member.id:
                continue

            await member.move_to(active_voice_channel.channel)
            return

        voice_channel = await VoiceChannel.new(
            bot=self.bot,
            database=self.bot.database,
            guild_settings=guild_settings,
            owner=member
        )

        await member.move_to(voice_channel.channel)

    @Cog.listener(name="on_voice_channel_created")
    async def on_voice_channel_created(self, voice_channel: VoiceChannel) -> None:
        view = LockChannel()  # The Panel is a singleton, so we can reuse it

        await voice_channel.notify(
            wait=True,
            embeds=[
                voice_channel.channel_settings.as_embed(),
                view.embed
            ],
            view=view
        )

    @Cog.listener(name="on_voice_channel_restored")
    async def on_voice_channel_restored(self, voice_channel: VoiceChannel) -> None:
        view = ChannelRestored()

        await voice_channel.notify(
            wait=True,
            embed=view.embed,
            view=view
        )

    @Cog.listener(name=Event.guild_channel_delete)
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        if channel.id not in VoiceChannel.active_channels:
            return

        VoiceChannel.logger.info(f"{channel.name} seems accidentally deleted, removing.")

        voice_channel = VoiceChannel.active_channels[channel.id]
        await voice_channel.remove()

    @Cog.listener(name=Event.guild_channel_update)
    async def on_guild_channel_update(self,
                                      before: Union[GuildChannel, disnake.VoiceChannel],
                                      after: Union[GuildChannel, disnake.VoiceChannel]) -> None:
        if before.id not in VoiceChannel.active_channels:
            return

        voice_channel = VoiceChannel.active_channels[before.id]

        if before.name != after.name:
            voice_channel.channel_settings.channel_name = after.name

        if before.bitrate != after.bitrate:
            voice_channel.channel_settings.bitrate = after.bitrate

        if before.user_limit != after.user_limit:
            voice_channel.channel_settings.user_limit = after.user_limit

        if before.rtc_region != after.rtc_region:
            voice_channel.channel_settings.rtc_region = after.rtc_region

        if before.nsfw != after.nsfw:
            voice_channel.channel_settings.nsfw = after.nsfw

        if before.slowmode_delay != after.slowmode_delay:
            voice_channel.channel_settings.slowmode_delay = after.slowmode_delay

        await voice_channel.channel_settings.upsert()


def setup(bot: Krabbe) -> None:
    bot.add_cog(Channels(bot))
