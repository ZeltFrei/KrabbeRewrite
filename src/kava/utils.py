from typing import Optional

from disnake import Guild

from src.classes.voice_channel import VoiceChannel
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


def get_playing_client_in(server: KavaServer, channel: VoiceChannel) -> Optional[ServerSideClient]:
    """
    Get the playing client in the guild.

    :param server: The server to get the clients from.
    :param channel: The channel to get the playing client in.
    :return: The playing client in the guild. None if no playing client is found.
    """
    for member in channel.channel.members:
        if member.id in server.clients:
            return server.clients[member.id]

    return None
