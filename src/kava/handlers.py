from src.classes.voice_channel import VoiceChannel
from src.kava.server import KavaServer, Request
from src.kava.utils import has_music_permissions


async def can_use_music(request: "Request", user_id: int, channel_id: int):
    channel = VoiceChannel.active_channels.get(channel_id)

    if not channel:
        await request.respond(
            {
                "status": "error",
                "message": "這不是一個有效的動態語音頻道！"
            }
        )
        return

    if not has_music_permissions(user_id, channel):
        await request.respond(
            {
                "status": "error",
                "message": "您沒有權限在這個頻道播放音樂！"
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
