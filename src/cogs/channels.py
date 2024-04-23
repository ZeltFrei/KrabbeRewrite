from disnake import VoiceState, Member, Event
from disnake.abc import GuildChannel
from disnake.ext.commands import Cog

from src.bot import Krabbe
from src.classes.guild_settings import GuildSettings
from src.classes.voice_channel import VoiceChannel


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

        await guild_settings.resolve()

        voice_channel = await VoiceChannel.new(
            bot=self.bot,
            database=self.bot.database,
            guild_settings=guild_settings,
            owner=member
        )

        await member.move_to(voice_channel.channel)

    @Cog.listener(name=Event.guild_channel_delete)
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        if channel.id not in self.bot.voice_channels:
            return

        VoiceChannel.logger.info(f"{channel.name} seems accidentally deleted, removing.")

        voice_channel = self.bot.voice_channels[channel.id]
        await voice_channel.remove()


def setup(bot: Krabbe) -> None:
    bot.add_cog(Channels(bot))
