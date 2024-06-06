import asyncio
import uuid
from typing import TYPE_CHECKING, Literal, Tuple, Dict, Union

from disnake import ApplicationCommandInteraction, SelectOption, Event, MessageInteraction, ChannelType, \
    CategoryChannel, Interaction, VoiceChannel, Webhook, ButtonStyle, Guild
from disnake.ext.commands import Cog, has_permissions, slash_command
from disnake.ui import StringSelect, ChannelSelect, Button

from src.classes.guild_settings import GuildSettings
from src.embeds import InfoEmbed, SuccessEmbed, ErrorEmbed
from src.panels import panels

if TYPE_CHECKING:
    from src.bot import Krabbe


class Setup(Cog):
    def __init__(self, bot: "Krabbe"):
        self.bot: "Krabbe" = bot

    @Cog.listener(name="on_guild_join")
    async def on_guild_join(self, guild: Guild):
        self.bot.logger.info("Joined guild %s", guild.name)

        for text_channel in guild.text_channels:
            self.bot.logger.info("Trying to send setup message to %s", text_channel.name)

            try:
                await text_channel.send(
                    embed=InfoEmbed(
                        title="歡迎使用 Krabbe",
                        description="感謝你邀請 Krabbe 進入你的伺服器！\n"
                                    "要開始使用 Krabbe，請使用 `/start` 指令進行設定。"
                    )
                )
                break
            except Exception as error:
                self.bot.logger.warning("Failed to send setup message to %s: %s", text_channel.name, error)
                continue

    @has_permissions(administrator=True)
    @slash_command(
        name="start",
        description="快捷設定",
    )
    async def start(self, interaction: ApplicationCommandInteraction):
        use_custom_category, interaction = await self.use_custom_category(interaction)

        if use_custom_category == "existing":
            category, interaction = await self.select_category(interaction)
        elif use_custom_category == "new":
            category = await interaction.guild.create_category("🔊 動態語音頻道")
        else:
            raise ValueError("Unknown option")

        channels_and_webhooks_task = self.bot.loop.create_task(
            self.create_channels_and_webhooks(self.bot, interaction, category)
        )

        nsfw, interaction = await self.ask_for_nsfw(interaction)
        lock_message_dm, interaction = await self.ask_for_lock_message_dm(interaction)

        await interaction.response.send_message(
            embed=InfoEmbed(
                title="動態語音設定",
                description="正在設定..."
            ),
            ephemeral=True
        )

        await channels_and_webhooks_task

        guild_settings = GuildSettings(
            bot=self.bot,
            database=self.bot.database,
            guild_id=interaction.guild.id,
            category_channel_id=category.id,
            root_channel_id=channels_and_webhooks_task.result()["root_channel"].id,
            base_role_id=interaction.guild.default_role.id,
            event_logging_channel_id=channels_and_webhooks_task.result()["event_logging_channel"].id,
            message_logging_channel_id=channels_and_webhooks_task.result()["message_logging_channel"].id,
            message_logging_webhook_url=channels_and_webhooks_task.result()["message_logging_webhook"].url,
            allow_nsfw=nsfw == "yes",
            lock_message_dm=lock_message_dm == "yes"
        )

        await guild_settings.upsert()

        await interaction.edit_original_message(
            embeds=[
                SuccessEmbed(
                    title="動態語音設定",
                    description="設定完成！"
                ),
                guild_settings.as_embed(),
                InfoEmbed(
                    title="音樂系統",
                    description="在你邀請音樂機器人以前，你將無法使用音樂功能。\n"
                                "請透過以下的任意一個連結邀請音樂機器人：",
                )
            ],
            components=[
                Button(
                    label=kava.bot_user_name,
                    url=kava.invite_link,
                    style=ButtonStyle.url
                )
                for kava in self.bot.kava_server.clients.values()
            ]
        )

    @staticmethod
    async def use_custom_category(
            interaction: Interaction
    ) -> Tuple[Literal["existing", "new"], MessageInteraction]:
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=InfoEmbed(
                title="動態語音設定",
                description="你想要將動態語音設置在一個現成的類別底下嗎？"
            ),
            components=[StringSelect(
                custom_id=custom_id,
                placeholder="選擇類別",
                options=[
                    SelectOption(
                        label="我想要使用現成的類別",
                        value="existing",
                        description="選擇這個選項，你將會在現有的類別底下建立動態語音頻道"
                    ),
                    SelectOption(
                        label="我想要建立新的類別",
                        value="new",
                        description="選擇這個選項，機器人將會自動為你創建一個新類別"
                    )
                ]
            )],
            ephemeral=True
        )

        try:
            new_interaction: MessageInteraction = await interaction.bot.wait_for(
                Event.message_interaction, check=lambda i: i.data.custom_id == custom_id, timeout=180
            )
        except asyncio.TimeoutError:
            await interaction.edit_original_message(
                embed=ErrorEmbed(
                    title="錯誤",
                    description="操作超時！"
                ),
                components=[]
            )

            raise asyncio.TimeoutError

        if new_interaction.values[0] == "existing":
            await interaction.edit_original_message(
                embed=SuccessEmbed(
                    title="動態語音設定",
                    description="好，我將會使用現成的類別"
                ),
                components=[]
            )
        elif new_interaction.values[0] == "new":
            await interaction.edit_original_message(
                embed=SuccessEmbed(
                    title="動態語音設定",
                    description="好，我將會為你創建一個新類別"
                ),
                components=[]
            )
        else:
            await new_interaction.response.send_message(
                embed=ErrorEmbed(
                    title="錯誤",
                    description="未知的選項！"
                ),
                ephemeral=True
            )

            raise ValueError("Unknown option")

        return new_interaction.values[0], new_interaction

    @staticmethod
    async def select_category(interaction: Interaction) -> Tuple[CategoryChannel, MessageInteraction]:
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=InfoEmbed(
                title="動態語音設定",
                description="請選擇一個類別"
            ),
            components=[ChannelSelect(
                custom_id=custom_id,
                placeholder="選擇類別",
                channel_types=[ChannelType.category]
            )],
            ephemeral=True
        )

        try:
            new_interaction: MessageInteraction = await interaction.bot.wait_for(
                Event.message_interaction, check=lambda i: i.data.custom_id == custom_id, timeout=180
            )
        except asyncio.TimeoutError:
            await interaction.edit_original_message(
                embed=ErrorEmbed(
                    title="錯誤",
                    description="操作超時！"
                ),
                components=[]
            )

            raise asyncio.TimeoutError

        category: CategoryChannel = new_interaction.resolved_values[0]

        await interaction.edit_original_message(
            embed=SuccessEmbed(
                title="動態語音設定",
                description=f"好，我將會在 {category.name} 中建立動態語音頻道"
            ),
            components=[]
        )

        return category, new_interaction

    @staticmethod
    async def create_channels_and_webhooks(
            bot: "Krabbe",
            interaction: Interaction,
            category: CategoryChannel
    ) -> Dict[str, Union[CategoryChannel, VoiceChannel, Webhook]]:
        await interaction.edit_original_message(
            content="⌛ 正在創建頻道和 Webhook..."
        )

        root_channel = await category.create_voice_channel(
            "🔊 建立語音頻道",
            overwrites=category.overwrites
        )
        event_logging_channel = await category.create_forum_channel(
            "事件紀錄",
            overwrites=category.overwrites
        )
        message_logging_channel = await category.create_forum_channel(
            "訊息紀錄",
            overwrites=category.overwrites
        )
        message_logging_webhook = await message_logging_channel.create_webhook(name="Krabbe Logging")

        await interaction.edit_original_message(
            content="⌛ 正在設置控制面板...",
        )

        control_panel_channel = await category.create_text_channel(
            "控制面板",
            overwrites=category.overwrites
        )

        for panel in panels.values():
            await panel.send_to(control_panel_channel)

        await interaction.edit_original_message(
            content="✅ 設定完成！"
        )

        return {
            "category": category,
            "root_channel": root_channel,
            "event_logging_channel": event_logging_channel,
            "message_logging_channel": message_logging_channel,
            "message_logging_webhook": message_logging_webhook,
            "control_panel_channel": control_panel_channel
        }

    @staticmethod
    async def ask_for_nsfw(interaction: Interaction):
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=InfoEmbed(
                title="動態語音設定",
                description="你是否想要成員在動態語音頻道中發送 NSFW 內容？"
            ),
            components=[StringSelect(
                custom_id=custom_id,
                placeholder="選擇",
                options=[
                    SelectOption(
                        label="是",
                        value="yes",
                        description="成員可以在動態語音頻道中發送 NSFW 內容",
                        emoji="✅"
                    ),
                    SelectOption(
                        label="否",
                        value="no",
                        description="成員不可以在動態語音頻道中發送 NSFW 內容",
                        emoji="❌"
                    )
                ]
            )],
            ephemeral=True
        )

        try:
            new_interaction: MessageInteraction = await interaction.bot.wait_for(
                Event.message_interaction, check=lambda i: i.data.custom_id == custom_id, timeout=180
            )
        except asyncio.TimeoutError:
            await interaction.edit_original_message(
                embed=ErrorEmbed(
                    title="錯誤",
                    description="操作超時！"
                ),
                components=[]
            )

            raise asyncio.TimeoutError

        if new_interaction.values[0] == "yes":
            await interaction.edit_original_message(
                embed=SuccessEmbed(
                    title="動態語音設定",
                    description="好，我將會啟用 NSFW"
                ),
                components=[]
            )
        elif new_interaction.values[0] == "no":
            await interaction.edit_original_message(
                embed=SuccessEmbed(
                    title="動態語音設定",
                    description="好，我將不會啟用 NSFW"
                ),
                components=[]
            )
        else:
            await new_interaction.response.send_message(
                embed=ErrorEmbed(
                    title="錯誤",
                    description="未知的選項！"
                ),
                ephemeral=True
            )

            raise ValueError("Unknown option")

        return new_interaction.values[0], new_interaction

    @staticmethod
    async def ask_for_lock_message_dm(interaction: Interaction):
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=InfoEmbed(
                title="動態語音設定",
                description="你是否想要在成員創建動態語音頻道時通知他們？"
            ),
            components=[StringSelect(
                custom_id=custom_id,
                placeholder="選擇",
                options=[
                    SelectOption(
                        label="是",
                        value="yes",
                        description="成員創建動態語音頻道時將會收到一則私人訊息",
                        emoji="✅"
                    ),
                    SelectOption(
                        label="否",
                        value="no",
                        description="成員創建動態語音頻道時不會收到任何訊息",
                        emoji="❌"
                    )
                ]
            )],
            ephemeral=True
        )

        try:
            new_interaction: MessageInteraction = await interaction.bot.wait_for(
                Event.message_interaction, check=lambda i: i.data.custom_id == custom_id, timeout=180
            )
        except asyncio.TimeoutError:
            await interaction.edit_original_message(
                embed=ErrorEmbed(
                    title="錯誤",
                    description="操作超時！"
                ),
                components=[]
            )

            raise asyncio.TimeoutError

        if new_interaction.values[0] == "yes":
            await interaction.edit_original_message(
                embed=SuccessEmbed(
                    title="動態語音設定",
                    description="好，我將會通知成員"
                ),
                components=[]
            )
        elif new_interaction.values[0] == "no":
            await interaction.edit_original_message(
                embed=SuccessEmbed(
                    title="動態語音設定",
                    description="好，我將不會通知成員"
                ),
                components=[]
            )
        else:
            await new_interaction.response.send_message(
                embed=ErrorEmbed(
                    title="錯誤",
                    description="未知的選項！"
                ),
                ephemeral=True
            )

            raise ValueError("Unknown option")

        return new_interaction.values[0], new_interaction


def setup(bot: "Krabbe"):
    bot.add_cog(Setup(bot))
