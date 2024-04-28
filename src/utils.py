from typing import Union, Dict, TYPE_CHECKING, List

from disnake import PermissionOverwrite, Member, Role, Guild, User

if TYPE_CHECKING:
    from src.classes.guild_settings import GuildSettings
    from src.classes.channel_settings import ChannelSettings


def max_bitrate(guild: Guild) -> int:
    """
    Get the maximum bitrate for a guild.

    :param guild: The guild to get the maximum bitrate for.
    :return: The maximum bitrate for the guild.
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
        owner: Union[Role, Member],
        members: List[Union[User, Member]],
        channel_settings: "ChannelSettings",
        guild_settings: "GuildSettings",
        locked: bool = False
) -> Dict[str, Union[str, int, PermissionOverwrite, bool]]:
    """
    Generate the metadata for a channel.

    :param owner: The owner of the channel.
    :param members: The members of the channel.
    :param channel_settings: The channel settings object.
    :param guild_settings: The guild settings object.
    :param locked: Whether the channel is locked.
    :return: The metadata for the channel, usually can be passed as kwargs to a channel creation or edit method.
    """
    return {
        "name": channel_settings.channel_name or f"{channel_settings.user} 的語音頻道",
        "overwrites": generate_permission_overwrites(owner, members, channel_settings, guild_settings, locked),
        "bitrate": max_bitrate(guild_settings.guild)
        if channel_settings.bitrate and channel_settings.bitrate >= max_bitrate(guild_settings.guild)
        else channel_settings.bitrate or 64000,
        "user_limit": channel_settings.user_limit or 0,
        "rtc_region": channel_settings.rtc_region or None,
        "nsfw": channel_settings.nsfw or False,
        "slowmode_delay": channel_settings.slowmode_delay or 0
    }


def generate_permission_overwrites(
        owner: Union[Role, Member],
        members: List[Union[User, Member]],
        channel_settings: "ChannelSettings",
        guild_settings: "GuildSettings",
        locked: bool = False,
) -> Dict[Union[Role, Member], PermissionOverwrite]:
    """
    Generate permission overwrites for a channel.

    :param owner: The owner of the channel.
    :param members: The members of the channel.
    :param channel_settings: The channel settings.
    :param guild_settings: The guild settings.
    :param locked: Whether the channel is locked.
    :return: The permission overwrites for the channel.
    """
    if locked:
        overwrites = guild_settings.category_channel.overwrites.copy()

        overwrites.update(
            {
                owner: PermissionOverwrite(
                    connect=True,
                    manage_channels=True
                ),
                guild_settings.base_role: PermissionOverwrite(
                    connect=True,
                    use_soundboard=channel_settings.soundboard_enabled,
                    attach_files=channel_settings.media_allowed,
                    embed_links=channel_settings.media_allowed
                )
            }
        )

        for member in members:
            overwrites[member] = PermissionOverwrite(
                connect=True
            )

        return overwrites

    else:
        overwrites = guild_settings.category_channel.overwrites.copy()

        overwrites.update(
            {
                owner: PermissionOverwrite(
                    connect=True,
                    manage_channels=True
                ),
                guild_settings.base_role: PermissionOverwrite(
                    connect=True,
                    use_soundboard=channel_settings.soundboard_enabled,
                    attach_files=channel_settings.media_allowed,
                    embed_links=channel_settings.media_allowed
                )
            }
        )

        return overwrites
