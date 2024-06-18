from disnake import Member

from src.classes.voice_channel import VoiceChannel


class FailedToResolve(Exception):
    """
    Raised when the resolver failed to resolve the object.
    """
    pass


class OwnedChannel(Exception):
    """
    Raised when the new owner already owns a channel.
    """

    def __init__(self, member: Member, channel: VoiceChannel):
        self.member: Member = member
        self.channel: VoiceChannel = channel


class AlternativeOwnerNotFound(Exception):
    """
    Raised when the to find an alternative owner for the channel.
    """
    pass
