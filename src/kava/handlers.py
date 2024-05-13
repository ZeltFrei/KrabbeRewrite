from src.classes.voice_channel import VoiceChannel
from src.kava.server import KavaServer, Request
from src.kava.utils import has_music_permissions


async def can_use_music(request: "Request", user_id: int, channel_id: int):
    channel = VoiceChannel.active_channels.get(channel_id)

    if not channel:
        await request.respond(
            {
                "status": "error",
                "message": "Not a valid channel!"
            }
        )
        return

    if not has_music_permissions(user_id, channel):
        await request.respond(
            {
                "status": "error",
                "message": "You do not have permission to use music commands in this channel!"
            }
        )
        return

    await request.respond(
        {
            "status": "success"
        }
    )


def add_handlers(client: "KavaServer"):
    """
    Convenience function to add handlers from this file to the KavaServer.
    """
    client.add_handler("can_use_music", can_use_music)
