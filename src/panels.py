from dataclasses import dataclass
from typing import Dict, TYPE_CHECKING

from disnake import Embed, ButtonStyle, MessageInteraction, ui
from disnake.ui import View, Button

if TYPE_CHECKING:
    from src.bot import Krabbe


@dataclass
class Panel:
    embed: Embed
    view: View


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
        view=JoinPanelView()
    )
}


def register_views(bot: "Krabbe"):
    """
    Register views to the bot. This should be called once the bot is started.

    :param bot: The bot instance.
    :return: None
    """
    for panel in panels.values():
        bot.add_view(panel.view)
