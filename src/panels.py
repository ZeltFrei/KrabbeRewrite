import asyncio
from abc import ABC
from datetime import datetime
from typing import Dict, TYPE_CHECKING, Optional, Literal

from ZeitfreiOauth import AsyncDiscordOAuthClient
from disnake import Embed, ButtonStyle, MessageInteraction, ui, Interaction, SelectOption, Message, Color, \
    TextInputStyle, AllowedMentions
from disnake.abc import Messageable
from disnake.ui import View, Button, Select, Modal, TextInput

from src.classes.voice_channel import VoiceChannel
from src.embeds import ErrorEmbed, SuccessEmbed, WarningEmbed, InfoEmbed, ChannelNotificationEmbed
from src.quick_ui import confirm_button, string_select, user_select, quick_modal, confirm_modal, quick_long_modal
from src.utils import max_bitrate, is_authorized

if TYPE_CHECKING:
    from src.bot import Krabbe

reset_option = SelectOption(label="取消選定", value="reset", emoji="🔄")


async def ensure_authorization(oauth_client: AsyncDiscordOAuthClient, interaction: Interaction) -> bool:
    """
    Ensure that the user is authorized. And respond to the interaction with an error message if not.

    :param oauth_client: The OAuth API client to use.
    :param interaction: The interaction to check.
    :return: Whether the user is authorized.
    """
    if await is_authorized(oauth_client, interaction.author.id):
        return True

    authorization_terms_panel = AuthorizationTerms(interaction.bot, oauth_client)

    await interaction.response.send_message(
        embed=authorization_terms_panel.embed,
        view=authorization_terms_panel,
        ephemeral=True
    )

    return False


async def ensure_owned_channel(interaction: Interaction) -> Optional[VoiceChannel]:
    """
    Block the interaction if the user does not have a channel.

    :return: VoiceChannel object if the user has a channel
    """
    channel = VoiceChannel.get_active_channel_from_interaction(interaction)

    if not channel:
        await interaction.response.send_message(
            embed=ErrorEmbed("找不到你的頻道", "你並不在一個動態語音頻道內！"),
            ephemeral=True
        )
        return None

    if channel.owner_id != interaction.author.id:
        await interaction.response.send_message(
            embed=ErrorEmbed("權限不足", "你不是這個頻道的所有者！"),
            ephemeral=True
        )
        return None

    return channel


async def feedback(interaction: Interaction) -> None:
    interaction, feedbacks = await quick_long_modal(
        interaction,
        modal=Modal(
            title="回報問題",
            components=[
                TextInput(
                    label="回報問題還是提供建議",
                    placeholder="回報問題 / 提供建議",
                    style=TextInputStyle.short,
                    custom_id="type",
                    required=True
                ),
                TextInput(
                    label="請闡述您遇到的問題",
                    placeholder="我在使用過程中遇到了...",
                    style=TextInputStyle.long,
                    custom_id="description",
                    required=False
                ),
                TextInput(
                    label="如何觸發該問題？",
                    placeholder="我是這樣做的...",
                    style=TextInputStyle.long,
                    custom_id="trigger",
                    required=False
                ),
                TextInput(
                    label="請您敘述您期望的建議",
                    placeholder="我希望能夠...",
                    style=TextInputStyle.long,
                    custom_id="suggestion",
                    required=False
                ),
                TextInput(
                    label="伺服器邀請連結",
                    placeholder="https://discord.gg/...\n"
                                "如果不輸入，機器人將會自動創建一個邀請連結。\n"
                                "輸入 `none` 來取消邀請連結的創建。",
                    style=TextInputStyle.short,
                    custom_id="invite",
                    required=False
                )
            ]
        )
    )

    invite = feedbacks.get("invite")

    if (not invite) and (invite.lower() != "none"):
        try:
            invite = (await interaction.channel.create_invite(unique=True)).url
        except Exception as error:
            invite = f"創建邀請連結時遇到了錯誤 {str(error)[:60]}"

    await interaction.bot.feedback_webhook.send(
        username=interaction.author.name,
        avatar_url=interaction.author.avatar.url,
        content=f"# 回報問題還是提供建議\n"
                f"{feedbacks['type']}\n"
                f"# 請闡述您遇到的問題\n"
                f"{feedbacks.get('description', '無')}\n"
                f"# 如何觸發該問題？\n"
                f"{feedbacks.get('trigger', '無')}\n"
                f"# 請您敘述您期望的建議\n"
                f"{feedbacks.get('suggestion', '無')}"
                f"# 伺服器邀請連結\n"
                f"{invite}"
                f"\n\n"
                f"**{interaction.author.mention}** ({interaction.author.id})",
        allowed_mentions=AllowedMentions.none()
    )

    await interaction.response.send_message(
        embed=SuccessEmbed(
            title="已回報問題",
            description="您的問題已經成功回報給我們了！"
        ),
        ephemeral=True
    )


class Panel(View, ABC):
    """
    The base class for all panels.
    """
    _instance: Optional["Panel"] = None

    def __init__(self, bot: "Krabbe"):
        super().__init__(timeout=None)

        self.bot: "Krabbe" = bot

    def __new__(cls, bot: "Krabbe") -> "Panel":
        if cls._instance:
            return cls._instance

        cls._instance = super().__new__(cls)

        return cls._instance

    @property
    def embed(self) -> Optional[Embed]:
        """
        Returns the embed of this panel. Can be overridden by subclasses.

        :return: The embed.
        """
        return None

    async def send_to(self, destination: Messageable) -> Message:
        """
        Send the panel to a messageable object.

        :param destination: The messageable object.
        :return: The message sent.
        """
        return await destination.send(
            embed=self.embed,
            view=self._instance
        )


class AuthorizationTerms(Panel):
    _instance: Optional["AuthorizationTerms"] = None

    def __init__(self, bot: "Krabbe", oauth_client: AsyncDiscordOAuthClient,
                 locale: Literal["zh_TW", "en_US"] = "zh_TW"):
        super().__init__(bot)

        self.oauth_client: AsyncDiscordOAuthClient = oauth_client
        self.locale: Literal["zh_TW", "en_US"] = locale

        self.add_item(Button(style=ButtonStyle.url, label="授權 / Authorize", url=oauth_client.api_base_url))

    def __new__(cls, bot: "Krabbe", oauth_client: AsyncDiscordOAuthClient) -> "AuthorizationTerms":
        if cls._instance:
            return cls._instance

        # noinspection PyTypeChecker
        cls._instance = super().__new__(cls, bot)
        return cls._instance

    @property
    def embed(self) -> Optional[Embed]:
        if self.locale == "zh_TW":
            embed = Embed(
                title="您必須先同意 Krabbe 2 的授權需求，以便您進行更多操作設定。",
                description="`Krabbe 2.0〡自動化語音&音樂系統` 以下說明簡稱 `本系統`\n"
                            "### 本系統為了打造更多豐富的機器人功能服務，需要請您同意。\n"
                            ">>>  1. 本系統只會進行一次授權，短時間內多次要求授權，屬於異常，請使用回饋按鈕回報。\n"
                            " 2. 本系統都會符合 [Discord 官方開發人員政策](https://discord.com/developers/docs/policies-and-agreements/developer-policy) 的所有條款。\n"
                            " 3. 本系統會在您授權許可後將您加入我們的 Discord 社群伺服器。\n"
                            " 4. 本系統並不會透過私訊來對您的帳戶發送與 __本系統__ 毫無相關的訊息。\n"
                            " 5. 本系統不會對您的個人資料頭像、個人資料橫幅、使用者名稱進行操作。\n"
                            " 6. 本系統不會將您的個人信箱進行任何操作。\n"
                            " 7. 本系統不支持&不接受用戶使用本系統來進行任何違反官方規定的行為。\n"
                            " 8. 本系統符合官方所有條款：\n"
                            "[開發人員政策](https://discord.com/developers/docs/policies-and-agreements/developer-policy), [開發人員服務條款](https://discord.com/developers/docs/policies-and-agreements/developer-terms-of-service), [社群守則](https://discord.com/guidelines), [服務條款](https://discord.com/terms)\n"
                            " 9. 您沒有同意也可以繼續使用本系統的其他功能，例如加入語音進行對話。\n"
                            "### 請點選 `授權` 按鈕來進行授權動作",
                timestamp=datetime.now()
            )

            embed.set_author(name="系統通知〡機器人授權同意書", icon_url="https://i.imgur.com/lsTtd9c.png")

            embed.set_footer(text="請注意，同意授權即代表您個人（Discord帳戶）許可授權項目的所有操作")

            return embed

        elif self.locale == "en_US":
            embed = Embed(
                title="You must agree to the authorization request from Krabbe 2 to proceed with more settings.",
                description="`Krabbe 2.0〡Auto Voice & Music System` is referred to as `this system` below.\n"
                            "### This system needs you to agree to the following:\n"
                            ">>>  1. This system will only request authorization once, multiple requests in a short period of time are abnormal, please report using the feedback button.\n"
                            " 2. This system will comply with all terms of the [Discord Official Developer Policy](https://discord.com/developers/docs/policies-and-agreements/developer-policy).\n"
                            " 3. This system will add you to our Discord community server after you authorize it.\n"
                            " 4. This system will not send you messages unrelated to __this system__ through private messages.\n"
                            " 5. This system will not operate on your personal data, avatar, profile banner, or username.\n"
                            " 6. This system will not operate on your personal email.\n"
                            " 7. This system does not support & accept users using this system to perform any behavior that violates official regulations.\n"
                            " 8. This system complies with all official terms:\n"
                            "[Developer Policy](https://discord.com/developers/docs/policies-and-agreements/developer-policy), [Developer Terms of Service](https://discord.com/developers/docs/policies-and-agreements/developer-terms-of-service), [Community Guidelines](https://discord.com/guidelines), [Terms of Service](https://discord.com/terms)\n"
                            " 9. You can continue to use other functions of this system without agreeing, such as joining a voice chat.\n"
                            "### Please click the `Authorize` button below to authorize",
                timestamp=datetime.now()
            )

            embed.set_author(
                name="System Notification〡Bot Authorization Agreement", icon_url="https://i.imgur.com/lsTtd9c.png"
            )

            embed.set_footer(
                text="Please note that by agreeing to the authorization, you (your Discord account) permit all operations of the authorized items."
            )

            return embed

        else:
            return None

    @ui.string_select(
        placeholder="語言選擇 / Language Selection",
        options=[
            SelectOption(label="繁體中文", value="zh_TW"),
            SelectOption(label="English", value="en_US")
        ],
        custom_id="locale"
    )
    async def select_locale(self, _select, interaction: MessageInteraction):
        self.locale = interaction.values[0]

        await interaction.response.edit_message(embed=self.embed, view=self)


class Title(Panel):
    @property
    def embed(self) -> Optional[Embed]:
        embed = Embed(
            color=0x2b2d31,
            title="語音頻道控制介面使用說明",
            description="""
### 加入私人語音頻道
 * **您可以透過此按鈕來加入上鎖的語音頻道。**
### 取消選定選項
 * **此選項為重新定位您的清單，方便您再次選擇相同設定。**
### 頻道設定
* 頻道名稱：
 - **設定語音頻道的名字。**
* 移交所有權：
 - **將頻道的設定權限轉移給其他成員。**
* 移除頻道：
 - **將頻道永久刪除。**
### 成員設定
* 邀請成員：
 - **使用短連結邀請成員加入您的語音頻道。**
* 移出成員：
 - **將成員移出您的語音頻道，並將使用權限刪除。**
* 頻道鎖：
 - **將頻道變更為私人頻道，透過邀請或輸入密碼加入。**
* 人數限制：
 - **設定頻道可以加入多少位成員。**
* 進出通知：
 - **設定語音頻道的進出通知。**
### 語音設定
* 語音位元率：
 - **選擇適合您頻道的位元率。**
* NSFW：
 - **允許或禁止您頻道發佈限制級內容。**
* 語音區域：
 - **選擇適合您頻道的伺服器語音區域。**
* 音效板：
 - **允許或禁止您頻道的音效板效果。**
* 媒體傳送許可：
 - **允許或禁止您頻道的檔案上傳。**
* 慢速模式：
 - **設定您頻道的發言時間速度。**
* 允許/禁止 畫面直播：
 - **設定語音頻道成員畫面分享權限。**
* 允許/禁止 建立語音活動：
 - **設定語音頻道成員建立活動權限。**
### 音樂設定
* 使用的音樂機器人為『__Krabbe 2.0__』
 - **請在語音文字頻道中使用 「 __/py__ 」來使用音樂功能**
* 召喚音樂機器人：
 - **在您的語音頻道中播放音樂。**
* 允許/禁止頻道成員使用音樂：
 - **由其他成員操控您的音樂。**
## 使用「回報問題&提供建議」按鈕聯絡我們
            """
        )

        embed.set_author(name="Krabbe 2 - Voice Channel 自動化語音頻道", icon_url="https://i.imgur.com/lsTtd9c.png")

        embed.add_field(
            name="系統為什麼要我進行授權操作？",
            value="* **您接下來的任何驗證操作都不會對您的帳戶造成問題**\n"
                  "* **驗證收集的任何資料都是符合 Discord 社群規範**\n"
                  "* **這些資料僅為了使功能更加完善，讓 Krabbe 2 自由化設定提高**\n"
                  "* **您可以選擇不進行驗證，但同時您也無法進一步使用更多內容**",
            inline=False
        )

        embed.set_image(url="https://i.imgur.com/BaXj26Y.gif")

        embed.set_footer(text="如果遇到交互失敗的訊息，屬於正常現象，重新操作即可。")

        return embed


class JoinChannel(Panel):
    @ui.button(
        label="加入私人語音頻道",
        custom_id="join_channel",
        style=ButtonStyle.green,
        emoji="🔓"
    )
    async def join_channel(self, button: Button, interaction: MessageInteraction) -> None:
        interaction, pin_code = await quick_modal(
            interaction,
            title="🔒 輸入 PIN 碼",
            field_name="請向擁有者要求六位數 PIN 碼以求加入語音",
            placeholder="123456",
            required=True
        )

        channel = VoiceChannel.locked_channels.get(pin_code)

        if not channel:
            return await interaction.response.send_message(
                embed=ErrorEmbed("找不到這個頻道"),
                ephemeral=True
            )

        await channel.add_member(interaction.author)

        await interaction.response.send_message(
            embed=SuccessEmbed(
                title="已成功取得頻道權限！",
                description=f"你可以點擊或下方的連結 {channel.channel.mention} 來加入頻道"
            ),
            components=[
                Button(
                    style=ButtonStyle.url,
                    label=channel.channel.name,
                    url=channel.channel.jump_url
                )
            ],
            ephemeral=True
        )

    @ui.button(
        label="回報問題&提供建議",
        emoji="🔧",
        custom_id="feedback"
    )
    async def feedback(self, _button: Button, interaction: MessageInteraction):
        await feedback(interaction)


class ChannelSettings(Panel):
    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        return await ensure_authorization(interaction.bot.oauth, interaction)

    @ui.string_select(
        placeholder="⚙️ 頻道類設定",
        options=[
            reset_option,
            SelectOption(label="頻道名稱", value="rename_channel", description="重新命名頻道", emoji="✒️"),
            SelectOption(label="移交所有權", value="transfer_ownership", description="將頻道所有權轉移", emoji="👑"),
            SelectOption(label="移除頻道", value="remove_channel", description="讓頻道永遠沉眠", emoji="🗑️")
        ],
        custom_id="channel_settings"
    )
    async def select_setting(self, _select, interaction: MessageInteraction):
        match interaction.values[0]:
            case "rename_channel":
                await self.rename_channel(interaction)
            case "transfer_ownership":
                await self.transfer_ownership(interaction)
            case "remove_channel":
                await self.remove_channel(interaction)

        await interaction.edit_original_message(view=self)

    @staticmethod
    async def rename_channel(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, new_name = await quick_modal(
            interaction,
            title="✒️ 重新命名頻道",
            field_name="新名稱",
            placeholder=f"{interaction.author}'s channel",
            value=channel.channel_settings.channel_name or channel.channel.name,
            max_length=100,
            min_length=1,
            required=False
        )

        await interaction.response.defer(ephemeral=True)

        channel.channel_settings.channel_name = new_name

        task = await channel.apply_setting_and_permissions()

        try:
            await asyncio.wait_for(task, timeout=5)

            await channel.channel_settings.upsert()

            await interaction.edit_original_message(
                embed=SuccessEmbed(f"頻道已重新命名為 {new_name}" if new_name else "已重設頻道名稱"),
            )

            await channel.guild_settings.log_event(
                f"{interaction.author.mention} 重新命名了頻道為 {new_name}"
            )

            return
        except asyncio.TimeoutError:
            channel.channel_settings.channel_name = channel.channel.name

            await interaction.edit_original_message(
                embed=WarningEmbed(
                    title="你太快了！",
                    description="因為 Discord API 的限制，\n"
                                "請稍後再試著更改頻道名稱！"
                ),
            )

            return

    @staticmethod
    async def transfer_ownership(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, selected_users = await user_select(interaction, "選擇新的頻道所有者")

        new_owner = selected_users[0]

        if new_owner.id == interaction.author.id:
            return await interaction.response.edit_message(
                embed=ErrorEmbed("你不能將所有權移交給你自己"), components=[]
            )

        if new_owner not in channel.channel.members:
            return await interaction.response.edit_message(
                embed=ErrorEmbed("這個成員不在這個頻道裡"), components=[]
            )

        if new_owner.bot:
            return await interaction.response.edit_message(
                embed=ErrorEmbed("你不能將所有權移交給機器人"), components=[]
            )

        for active_voice_channel in VoiceChannel.active_channels.values():
            if active_voice_channel.owner_id == new_owner.id:
                return await interaction.response.edit_message(
                    embed=ErrorEmbed(
                        title="錯誤",
                        description="這個成員已經擁有一個頻道了！"
                                    "如果他剛來到這個頻道，"
                                    "請等待他原有的頻道被刪除或是請他手動刪除頻道！"
                    ), components=[]
                )

        interaction, confirmed = await confirm_modal(
            interaction,
            text=f"確定要移交所有權給 {new_owner.name} 嗎？",
            confirmation_message="我確定"
        )

        if not confirmed:
            return await interaction.response.edit_message(embed=ErrorEmbed("已取消"))

        await channel.transfer_ownership(new_owner)

        await interaction.response.edit_message(embed=SuccessEmbed(f"已移交所有權給 {new_owner.name}"), components=[])

    @staticmethod
    async def remove_channel(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, confirmed = await confirm_modal(
            interaction,
            text="確定要移除頻道嗎？",
            confirmation_message="我確定"
        )

        if not confirmed:
            return await interaction.response.send_message(embed=ErrorEmbed("已取消"))

        await channel.remove()

        await interaction.response.send_message(embed=SuccessEmbed("頻道已移除"), ephemeral=True)


class MemberSettings(Panel):
    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        return await ensure_authorization(interaction.bot.oauth, interaction)

    @ui.string_select(
        placeholder="👥 成員設定",
        options=[
            reset_option,
            SelectOption(label="邀請成員", value="invite_member", description="邀請成員加入頻道", emoji="📩"),
            SelectOption(label="移出成員", value="remove_member", description="移出成員出頻道", emoji="🚪"),
            SelectOption(label="頻道鎖", value="lock_channel", description="鎖定或解鎖頻道", emoji="🔒"),
            SelectOption(label="人數限制", value="limit_members", description="設定頻道人數上限", emoji="🔢"),
            SelectOption(label="進出通知", value="join_notifications", description="設定進出通知", emoji="🔔")
        ],
        custom_id="member_settings"
    )
    async def select_setting(self, _select, interaction: MessageInteraction):
        match interaction.values[0]:
            case "invite_member":
                await self.invite_member(interaction)
            case "remove_member":
                await self.remove_member(interaction)
            case "lock_channel":
                await self.lock_channel(interaction)
            case "limit_members":
                await self.limit_members(interaction)
            case "join_notifications":
                await self.join_notifications(interaction)

        await interaction.edit_original_message(view=self)

    @staticmethod
    async def invite_member(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        if not channel.is_locked():
            invite = await channel.channel.create_invite(max_age=21600, unique=False)

            return await interaction.response.send_message(
                embed=InfoEmbed(
                    title="這個語音頻道當前未設定密碼，屬於公開頻道",
                    description=f"您可以複製此語音邀請連結來邀請完成驗證之成員。\n{invite.url}"
                ),
                ephemeral=True
            )

        interaction, selected_users = await user_select(interaction, "選擇要邀請的成員")

        member = selected_users[0]

        if member.id == interaction.author.id:
            return await interaction.response.edit_message(
                embed=ErrorEmbed("你不能邀請自己"), components=[]
            )

        invite = await channel.channel.create_invite(max_age=180, unique=True, max_uses=1)

        _ = interaction.bot.loop.create_task(channel.add_member(member))

        await interaction.response.edit_message(
            embed=SuccessEmbed(
                title=f"已邀請 {member.name}",
                description=f"你可以使用這個連結來讓他們加入 {invite.url}\n"
                            "如果他沒有在 180 秒內加入，你將需要再次邀請他！"
            ),
            components=[]
        )

    @staticmethod
    async def remove_member(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, selected_users = await user_select(interaction, "選擇要移出的成員")

        member = selected_users[0]

        if member not in channel.channel.members + channel.member_queue:
            return await interaction.response.edit_message(
                embed=ErrorEmbed("很抱歉，您的語音頻道並沒有這位成員"), components=[]
            )

        if member.id == interaction.author.id:
            return await interaction.response.edit_message(
                embed=ErrorEmbed("你不能移出自己"), components=[]
            )

        interaction, confirmed = await confirm_button(
            interaction,
            message=f"確定要移出 {member.name} 嗎？"
        )

        if not confirmed:
            return await interaction.response.edit_message(embed=ErrorEmbed("已取消"), components=[])

        await channel.remove_member(member)

        await channel.notify(
            embed=InfoEmbed(
                title="擁有者移除頻道成員與權限",
                description=f"{member.mention} 被移出且被刪除頻道使用權限！"
            )
        )

        await interaction.response.edit_message(embed=SuccessEmbed(f"已移出 {member.name}"), components=[])

    @staticmethod
    async def lock_channel(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        if channel.is_locked():
            interaction, confirmed = await confirm_button(message="確定要解鎖頻道嗎？", interaction=interaction)

            if confirmed:
                await channel.unlock()

                await interaction.response.edit_message(embed=SuccessEmbed("已解鎖頻道"), components=[])
            else:
                await interaction.response.edit_message(embed=ErrorEmbed("已取消"), components=[])

            return

        interaction, confirmed = await confirm_button(message="確定要鎖定頻道嗎？", interaction=interaction)

        if not confirmed:
            return await interaction.response.edit_message(embed=ErrorEmbed("已取消"), components=[])

        pin_code = channel.generate_pin_code()

        await channel.lock(pin_code)

        await interaction.response.edit_message(
            embed=SuccessEmbed(
                title="已鎖定頻道！",
                description=f"請使用這個 PIN 碼來讓其他成員加入：\n```{pin_code}```"
            ),
            components=[]
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 鎖定了頻道 {channel.channel.name}"
        )

    @staticmethod
    async def limit_members(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, limit = await quick_modal(
            interaction,
            title="🔢 設定人數限制",
            field_name="請輸入 0~99 的數字來做為您的頻道人數上限，0 為無限制",
            placeholder="輸入人數限制",
            value=str(channel.channel_settings.user_limit or 0),
            max_length=3,
            min_length=1,
            required=True
        )

        if int(limit) < 0:
            return await interaction.response.send_message(
                embed=ErrorEmbed("人數限制必須大於 0"),
                ephemeral=True
            )

        if int(limit) >= 100:
            return await interaction.response.send_message(
                embed=ErrorEmbed("人數限制必須小於 100"),
                ephemeral=True
            )

        channel.channel_settings.user_limit = int(limit)

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道加入人數限制",
                description=f"此語音頻道的人數上限為：{limit} 位。"
            )
        )

        await interaction.response.send_message(embed=SuccessEmbed(f"已設定人數限制為 {limit}"), ephemeral=True)

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的人數上限為 {limit}"
        )

    @staticmethod
    async def join_notifications(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        channel.channel_settings.join_notifications = not channel.channel_settings.join_notifications

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道進出通知",
                description=f"進出通知已{'啟用' if channel.channel_settings.join_notifications else '禁用'}"
            )
        )

        await interaction.response.send_message(
            embed=SuccessEmbed(f"已{'啟用' if channel.channel_settings.join_notifications else '禁用'}進出通知"),
            ephemeral=True
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的進出通知為 {channel.channel_settings.join_notifications}"
        )


class VoiceSettings(Panel):
    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        return await ensure_authorization(interaction.bot.oauth, interaction)

    @ui.string_select(
        placeholder="🔊 語音設定",
        options=[
            reset_option,
            SelectOption(label="語音位元率", value="bitrate", description="調整語音位元率", emoji="🎶"),
            SelectOption(label="NSFW", value="nsfw", description="啟用或禁用 NSFW 內容", emoji="🔞"),
            SelectOption(label="語音區域", value="rtc_region", description="調整語音區域", emoji="🌐"),
            SelectOption(label="音效板", value="toggle_soundboard", description="啟用或禁用音效板", emoji="🔉"),
            SelectOption(
                label="檔案上傳", value="media_permission", description="設定語音頻道成員檔案上傳權限", emoji="📎"
            ),
            SelectOption(label="慢速模式", value="slowmode", description="設定慢速模式", emoji="⏳"),
            SelectOption(
                label="允許/禁止畫面直播", value="stream", description="設定語音頻道成員畫面分享權限", emoji="🔴"
            ),
            SelectOption(
                label="允許/禁止建立語音活動", value="embedded_activities", description="設定語音頻道成員建立活動權限",
                emoji="🎮"
            )
        ],
        custom_id="voice_settings"
    )
    async def select_setting(self, _select: Select, interaction: MessageInteraction):
        match interaction.values[0]:
            case "bitrate":
                await self.bitrate(interaction)
            case "nsfw":
                await self.nsfw(interaction)
            case "rtc_region":
                await self.rtc_region(interaction)
            case "toggle_soundboard":
                await self.toggle_soundboard(interaction)
            case "media_permission":
                await self.media_permission(interaction)
            case "slowmode":
                await self.slowmode(interaction)
            case "stream":
                await self.toggle_stream(interaction)
            case "embedded_activities":
                await self.use_embedded_activities(interaction)

        await interaction.edit_original_message(view=self)

    @staticmethod
    async def bitrate(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, selected_bitrate = await string_select(
            interaction,
            placeholder="選擇語音位元率",
            options=[
                SelectOption(label="64 Kbps", value="64000"),
                SelectOption(label="96 Kbps", value="96000"),
                SelectOption(label="128 Kbps", value="128000"),
                SelectOption(label="256 Kbps", value="256000"),
                SelectOption(label="384 Kbps", value="384000")
            ]
        )

        channel.channel_settings.bitrate = int(selected_bitrate[0])

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道位元率",
                description=f"此語音頻道的位元率調整為：{int(selected_bitrate[0]) // 1000} Kbps"
            )
        )

        await interaction.response.send_message(
            embeds=[SuccessEmbed(f"已設定比特率為 {int(selected_bitrate[0]) // 1000} Kbps")] +
                   ([
                        WarningEmbed("注意", "這個伺服器的加成等級可能限制了比特率")
                    ] if int(selected_bitrate[0]) > max_bitrate(interaction.guild) else []),
            ephemeral=True
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的比特率為 {int(selected_bitrate[0]) // 1000} Kbps"
        )

    @staticmethod
    async def nsfw(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        channel.channel_settings.nsfw = not channel.channel_settings.nsfw

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        if channel.guild_settings.allow_nsfw:
            await channel.guild_settings.log_event(
                f"{interaction.author.mention} 設定了 {channel.channel.name} 的 NSFW 為 {channel.channel_settings.nsfw}"
            )

            await channel.notify(
                embed=InfoEmbed(
                    title="當前語音文字 NSFW 限制級內容",
                    description=f"NSFW 已{'啟用，允許限制級內容' if channel.channel_settings.nsfw else '禁用'}"
                )
            )

            await interaction.response.send_message(
                embed=SuccessEmbed(f"NSFW：{'開' if channel.channel_settings.nsfw else '關'}"),
                ephemeral=True
            )

        else:
            await interaction.response.send_message(
                embeds=[
                    SuccessEmbed(f"NSFW：{'開' if channel.channel_settings.nsfw else '關'}"),
                    WarningEmbed(
                        title="您的設定檔已更新並保存，但此伺服器設定禁止 NSFW 內容。",
                        description=f"您的頻道因為 {interaction.guild.name} 伺服器設定的關係，無法變更為 NSFW 頻道。"
                    )
                ],
                ephemeral=True
            )

    @staticmethod
    async def rtc_region(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, rtc_region = await string_select(
            interaction,
            placeholder="選擇語音區域",
            options=[SelectOption(label=region.name, description=str(region.id), value=region.id)
                     for region in (await interaction.guild.fetch_voice_regions())]
        )

        channel.channel_settings.rtc_region = rtc_region[0]

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道伺服器區域位置",
                description=f"此語音頻道的伺服器區域調整為：{rtc_region[0]}"
            )
        )

        await interaction.response.edit_message(embed=SuccessEmbed(f"已設定語音區域為 {rtc_region[0]}"))

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的語音區域為 {rtc_region[0]}"
        )

    @staticmethod
    async def toggle_soundboard(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        channel.channel_settings.soundboard_enabled = not channel.channel_settings.soundboard_enabled

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道音效版的設定",
                description=f"此語音頻道的音效板調整為：{'啟用' if channel.channel_settings.soundboard_enabled else '關閉'}"
            )
        )

        await interaction.response.send_message(
            embed=SuccessEmbed(f"音效板：{'開' if channel.channel_settings.soundboard_enabled else '關'}"),
            ephemeral=True
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的音效板為 {channel.channel_settings.soundboard_enabled}"
        )

    @staticmethod
    async def media_permission(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        channel.channel_settings.media_allowed = not channel.channel_settings.media_allowed

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道檔案上傳的權限",
                description=f"此語音頻道的檔案上傳調整為：{'允許' if channel.channel_settings.media_allowed else '禁止'}"
            )
        )

        await interaction.response.send_message(
            embed=SuccessEmbed(f"媒體傳送許可：{'開' if channel.channel_settings.media_allowed else '關'}"),
            ephemeral=True
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的媒體傳送許可為 {channel.channel_settings.media_allowed}"
        )

    @staticmethod
    async def slowmode(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, slowmode_delay = await quick_modal(
            interaction,
            title="⏳ 設定慢速模式",
            field_name="秒數",
            placeholder="輸入慢速模式秒數",
            value=str(channel.channel_settings.slowmode_delay or 0),
            max_length=3,
            min_length=1,
            required=True
        )

        if int(slowmode_delay) < 0:
            return await interaction.response.send_message(
                embed=ErrorEmbed("慢速模式秒數必須大於 0"),
                ephemeral=True
            )

        if int(slowmode_delay) > 21600:
            return await interaction.response.send_message(
                embed=ErrorEmbed("慢速模式秒數必須小於 21600"),
                ephemeral=True
            )

        channel.channel_settings.slowmode_delay = int(slowmode_delay)

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道發言時間限制",
                description=f"此語音頻道的文字頻道發言時速調整為：{slowmode_delay} 秒"
            )
        )

        await interaction.response.send_message(
            embed=SuccessEmbed(f"已設定慢速模式為 {slowmode_delay} 秒"), ephemeral=True
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的慢速模式為 {slowmode_delay} 秒"
        )

    @staticmethod
    async def toggle_stream(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        channel.channel_settings.stream = not channel.channel_settings.stream

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道直播 / 視訊的權限",
                description=f"此語音頻道的直播 / 視訊調整為：{'允許' if channel.channel_settings.stream else '禁止'}"
            )
        )

        await interaction.response.send_message(
            embed=SuccessEmbed(f"直播 / 視訊：{'開' if channel.channel_settings.stream else '關'}"),
            ephemeral=True
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的直播 / 視訊許可為 {channel.channel_settings.stream}"
        )

    @staticmethod
    async def use_embedded_activities(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        channel.channel_settings.use_embedded_activities = not channel.channel_settings.use_embedded_activities

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道使用活動的權限",
                description=f"此語音頻道的活動權限調整為：{'允許' if channel.channel_settings.use_embedded_activities else '禁止'}"
            )
        )

        await interaction.response.send_message(
            embed=SuccessEmbed(f"使用活動：{'開' if channel.channel_settings.use_embedded_activities else '關'}"),
            ephemeral=True
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的使用活動許可為 {channel.channel_settings.use_embedded_activities}"
        )


class MusicSettings(Panel):
    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        return await ensure_authorization(interaction.bot.oauth, interaction)

    @ui.string_select(
        placeholder="🎵 音樂設定",
        options=[
            reset_option,
            SelectOption(
                label="播放 ZeitFrei 電台", value="play_radio", description="在您的語音頻道播放 ZeitFrei 電台", emoji="📻"
            ),
            SelectOption(
                label="允許/禁止頻道成員使用音樂", value="toggle_music", description="啟用或禁用音樂功能", emoji="🎶"
            )
        ],
        custom_id="music_settings"
    )
    async def select_setting(self, _select: Select, interaction: MessageInteraction):
        match interaction.values[0]:
            case "play_radio":
                await self.play_radio(interaction)
            case "toggle_music":
                await self.toggle_music(interaction)

        await interaction.edit_original_message(view=self)

    @staticmethod
    async def play_radio(interaction: MessageInteraction) -> None:
        if not await ensure_owned_channel(interaction):
            return

        await interaction.bot.get_slash_command("py").invoke(interaction)

    @staticmethod
    async def toggle_music(interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        channel.channel_settings.shared_music_control = not channel.channel_settings.shared_music_control

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="共享音樂控制",
                description=f"此頻道的共享音樂控制設定為：{'允許' if channel.channel_settings.shared_music_control else '禁止'}"
            )
        )

        await interaction.response.send_message(
            embed=SuccessEmbed(f"共享音樂控制：{'開' if channel.channel_settings.shared_music_control else '關'}"),
            ephemeral=True
        )

        await channel.guild_settings.log_event(
            f"{interaction.author.mention} 設定了 {channel.channel.name} 的共享音樂控制為為 {channel.channel_settings.shared_music_control}"
        )


class LockChannel(Panel):
    @property
    def embed(self) -> Embed:
        embed = Embed(
            title="讓頻道設定為私人頻道。",
            description="> 點選下面的按鈕，馬上將您的頻道進行鎖定。\n"
                        "> 請別擔心，這個按鈕只有身為頻道擁有者的您才能使用。\n"
                        "> 如您找不到按鈕，您也可以前往設定區域進行點選。",
            color=Color.blurple()
        )

        embed.set_image("https://i.imgur.com/8tMgmWa.png")

        return embed

    @ui.button(
        label="鎖定頻道",
        custom_id="lock_channel",
        emoji="🔒"
    )
    async def lock_channel(self, _button: Button, interaction: MessageInteraction) -> None:
        await MemberSettings.lock_channel(interaction)

    @ui.button(
        label="播放音樂",
        custom_id="play_music",
        emoji="🎵"
    )
    async def play_music(self, _button: Button, interaction: MessageInteraction) -> None:
        await MusicSettings.summon_bot(interaction)


class ChannelRestored(Panel):
    @property
    def embed(self) -> Embed:
        embed = ChannelNotificationEmbed(
            left_message="系統伺服器完成重新啟動！請注意，所有邀請已刪除",
            right_message="您可能會遇到一些問題可以點選按鈕進行回報",
            image_url="https://i.imgur.com/9Pt1NZA.png"
        )

        embed.set_footer(text="請重新建立語音頻道讓功能保持正常狀態")

        return embed

    @ui.button(
        label="回報問題&提供建議",
        emoji="🔧",
        custom_id="feedback"
    )
    async def feedback(self, _button: Button, interaction: MessageInteraction):
        await feedback(interaction)


panels: Dict[str, Panel] = {}


def setup_views(bot: "Krabbe") -> None:
    """
    Initialize and register the views to the bot. This should only be called once after bot is started.

    :param bot: The bot instance.
    :return: None
    """
    panels.update(
        {
            "title": Title(bot),
            "join_channel": JoinChannel(bot),
            "channel_settings": ChannelSettings(bot),
            "member_settings": MemberSettings(bot),
            "voice_settings": VoiceSettings(bot),
            "music_settings": MusicSettings(bot)
        }
    )

    for panel in panels.values():
        bot.add_view(panel)
