import asyncio
import uuid
from typing import TYPE_CHECKING, Literal, Tuple, Dict, Union

from disnake import ApplicationCommandInteraction, SelectOption, Event, MessageInteraction, ChannelType, \
    CategoryChannel, Interaction, VoiceChannel, Webhook
from disnake.ext.commands import Cog, has_permissions, slash_command
from disnake.ui import StringSelect, ChannelSelect

from src.embeds import InfoEmbed, SuccessEmbed, ErrorEmbed
from src.panels import panels

if TYPE_CHECKING:
    from src.bot import Krabbe


class Setup(Cog):
    def __init__(self, bot: "Krabbe"):
        self.bot: "Krabbe" = bot

    @has_permissions(administrator=True)
    @slash_command(
        name="setup",
        description="快捷設定",
    )
    async def setup(self, interaction: ApplicationCommandInteraction):
        use_custom_category, interaction = await self.use_custom_category(interaction)

        if use_custom_category == "existing":
            category, interaction = await self.select_category(interaction)
        elif use_custom_category == "new":
            category = await interaction.guild.create_category("🔊 動態語音頻道")
        else:
            raise ValueError("Unknown option")

        self.bot.loop.create_task(
            self.create_channels_and_webhooks(self.bot, interaction, category)
        )

        # TODO: Ask for settings

        # TODO: Await for the task to be done

        # TODO: Upsert

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
                Event.message_interaction, check=lambda i: i.custom_id == custom_id, timeout=180
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
                Event.message_interaction, check=lambda i: i.custom_id == custom_id, timeout=180
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

        await new_interaction.edit_original_message(
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

        root_channel = await category.create_voice_channel("🔊 建立語音頻道")
        event_logging_channel = await category.create_forum_channel("事件紀錄")
        message_logging_channel = await category.create_forum_channel("訊息紀錄")
        message_logging_webhook = await message_logging_channel.create_webhook(name="Krabbe Logging")

        await interaction.edit_original_message(
            content="⌛ 正在設置控制面板...",
        )

        control_panel_channel = await category.create_text_channel("控制面板")

        for panel in panels.values():
            await panel.send_to(control_panel_channel)

        await interaction.edit_original_message(
            content="✅ 設定完成！"
        )

def setup(bot: "Krabbe"):
    bot.add_cog(Setup(bot))
