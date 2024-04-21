from dataclasses import dataclass
from typing import Dict, TYPE_CHECKING, Union

from disnake import Embed, ButtonStyle, MessageInteraction, ui
from disnake.ui import View, Button

if TYPE_CHECKING:
    from src.bot import Krabbe


@dataclass
class Panel:
    embed: Embed
    view: Union[View, type]


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
        view=JoinPanelView
    )
}


def setup_views(bot: "Krabbe"):
    """
    Initialize and register the views to the bot. This should only be called once after bot is started.

    :param bot: The bot instance.
    :return: None
    """
    for panel in panels.values():
        if isinstance(panel.view, type):
            panel.view = panel.view()

        bot.add_view(panel.view)
