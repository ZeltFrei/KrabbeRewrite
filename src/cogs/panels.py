import logging

from disnake import ApplicationCommandInteraction, Option, OptionType
from disnake.ext.commands import Cog, slash_command

from src.bot import Krabbe
from src.panels import panels


class Panels(Cog):
    def __init__(self, bot: Krabbe):
        self.bot = bot
        self.logger = logging.getLogger("krabbe.panels")

    @slash_command(
        name="panel",
        description="傳送指定的控制面板",
        options=[
            Option(
                name="panel",
                description="要傳送的控制面板",
                type=OptionType.string,
                choices=[str(key) for key in panels.keys()],
                required=True
            )
        ],
        guild_ids=[975244147730546758]
    )
    async def panel(self, interaction: ApplicationCommandInteraction, panel: str):
        panel_to_send = panels.get(panel)

        await interaction.channel.send(
            embed=panel_to_send.embed,
            view=panel_to_send.view
        )

        await interaction.response.send_message("✅ 完成", ephemeral=True)


def setup(bot: Krabbe):
    bot.add_cog(Panels(bot))
