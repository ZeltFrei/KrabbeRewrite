from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING, Type, Optional

from disnake import Embed, ButtonStyle, MessageInteraction, ui
from disnake.ui import View, Button

if TYPE_CHECKING:
    from src.bot import Krabbe


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
    async def join_channel(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement join channel functionality
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
    async def rename_channel(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement rename channel functionality
        pass

    @ui.button(
        label="設定頻道狀態",
        custom_id="set_channel_activity",
        style=ButtonStyle.secondary,
        emoji="🔧"
    )
    async def set_channel_activity(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement set channel activity functionality
        pass

    @ui.button(
        label="移交所有權",
        custom_id="transfer_ownership",
        style=ButtonStyle.secondary,
        emoji="👥"
    )
    async def transfer_ownership(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement transfer ownership functionality
        pass

    @ui.button(
        label="移除頻道",
        custom_id="remove_channel",
        style=ButtonStyle.secondary,
        emoji="🗑️"
    )
    async def remove_channel(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement functionality to remove channel
        pass


class MemberSettings(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="邀請成員",
        custom_id="invite_member",
        style=ButtonStyle.green,
        emoji="👤"
    )
    async def invite_member(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement invite member functionality
        pass

    @ui.button(
        label="移出成員",
        custom_id="remove_member",
        style=ButtonStyle.danger,
        emoji="🚪"
    )
    async def remove_member(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement remove member functionality
        pass

    @ui.button(
        label="頻道鎖",
        custom_id="lock_channel",
        style=ButtonStyle.secondary,
        emoji="🔒"
    )
    async def lock_channel(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement channel lock functionality
        pass

    @ui.button(
        label="人數限制",
        custom_id="limit_members",
        style=ButtonStyle.secondary,
        emoji="🔢"
    )
    async def limit_members(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement member limit functionality
        pass


class VoiceSettings(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="音效版開關",
        custom_id="toggle_sounds",
        style=ButtonStyle.secondary,
        emoji="🔊"
    )
    async def toggle_sounds(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement sounds toggle functionality
        pass

    @ui.button(
        label="開關文字頻道",
        custom_id="toggle_text_channel",
        style=ButtonStyle.secondary,
        emoji="📝"
    )
    async def toggle_text_channel(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement text channel toggle functionality
        pass

    @ui.button(
        label="媒體傳送許可",
        custom_id="media_permission",
        style=ButtonStyle.secondary,
        emoji="🎥"
    )
    async def media_permission(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement media sending permission functionality
        pass

    @ui.button(
        label="慢速模式",
        custom_id="slow_mode",
        style=ButtonStyle.secondary,
        emoji="⏳"
    )
    async def slow_mode(self, button: Button, interaction: MessageInteraction):
        # TODO: Implement slow mode functionality
        pass


panels: Dict[str, Panel] = {
    "join_channel": Panel(
        embed=Embed(
            title="加入頻道",
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
            title="成員設定",
            description="管理頻道成員！"
        ),
        view_class=MemberSettings
    ),
    "voice_settings": Panel(
        embed=Embed(
            title="語音設定",
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
