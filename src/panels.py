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


class JoinPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="加入頻道",
        custom_id="join_channel",
        style=ButtonStyle.green,
        emoji="🔊"
    )
    async def join_channel(self, button: Button, interaction: MessageInteraction):
        pass


panels: Dict[str, Panel] = {
    "join_channel": Panel(
        embed=Embed(
            title="加入頻道",
            description="點擊下方按鈕來加入一個私人頻道！"  # TODO: Design this
        ),
        view_class=JoinPanelView
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
