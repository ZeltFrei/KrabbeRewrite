import asyncio
import uuid
from typing import TYPE_CHECKING, Literal, Tuple, Dict, Union

from disnake import ApplicationCommandInteraction, SelectOption, Event, MessageInteraction, ChannelType, \
    CategoryChannel, Interaction, VoiceChannel, Webhook, ButtonStyle, Guild
from disnake.ext.commands import Cog, has_permissions, slash_command
from disnake.ui import StringSelect, ChannelSelect, Button

from src.classes.guild_settings import GuildSettings
from src.embeds import SuccessEmbed, ErrorEmbed, VoiceSetupEmbed
from src.panels import panels
from src.quick_ui import confirm_button

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
                    embed=VoiceSetupEmbed(
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
        interaction, is_to_continue = await self.check_previous_settings(self.bot, interaction)

        if not is_to_continue:
            return await interaction.response.send_message(
                embed=ErrorEmbed("已取消設定")
            )

        if "COMMUNITY" not in interaction.guild.features:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    title="錯誤",
                    description="此功能僅支援社群伺服器！"
                )
            )

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

        use_music, interaction = await self.ask_for_music(interaction)
        nsfw, interaction = await self.ask_for_nsfw(interaction)
        lock_message_dm, interaction = await self.ask_for_lock_message_dm(interaction)

        await interaction.response.send_message(
            embed=VoiceSetupEmbed(
                status="正在設定..."
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

        settings_embed = guild_settings.as_embed()

        settings_embed.set_author(name="成功安裝〡這是您的伺服器語音設定", icon_url="https://i.imgur.com/lsTtd9c.png")

        settings_embed.description = "### 系統頻道介紹\n" \
                                     "請記得檢查語音頻道權限是否與您的伺服器權限符合。\n\n" \
                                     "語音事件紀錄：此論壇頻道用於紀錄所有語音的動態，包含成員語音設定，任何加入、退出等資訊。\n" \
                                     "語音訊息紀錄：此論壇頻道用於紀錄所有語音文字頻道中的所有發佈的訊息紀錄（不包含語音設定）\n。" \
                                     "語音控制面板：此文字頻道用於成員設定自己的語音頻道相關內容。\n" \
                                     "建立語音頻道：此語音頻道用於自動建立語音頻道，並根據用戶名稱來設定頻道名稱"

        await interaction.edit_original_message(
            embeds=[
                       SuccessEmbed(
                           title="設定完成",
                           description="成功設定動態語音頻道！\n"
                                       "你可能需要調整權限設定。"
                       ),
                       settings_embed
                   ] + [
                       VoiceSetupEmbed(
                           status="邀請音樂機器人",
                           description="請邀請音樂機器人進入伺服器，並設定權限。\n"
                                       "### 提醒您\n"
                                       "系統會根據您邀請的機器人數量，來決定伺服器同時支援播放數量"
                       )
                   ],
            components=[
                Button(
                    label=kava.bot_user_name,
                    url=kava.invite_link,
                    style=ButtonStyle.url
                )
                for kava in self.bot.kava_server.clients.values()
            ] if use_music == "yes" else []
        )

    @staticmethod
    async def check_previous_settings(bot: "Krabbe", interaction: Interaction) -> Tuple[Interaction, bool]:
        guild_settings = await GuildSettings.find_one(
            bot, bot.database, guild_id=interaction.guild.id
        )

        if not guild_settings:
            return interaction, True

        new_interaction, confirmed = await confirm_button(
            interaction,
            message="您已經在這個伺服器設定過動態語音系統，繼續設定將會移除先前的所有設定，並刪除舊有的頻道，是否要繼續設定？\n"
                    "註：控制面板頻道將不會被自動刪除"
        )

        if not confirmed:
            return new_interaction, False

        _ = bot.loop.create_task(guild_settings.root_channel.delete())
        _ = bot.loop.create_task(guild_settings.category_channel.delete())
        _ = bot.loop.create_task(guild_settings.event_logging_channel.delete())
        _ = bot.loop.create_task(guild_settings.message_logging_channel.delete())

        await guild_settings.delete()

        return new_interaction, True

    @staticmethod
    async def use_custom_category(
            interaction: Interaction
    ) -> Tuple[Literal["existing", "new"], MessageInteraction]:
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=VoiceSetupEmbed(
                status="設定建立系統時的頻道類別",
                description="## 請選擇您想要如何建立語音系統？\n"
                            "### 功能建立時會自動跟隨頻道類別設定的權限。\n"
                            "- 使用現成的類別：\n"
                            "- - 將系統建立在目前伺服器擁有的頻道類別（由自己選擇頻道類別）\n"
                            "- 建立全新的類別：\n"
                            "- - 系統將自動建立新類別來存放所有相關頻道（頻道權限預設查看全開）"
            ),
            components=[StringSelect(
                custom_id=custom_id,
                placeholder="選擇類別",
                options=[
                    SelectOption(
                        label="我想要使用現成的類別",
                        value="existing",
                        description="選擇這個選項，你將會在現有的類別底下建立動態語音頻道，功能建立時會自動跟隨頻道類別設定的權限。"
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

        await interaction.edit_original_message(
            embed=VoiceSetupEmbed(
                status="設定成功，請繼續下一步"
            ),
            components=[]
        )

        return new_interaction.values[0], new_interaction

    @staticmethod
    async def select_category(interaction: Interaction) -> Tuple[CategoryChannel, MessageInteraction]:
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=VoiceSetupEmbed(
                status="設定建立系統時的頻道類別",
                title="請選擇一個類別"
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
            embed=VoiceSetupEmbed(
                status="設定成功，請繼續下一步"
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
            "語音事件記錄",
            overwrites=category.overwrites
        )
        message_logging_channel = await category.create_forum_channel(
            "語音訊息記錄",
            overwrites=category.overwrites
        )
        message_logging_webhook = await message_logging_channel.create_webhook(name="Krabbe Logging")

        await interaction.edit_original_message(
            content="⌛ 正在設置控制面板...",
        )

        control_panel_channel = await category.create_text_channel(
            "語音控制面板",
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
    async def ask_for_music(interaction: Interaction):
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=VoiceSetupEmbed(
                status="設定音樂功能",
                title="您是否想要讓成員使用此系統專屬的音樂功能？",
                description="使用我們的音樂機器人有幾點好處。\n"
                            "1. 直接在我們的系統的語音文字頻道輸入相關命令播放\n"
                            "2. 您的Discord伺服器最多可以在不同語音頻道播放多達三個的音樂系統\n"
                            "3  根據您邀請的機器人數量來決定播放數量\n"
                            "4. 相關命令只要在 Krabbe 2.0 中選擇並輸入即可，不用在不同機器人輸入\n"
                            "5. 每個成員都可以決定是否讓其他成員操作音樂系統\n"
                            "6. 可以使用 YouTube, Spotify 等音樂平台進行播放\n"
                            "7. 全中文操作介面，相關指令不會與其他機器人衝突\n\n"
                            "Krabbe 2.0 使用 [Lava](https://github.com/Nat1anWasTaken/Lava) 來播放音樂。"
            ),
            components=[StringSelect(
                custom_id=custom_id,
                placeholder="選擇",
                options=[
                    SelectOption(
                        label="是",
                        value="yes",
                        description="邀請音樂機器人",
                        emoji="✅"
                    ),
                    SelectOption(
                        label="否",
                        value="no",
                        description="不邀請音樂機器人",
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
                embed=VoiceSetupEmbed(
                    status="設定音樂功能",
                    title="請在語音設定完畢後邀請音樂機器人，會給予邀請按鈕。\n",
                    description="如果您找不到邀請按鈕，您可以輸入 `/music_bot` 命令呼叫邀請。\n"
                                "### 提醒您\n"
                                "系統會根據您邀請的機器人數量，來決定伺服器同時支援播放數量"
                ),
                components=[]
            )

        elif new_interaction.values[0] == "no":
            await interaction.edit_original_message(
                embed=VoiceSetupEmbed(
                    status="設定成功，請繼續下一步"
                ),
                components=[]
            )
        else:
            raise ValueError("Unknown option")

        return new_interaction.values[0], new_interaction

    @staticmethod
    async def ask_for_nsfw(interaction: Interaction):
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=VoiceSetupEmbed(
                status="限制級內容允許或禁止",
                title="請選擇是否允許所有成員在語音文字頻道中發送 NSFW 內容。",
                description="此設定可以再次使用指令：`/configure allow_nsfw:true/false` 來更改"
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

        await interaction.edit_original_message(
            embed=VoiceSetupEmbed(
                status="設定成功，請繼續下一步"
            ),
            components=[]
        )

        return new_interaction.values[0], new_interaction

    @staticmethod
    async def ask_for_lock_message_dm(interaction: Interaction):
        custom_id = str(uuid.uuid1())

        await interaction.response.send_message(
            embed=VoiceSetupEmbed(
                status="系統私訊通知開啟或關閉",
                title="請選擇是否開啟發送成員建立頻道成功時的私人訊息通知。",
                description="此設定可以再次使用指令：`/configure lock_message_dm:true/false` 來更改"
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

        await interaction.edit_original_message(
            embed=VoiceSetupEmbed(
                status="設定成功，請繼續下一步"
            ),
            components=[]
        )

        return new_interaction.values[0], new_interaction


def setup(bot: "Krabbe"):
    bot.add_cog(Setup(bot))
