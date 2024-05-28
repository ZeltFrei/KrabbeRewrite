from typing import Optional

from disnake import Option, OptionType, ApplicationCommandInteraction, ButtonStyle, OptionChoice, ChannelType, \
    CategoryChannel, Role, ForumChannel
from disnake.ext.commands import Cog, slash_command, has_permissions
from disnake.ui import Button

from src.bot import Krabbe
from src.classes.guild_settings import GuildSettings
from src.classes.voice_channel import VoiceChannel
from src.embeds import SuccessEmbed, ErrorEmbed
from src.panels import panels


class Configuration(Cog):
    def __init__(self, bot: Krabbe):
        self.bot: Krabbe = bot

    @has_permissions(administrator=True)
    @slash_command(
        name="old_setup",
        description="快捷設定",
        options=[
            Option(
                name="category",
                description="要設定在的類別，未指定則由機器人自動創建",
                type=OptionType.channel,
                channel_types=[ChannelType.category],
                required=False
            )
        ]
    )
    async def setup(self, interaction: ApplicationCommandInteraction,
                    category: Optional[CategoryChannel] = None) -> None:
        await interaction.response.defer(ephemeral=True)

        if not category:
            category = await interaction.guild.create_category("🔊 動態語音頻道")

        root_channel = await interaction.guild.create_voice_channel("🔊 Krabbe 2 - 自動化語音頻道", category=category)
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
            message_logging_webhook_url=message_logging_webhook.url,
            allow_nsfw=True,
            lock_message_dm=False
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
        name="configure",
        description="個別調整伺服器的設定",
        options=[
            Option(
                name="category",
                description="動態語音類別，新的語音頻道將會在這個類別下創建並繼承權限設定",
                type=OptionType.channel,
                channel_types=[ChannelType.category],
            ),
            Option(
                name="root_channel",
                description="根頻道，用戶將透過這個頻道來創建新的語音頻道",
                type=OptionType.channel,
                channel_types=[ChannelType.voice],
            ),
            Option(
                name="base_role",
                description="基礎身分組，應該要是一個「所有人都有」的身分組，除非你知道你在做什麼，否則請不要更改這個選項",
                type=OptionType.role
            ),
            Option(
                name="event_logging_channel",
                description="事件紀錄頻道，Krabbe 會在這個頻道中記錄所有的事件，像是語音頻道的刪除、創建等等",
                type=OptionType.channel,
                channel_types=[ChannelType.forum]
            ),
            Option(
                name="message_logging_channel",
                description="訊息紀錄頻道，Krabbe 會在這個頻道中記錄所有語音頻道的訊息",
                type=OptionType.channel,
                channel_types=[ChannelType.forum]
            ),
            Option(
                name="message_logging_webhook",
                description="訊息紀錄 Webhook，Krabbe 會使用這個 Webhook 來記錄語音頻道的訊息，必須在 message_logging_channel 中",
                type=OptionType.string
            ),
            Option(
                name="allow_nsfw",
                description="是否允許 NSFW 頻道",
                type=OptionType.boolean
            ),
            Option(
                name="lock_message_dm",
                description="是否將鎖定通知訊息發送到私人訊息中",
                type=OptionType.boolean
            )
        ]
    )
    async def configure(self, interaction: ApplicationCommandInteraction,
                        category: Optional[CategoryChannel] = None,
                        root_channel: Optional[CategoryChannel] = None,
                        base_role: Optional[Role] = None,
                        event_logging_channel: Optional[ForumChannel] = None,
                        message_logging_channel: Optional[ForumChannel] = None,
                        message_logging_webhook: Optional[str] = None,
                        allow_nsfw: Optional[bool] = None,
                        lock_message_dm: Optional[bool] = None) -> None:
        guild_settings = await GuildSettings.find_one(self.bot, self.bot.database, guild_id=interaction.guild.id)

        if not guild_settings:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    title="伺服器設定不存在！",
                    description="請先執行 `/setup` 來設定伺服器"
                ),
                ephemeral=True
            )

        if category is not None:
            guild_settings.category_channel_id = category.id

        if root_channel is not None:
            guild_settings.root_channel_id = root_channel.id

        if base_role is not None:
            guild_settings.base_role_id = base_role.id

        if event_logging_channel is not None:
            guild_settings.event_logging_channel_id = event_logging_channel.id

        if message_logging_channel is not None:
            guild_settings.message_logging_channel_id = message_logging_channel.id

        if message_logging_webhook is not None:
            guild_settings.message_logging_webhook_url = message_logging_webhook

        if allow_nsfw is not None:
            guild_settings.allow_nsfw = allow_nsfw

        if lock_message_dm is not None:
            guild_settings.lock_message_dm = lock_message_dm

        await guild_settings.upsert()

        await interaction.response.send_message(
            embeds=[
                SuccessEmbed("伺服器設定已更新，各個頻道將會陸續套用新設定"),
                guild_settings.as_embed()
            ],
            ephemeral=True
        )

        for channel in VoiceChannel.active_channels.values():
            await channel.apply_setting_and_permissions()

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

        if panel == "all":
            for panel in panels.values():
                await panel.send_to(interaction.channel)

            await interaction.edit_original_response(
                embed=SuccessEmbed("所有控制面板已傳送"),
            )

            return

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
        return [OptionChoice(name=key, value=key) for key in panels.keys() if panel in key] + ["all"]


def setup(bot: Krabbe) -> None:
    bot.add_cog(Configuration(bot))
