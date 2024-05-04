from disnake import Option, OptionType, ApplicationCommandInteraction, ButtonStyle, OptionChoice
from disnake.ext.commands import Cog, slash_command, has_permissions
from disnake.ui import Button

from src.bot import Krabbe
from src.classes.guild_settings import GuildSettings
from src.embeds import SuccessEmbed
from src.panels import panels


class Setup(Cog):
    def __init__(self, bot: Krabbe):
        self.bot: Krabbe = bot

    @has_permissions(administrator=True)
    @slash_command(
        name="setup",
        description="快捷設定"
    )
    async def setup(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.defer(ephemeral=True)

        category = await interaction.guild.create_category("🔊 動態語音頻道")
        root_channel = await interaction.guild.create_voice_channel("🔊 建立語音頻道", category=category)
        event_logging_channel = await interaction.guild.create_forum_channel("事件紀錄", category=category)
        message_logging_channel = await interaction.guild.create_forum_channel(name="訊息紀錄", category=category)
        message_logging_webhook = await message_logging_channel.create_webhook(name="Krabbe Logging")

        guild_settings = GuildSettings(
            bot=self.bot,
            database=self.bot.database,
            guild_id=interaction.guild.id,
            category_channel_id=category.id,
            root_channel_id=root_channel.id,
            base_role_id=interaction.guild.default_role.id,
            event_logging_channel_id=event_logging_channel.id,
            message_logging_channel_id=message_logging_channel.id,
            message_logging_webhook_url=message_logging_webhook.url
        )

        await guild_settings.upsert()

        panel_channel = await category.create_text_channel("控制面板")

        for panel in panels.values():
            await panel.send_to(panel_channel)

        await interaction.edit_original_response(
            embed=SuccessEmbed(
                title="設定完成",
                description="成功設定動態語音頻道！\n"
                            "你可能需要調整權限設定。"
            )
        )

    @has_permissions(administrator=True)
    @slash_command(
        name="panel",
        description="傳送指定的控制面板",
        options=[
            Option(
                name="panel",
                description="要傳送的控制面板",
                type=OptionType.string,
                required=True,
                autocomplete=True
            )
        ]
    )
    async def panel(self, interaction: ApplicationCommandInteraction, panel: str) -> None:
        await interaction.response.defer(ephemeral=True)

        panel_to_send = panels.get(panel)

        message = await panel_to_send.send_to(interaction.channel)

        await interaction.edit_original_response(
            embed=SuccessEmbed("控制面板已傳送"),
            components=[
                Button(
                    label="面板訊息",
                    style=ButtonStyle.url,
                    url=message.jump_url
                )
            ]
        )

    @panel.autocomplete("panel")
    async def list_panels(self, _interaction: ApplicationCommandInteraction, panel: str) -> list[OptionChoice]:
        return [OptionChoice(name=key, value=key) for key in panels.keys() if panel in key]


def setup(bot: Krabbe) -> None:
    bot.add_cog(Setup(bot))
