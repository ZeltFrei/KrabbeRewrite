import asyncio
from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING, Type, Optional

from disnake import Embed, ButtonStyle, MessageInteraction, ui, Interaction, SelectOption
from disnake.ui import View, Button

from src.classes.voice_channel import VoiceChannel
from src.embeds import ErrorEmbed, SuccessEmbed, WarningEmbed, InfoEmbed
from src.quick_ui import confirm_button, string_select, user_select, quick_modal, confirm_modal
from src.utils import max_bitrate

if TYPE_CHECKING:
    from src.bot import Krabbe


async def ensure_owned_channel(interaction: Interaction) -> Optional[VoiceChannel]:
    """
    Block the interaction if the user does not have a channel.
    :return: VoiceChannel object if the user has a channel
    """
    channel = await VoiceChannel.get_active_channel_from_interaction(interaction)

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


@dataclass
class Panel:
    embed: Embed
    view_class: Type[View]
    view: Optional[View] = field(default=None, init=False)


class JoinChannel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="加入頻道",
        custom_id="join_channel",
        style=ButtonStyle.green,
        emoji="🔊"
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


class ChannelSettings(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="重新命名",
        custom_id="rename_channel",
        style=ButtonStyle.secondary,
        emoji="✒️"
    )
    async def rename_channel(self, _button: Button, interaction: MessageInteraction) -> None:
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

    @ui.button(
        label="移交所有權",
        custom_id="transfer_ownership",
        style=ButtonStyle.secondary,
        emoji="👥"
    )
    async def transfer_ownership(self, _button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, selected_users = await user_select(interaction, "選擇新的頻道所有者")

        new_owner = selected_users[0]

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

        if new_owner.id == interaction.author.id:
            return await interaction.response.edit_message(
                embed=ErrorEmbed("你不能將所有權移交給你自己"), components=[]
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

    @ui.button(
        label="移除頻道",
        custom_id="remove_channel",
        style=ButtonStyle.secondary,
        emoji="🗑️"
    )
    async def remove_channel(self, _button: Button, interaction: MessageInteraction) -> None:
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


class MemberSettings(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="邀請成員",
        custom_id="invite_member",
        style=ButtonStyle.green,
        emoji="👤"
    )
    async def invite_member(self, _button: Button, interaction: MessageInteraction) -> None:
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

    @ui.button(
        label="移出成員",
        custom_id="remove_member",
        style=ButtonStyle.danger,
        emoji="🚪"
    )
    async def remove_member(self, _button: Button, interaction: MessageInteraction) -> None:
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
                title="成員移除",
                description=f"{member.mention} 被移出了這個頻道！"
            )
        )

        await interaction.response.edit_message(embed=SuccessEmbed(f"已移出 {member.name}"), components=[])

    @ui.button(
        label="頻道鎖",
        custom_id="lock_channel",
        style=ButtonStyle.secondary,
        emoji="🔒"
    )
    async def lock_channel(self, _button: Button, interaction: MessageInteraction) -> None:
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

        return await interaction.response.edit_message(
            embed=SuccessEmbed(
                title="已鎖定頻道！",
                description=f"請使用這個 PIN 碼來讓其他成員加入：\n```{pin_code}```"
            ),
            components=[]
        )

    @ui.button(
        label="人數限制",
        custom_id="limit_members",
        style=ButtonStyle.secondary,
        emoji="🔢"
    )
    async def limit_members(self, _button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, limit = await quick_modal(
            interaction,
            title="🔢 設定人數限制",
            field_name="人數",
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

        await interaction.response.send_message(embed=SuccessEmbed(f"已設定人數限制為 {limit}"), ephemeral=True)


class VoiceSettings(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="語音位元率",
        custom_id="bitrate",
        style=ButtonStyle.secondary,
        emoji="📶"
    )
    async def bitrate(self, _button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        interaction, bitrate = await quick_modal(
            interaction,
            title="📶 設定比特率",
            field_name="比特率 (bit/s)",
            placeholder="輸入比特率",
            value=str(channel.channel_settings.bitrate or 64000),
            max_length=6,
            min_length=5,
            required=True
        )

        if int(bitrate) < 8000 or int(bitrate) > 384000:
            return await interaction.response.send_message(
                embed=ErrorEmbed("比特率必須介於 8000 和 384000 之間"),
                ephemeral=True
            )

        channel.channel_settings.bitrate = int(bitrate)

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

        await channel.notify(
            embed=InfoEmbed(
                title="當前語音頻道位元率",
                description=f"此語音頻道的位元率調整為：{int(bitrate) // 1000} kbps"
            )
        )

        await interaction.response.send_message(
            embeds=[SuccessEmbed(f"已設定比特率為 {bitrate}")] +
                   [
                       WarningEmbed("注意", "這個伺服器的加成等級可能限制了比特率")
                   ] if int(bitrate) > max_bitrate(interaction.guild) else [],
            ephemeral=True
        )

    @ui.button(
        label="NSFW",
        custom_id="nsfw",
        style=ButtonStyle.secondary,
        emoji="🔞"
    )
    async def nsfw(self, _button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await ensure_owned_channel(interaction)):
            return

        channel.channel_settings.nsfw = not channel.channel_settings.nsfw

        await channel.channel_settings.upsert()
        await channel.apply_setting_and_permissions()

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

    @ui.button(
        label="語音區域",
        custom_id="rtc_region",
        style=ButtonStyle.secondary,
        emoji="🌍"
    )
    async def rtc_region(self, _button: Button, interaction: MessageInteraction) -> None:
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

    @ui.button(
        label="音效板",
        custom_id="toggle_soundboard",
        style=ButtonStyle.secondary,
        emoji="🔊",
    )
    async def toggle_soundboard(self, _button: Button, interaction: MessageInteraction) -> None:
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

    @ui.button(
        label="媒體傳送許可",
        custom_id="media_permission",
        style=ButtonStyle.secondary,
        emoji="🎥",
    )
    async def media_permission(self, _button: Button, interaction: MessageInteraction) -> None:
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

    @ui.button(
        label="慢速模式",
        custom_id="slowmode",
        style=ButtonStyle.secondary,
        emoji="⏳"
    )
    async def slowmode(self, _button: Button, interaction: MessageInteraction) -> None:
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


panels: Dict[str, Panel] = {
    "join_channel": Panel(
        embed=Embed(
            title="➕ 加入頻道",
            description="點擊下方按鈕來加入一個私人頻道！"
        ),
        view_class=JoinChannel
    ),
    "channel_settings": Panel(
        embed=Embed(
            title="⚙️ 頻道設定",
            description="透過下方的按鈕來對你的頻道進行設定！"
        ),
        view_class=ChannelSettings
    ),
    "member_settings": Panel(
        embed=Embed(
            title="👥 成員設定",
            description="管理頻道成員！"
        ),
        view_class=MemberSettings
    ),
    "voice_settings": Panel(
        embed=Embed(
            title="🔊 語音設定",
            description="調整語音相關設定！"
        ),
        view_class=VoiceSettings
    )
}


def setup_views(bot: "Krabbe") -> None:
    """
    Initialize and register the views to the bot. This should only be called once after bot is started.

    :param bot: The bot instance.
    :return: None
    """
    for panel in panels.values():
        panel.view = panel.view_class()
        bot.add_view(panel.view)
