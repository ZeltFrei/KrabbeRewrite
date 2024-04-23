from typing import Union, Dict, TYPE_CHECKING

from disnake import PermissionOverwrite, Member, Role

if TYPE_CHECKING:
    from src.classes.guild_settings import GuildSettings
    from src.classes.channel_settings import ChannelSettings


def generate_permission_overwrites(
        channel_settings: "ChannelSettings",
        guild_settings: "GuildSettings"
) -> Dict[Union[Role, Member], PermissionOverwrite]:
    """
    Generate
    :return:
    """
    return {}
