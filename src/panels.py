from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING, Type, Optional

from disnake import Embed, ButtonStyle, MessageInteraction, ui, Interaction, SelectOption
from disnake.ui import View, Button

from src.classes.voice_channel import VoiceChannel
from src.embeds import ErrorEmbed, SuccessEmbed
from src.quick_ui import confirm_button, string_select, user_select, quick_modal, confirm_modal

if TYPE_CHECKING:
    from src.bot import Krabbe


async def check_channel(interaction: Interaction) -> Optional[VoiceChannel]:
    """
    Block the interaction if the user does not have a channel.
    :return: VoiceChannel object if the user has a channel
    """
    channel = await VoiceChannel.get_owned_channel_from_interaction(interaction)

    if not channel:
        await interaction.response.send_message(
            embed=ErrorEmbed("找不到你的頻道", "你可能還沒有創建屬於你的語音頻道"),
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
        emoji="🔊",
        disabled=True  # TODO: Implement join functionality
    )
    async def join_channel(self, button: Button, interaction: MessageInteraction) -> None:
        pass


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
        if not (channel := await check_channel(interaction)):
            return

        interaction, new_name = await quick_modal(
            interaction,
            title="✒️ 重新命名頻道",
            field_name="新名稱",
            placeholder="輸入新的頻道名稱",
            value=channel.channel_settings.channel_name or channel.channel.name,
            max_length=100,
            min_length=1,
            required=False
        )

        channel.channel_settings.channel_name = new_name

        await channel.channel_settings.upsert()
        await channel.apply_settings()

        await interaction.response.send_message(
            embed=SuccessEmbed(f"頻道已重新命名為 {new_name}" if new_name else "已重設頻道名稱"),
            ephemeral=True
        )

    @ui.button(
        label="移交所有權",
        custom_id="transfer_ownership",
        style=ButtonStyle.secondary,
        emoji="👥"
    )
    async def transfer_ownership(self, _button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await check_channel(interaction)):
            return

        interaction, selected_users = await user_select(interaction, "選擇新的頻道所有者")

        new_owner = selected_users[0]

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
        if not (channel := await check_channel(interaction)):
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
        emoji="👤",
        disabled=True  # TODO: Implement invite functionality
    )
    async def invite_member(self, button: Button, interaction: MessageInteraction) -> None:
        pass

    @ui.button(
        label="移出成員",
        custom_id="remove_member",
        style=ButtonStyle.danger,
        emoji="🚪"
    )
    async def remove_member(self, button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await check_channel(interaction)):
            return

        interaction, selected_users = await user_select(interaction, "選擇要移出的成員")

        member = selected_users[0]

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

        await interaction.response.edit_message(embed=SuccessEmbed(f"已移出 {member.name}"), components=[])

    @ui.button(
        label="頻道鎖",
        custom_id="lock_channel",
        style=ButtonStyle.secondary,
        emoji="🔒",
        disabled=True  # TODO: Implement channel lock functionality
    )
    async def lock_channel(self, button: Button, interaction: MessageInteraction) -> None:
        pass

    @ui.button(
        label="人數限制",
        custom_id="limit_members",
        style=ButtonStyle.secondary,
        emoji="🔢"
    )
    async def limit_members(self, button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await check_channel(interaction)):
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

        channel.channel_settings.user_limit = int(limit)

        await channel.channel_settings.upsert()
        await channel.apply_settings()

        await interaction.response.send_message(embed=SuccessEmbed(f"已設定人數限制為 {limit}"), ephemeral=True)


class VoiceSettings(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="比特率",
        custom_id="bitrate",
        style=ButtonStyle.secondary,
        emoji="📶"
    )
    async def bitrate(self, button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await check_channel(interaction)):
            return

        interaction, bitrate = await quick_modal(
            interaction,
            title="📶 設定比特率",
            field_name="比特率 (bit/s)",
            placeholder="輸入比特率",
            value=str(channel.channel_settings.bitrate or 64000),
            max_length=3,
            min_length=1,
            required=True
        )

        channel.channel_settings.bitrate = int(bitrate)

        await channel.channel_settings.upsert()
        await channel.apply_settings()

        await interaction.response.send_message(embed=SuccessEmbed(f"已設定比特率為 {bitrate}"), ephemeral=True)

    @ui.button(
        label="NSFW",
        custom_id="nsfw",
        style=ButtonStyle.secondary,
        emoji="🔞"
    )
    async def nsfw(self, button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await check_channel(interaction)):
            return

        channel.channel_settings.nsfw = not channel.channel_settings.nsfw

        await channel.channel_settings.upsert()
        await channel.apply_settings()

        await interaction.response.send_message(
            embed=SuccessEmbed(f"已切換 NSFW 狀態至 {'開' if channel.channel_settings.nsfw else '關'}"),
            ephemeral=True
        )

    @ui.button(
        label="語音區域",
        custom_id="rtc_region",
        style=ButtonStyle.secondary,
        emoji="🌍"
    )
    async def rtc_region(self, button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await check_channel(interaction)):
            return

        interaction, rtc_region = await string_select(
            interaction,
            placeholder="選擇語音區域",
            options=[SelectOption(label=region.name, description=str(region.id), value=region.id)
                     for region in (await interaction.guild.fetch_voice_regions())]
        )

        channel.channel_settings.rtc_region = rtc_region[0]

        await channel.channel_settings.upsert()
        await channel.apply_settings()

        await interaction.response.send_message(embed=SuccessEmbed(f"已設定語音區域為 {rtc_region[0]}"), ephemeral=True)

    @ui.button(
        label="音效版開關",
        custom_id="toggle_soundboard",
        style=ButtonStyle.secondary,
        emoji="🔊",
        disabled=True  # TODO: Implement soundboard toggle functionality
    )
    async def toggle_soundboard(self, button: Button, interaction: MessageInteraction) -> None:
        pass

    @ui.button(
        label="開關文字頻道",
        custom_id="toggle_text_channel",
        style=ButtonStyle.secondary,
        emoji="📝",
        disabled=True  # TODO: Implement text channel toggle functionality
    )
    async def toggle_text_channel(self, button: Button, interaction: MessageInteraction) -> None:
        pass

    @ui.button(
        label="媒體傳送許可",
        custom_id="media_permission",
        style=ButtonStyle.secondary,
        emoji="🎥",
        disabled=True  # TODO: Implement media permission functionality
    )
    async def media_permission(self, button: Button, interaction: MessageInteraction) -> None:
        pass

    @ui.button(
        label="慢速模式",
        custom_id="slowmode",
        style=ButtonStyle.secondary,
        emoji="⏳"
    )
    async def slowmode(self, button: Button, interaction: MessageInteraction) -> None:
        if not (channel := await check_channel(interaction)):
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

        channel.channel_settings.slowmode_delay = int(slowmode_delay)

        await channel.channel_settings.upsert()
        await channel.apply_settings()

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
