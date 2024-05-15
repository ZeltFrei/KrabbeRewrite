from typing import Optional

from disnake import Guild, Interaction

from src.classes.voice_channel import VoiceChannel
from src.embeds import ErrorEmbed
from src.kava.server import KavaServer, ServerSideClient


def get_clients_in(server: KavaServer, guild: Guild) -> list[ServerSideClient]:
    """
    Get the list of connected clients in the guild.

    :param server: The server to get the clients from.
    :param guild: The guild to get the clients in.
    :return: The list of clients in the guild.
    """
    return [
        server.clients[member.id] for member in guild.members
        if member.id in server.clients
    ]


def get_idle_clients_in(server: KavaServer, guild: Guild) -> list[ServerSideClient]:
    """
    Get the list of connected idle clients in the guild.

    :param server: The server to get the clients from.
    :param guild: The guild to get the clients in.
    :return: The list of idle clients in the guild.
    """
    return [
        server.clients[member.id] for member in guild.members
        if member.id in server.clients and member.voice is None
    ]


def get_active_client_in(server: KavaServer, channel: VoiceChannel) -> Optional[ServerSideClient]:
    """
    Get the active client in the channel.

    :param server: The server to get the clients from.
    :param channel: The channel to get the playing client in.
    :return: The playing client in the guild. None if no playing client is found.
    """
    for member in channel.channel.members:
        if member.id in server.clients:
            return server.clients[member.id]

    return None


def has_music_permissions(user_id: int, channel: VoiceChannel) -> bool:
    """
    Check if the user has music permissions in the channel.

    :param user_id: The user ID to check.
    :param channel: The channel to check.
    :return: True if the user has music permissions. False otherwise.
    """
    if not channel.channel_settings.shared_music_control:
        return user_id == channel.channel_settings.user_id

    return True


async def ensure_music_permissions(interaction: Interaction) -> Optional[VoiceChannel]:
    """
    This check ensures that the user is allowed to use the music commands.
    :param interaction: The interaction that triggered the command.
    :return: The active channel in the interaction.
    """
    channel = VoiceChannel.get_active_channel_from_interaction(interaction)

    if not has_music_permissions(interaction.author.id, channel):
        await interaction.response.send_message(
            embed=ErrorEmbed("此語音頻道擁有者不允許其他成員使用音樂功能"),
            ephemeral=True
        )
        return None

    return channel


async def ensure_music_client(server: KavaServer, interaction: Interaction) -> Optional[ServerSideClient]:
    """
    This check ensures that there's a active client in the channel.
    :param server: The server to get the clients from.
    :param interaction: The interaction that triggered the command.
    :return: The active client in the channel. None if no active client is found.
    """
    if not interaction.guild:
        await interaction.response.send_message(
            embed=ErrorEmbed("這個指令只能在伺服器中使用。"),
            ephemeral=True
        )
        return

    channel = VoiceChannel.get_active_channel_from_interaction(interaction)

    if not channel:
        await interaction.response.send_message(
            embed=ErrorEmbed("請先加入一個語音頻道。"),
            ephemeral=True
        )
        return

    client = get_active_client_in(server, channel)

    if client is None:
        await interaction.response.send_message(
            embed=ErrorEmbed("沒有正在你頻道裡的音樂機器人！"),
            ephemeral=True
        )
        return

    return client
