from disnake import Member

from src.classes.voice_channel import VoiceChannel


class FailedToResolve(Exception):
    """
    Raised when the resolver failed to resolve the object.
    """
    pass


class OwnedChannel(Exception):
    def __init__(self, member: Member, channel: VoiceChannel):
        self.member: Member = member
        self.channel: VoiceChannel = channel
