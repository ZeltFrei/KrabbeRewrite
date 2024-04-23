from typing import Union, Dict, TYPE_CHECKING

from disnake import PermissionOverwrite, Member, Role, Guild

if TYPE_CHECKING:
    from src.classes.guild_settings import GuildSettings
    from src.classes.channel_settings import ChannelSettings


def max_bitrate(guild: Guild) -> int:
    """
    Get the maximum bitrate for a guild
    :param guild: The guild to get the maximum bitrate for
    :return: The maximum bitrate for the guild
    """
    match guild.premium_tier:
        case 0:
            return 96000
        case 1:
            return 128000
        case 2:
            return 256000
        case 3:
            return 384000
        case _:
            return 96000


def generate_channel_metadata(
        channel_settings: "ChannelSettings",
        guild_settings: "GuildSettings"
) -> Dict[str, Union[str, int]]:
    """
    Generate the metadata for a channel

    :param channel_settings: The channel settings object
    :return: The metadata for the channel, usually can be passed as kwargs to a channel creation or edit method
    """
    if not channel_settings.is_resolved():
        raise ValueError("Channel settings must be resolved before generating metadata")

    if not guild_settings.is_resolved():
        raise ValueError("Guild settings must be resolved before generating metadata")

    return {
        "name": channel_settings.channel_name or f"{channel_settings.user}'s Channel",
        "overwrites": generate_permission_overwrites(channel_settings, guild_settings),
        "bitrate": max_bitrate(guild_settings.guild)
        if channel_settings.bitrate and channel_settings.bitrate >= max_bitrate(guild_settings.guild)
        else channel_settings.bitrate or 64000,
        "user_limit": channel_settings.user_limit or 0,
        "rtc_region": channel_settings.rtc_region or None,
        "nsfw": channel_settings.nsfw or False,
        "slowmode_delay": channel_settings.slowmode_delay or 0
    }


def generate_permission_overwrites(
        channel_settings: "ChannelSettings",
        guild_settings: "GuildSettings"
) -> Dict[Union[Role, Member], PermissionOverwrite]:
    """
    Generate
    :return:
    """
    return {}
