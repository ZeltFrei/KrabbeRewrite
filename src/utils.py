from datetime import datetime
from typing import Union, Dict, TYPE_CHECKING, List, Iterable

from ZeitfreiOauth import AsyncDiscordOAuthClient
from aiohttp import ClientResponseError
from disnake import PermissionOverwrite, Member, Role, Guild, User, Embed, utils
from tzlocal import get_localzone

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
    if not guild_settings.allow_nsfw:
        pass

    return {
        "name": channel_settings.channel_name or f"{channel_settings.user} 的語音頻道",
        "overwrites": generate_permission_overwrites(owner, members, channel_settings, guild_settings, locked),
        "bitrate": max_bitrate(guild_settings.guild)
        if channel_settings.bitrate and channel_settings.bitrate >= max_bitrate(guild_settings.guild)
        else channel_settings.bitrate or 64000,
        "user_limit": channel_settings.user_limit or 0,
        "rtc_region": channel_settings.rtc_region or None,
        "nsfw": False if not guild_settings.allow_nsfw else channel_settings.nsfw,
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
                    manage_channels=True,
                    mute_members=True,
                    deafen_members=True,
                    move_members=True
                ),
                guild_settings.base_role: PermissionOverwrite(
                    connect=False,
                    use_soundboard=False if channel_settings.soundboard_enabled is None
                    else channel_settings.soundboard_enabled,  # To make it's False by default
                    attach_files=channel_settings.media_allowed,
                    embed_links=channel_settings.media_allowed,
                    use_external_sounds=True,
                    use_application_commands=True,
                    stream=channel_settings.stream,
                    use_embedded_activities=channel_settings.use_embedded_activities
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
                    manage_channels=True,
                    mute_members=True,
                    deafen_members=True,
                    move_members=True
                ),
                guild_settings.base_role: PermissionOverwrite(
                    connect=True,
                    use_soundboard=False if channel_settings.soundboard_enabled is None
                    else channel_settings.soundboard_enabled,  # To make it's False by default
                    attach_files=channel_settings.media_allowed,
                    embed_links=channel_settings.media_allowed,
                    use_external_sounds=True,
                    use_application_commands=True,
                    stream=channel_settings.stream,
                    use_embedded_activities=channel_settings.use_embedded_activities
                )
            }
        )

        return overwrites


def is_same_day(date1: datetime, date2: datetime) -> bool:
    """
    Check if two dates are on the same day.

    :param date1: The first date.
    :param date2: The second date.
    :return: True if the dates are on the same day, False otherwise.
    """
    return date1.year == date2.year and date1.month == date2.month and date1.day == date2.day


def remove_image(embed: Embed) -> Embed:
    """
    Remove the image from the embed.

    :param embed: The embed to remove image from.
    :return The embed with the image removed.
    """
    embed.set_image(url=None)

    return embed


def snowflake_time(snowflake: int) -> datetime:
    """
    Get the time of a snowflake.

    :param snowflake: The snowflake to get the time of.
    :return: The time of the snowflake.
    """
    return utils.snowflake_time(snowflake).astimezone(get_localzone())


async def is_authorized(oauth_client: AsyncDiscordOAuthClient, user_id: int) -> bool:
    """
    Check if a user is authorized to use the bot.

    :param oauth_client: The OAuth client to use.
    :param user_id: The user ID to check.
    :return: True if the user is authorized, False otherwise.
    """
    try:
        await oauth_client.get_user(user_id)
    except ClientResponseError as error:
        if error.status == 404:
            return False

        raise error

    return True


def split_list(input_list, chunk_size) -> Iterable[list]:
    length = len(input_list)

    num_sublists = length // chunk_size

    for i in range(num_sublists):
        yield input_list[i * chunk_size:(i + 1) * chunk_size]

    if length % chunk_size != 0:
        yield input_list[num_sublists * chunk_size:]
