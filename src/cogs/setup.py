from disnake import Option, OptionType, ApplicationCommandInteraction
from disnake.ext.commands import Cog, slash_command, has_permissions

from src.bot import Krabbe
from src.classes.guild_settings import GuildSettings
from src.panels import panels


class Setup(Cog):
    def __init__(self, bot: Krabbe):
        self.bot: Krabbe = bot

    @has_permissions(administrator=True)
    @slash_command(
        name="setup",
        description="快捷設定",
        guild_ids=[975244147730546758]
    )
    async def setup(self, interaction: ApplicationCommandInteraction):
        await interaction.response.defer(ephermal=True)

        category = await interaction.guild.create_category("🔊 動態語音頻道")
        root = await interaction.guild.create_voice_channel("🔊 建立語音頻道", category=category)

        guild_settings = GuildSettings(
            bot=self.bot,
            database=self.bot.database,
            guild_id=interaction.guild.id,
            category_channel_id=category.id,
            root_channel_id=root.id
        )

        await guild_settings.upsert()

        await interaction.edit_original_response("✅ 完成")

    @slash_command(
        name="panel",
        description="傳送指定的控制面板",
        options=[
            Option(
                name="panel",
                description="要傳送的控制面板",
                type=OptionType.string,
                choices=[str(key) for key in panels.keys()],
                required=True
            )
        ],
        guild_ids=[975244147730546758]
    )
    async def panel(self, interaction: ApplicationCommandInteraction, panel: str):
        panel_to_send = panels.get(panel)

        await interaction.channel.send(
            embed=panel_to_send.embed,
            view=panel_to_send.view
        )

        await interaction.response.send_message("✅ 完成", ephemeral=True)


def setup(bot: Krabbe):
    bot.add_cog(Setup(bot))
