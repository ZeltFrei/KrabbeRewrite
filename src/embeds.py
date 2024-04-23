from typing import Optional

from disnake import Embed, Color


class ErrorEmbed(Embed):
    """
    The embed used when errors
    """

    def __init__(self, title: str, description: Optional[str] = None):
        super().__init__(title=f"❌ | {title}", description=description, color=Color.red())


class WarningEmbed(Embed):
    """
    The embed used when bot needs to warn something
    """

    def __init__(self, title: str, description: Optional[str] = None):
        super().__init__(title=f"⚠️ | {title}", description=description, color=Color.yellow())


class LoadingEmbed(Embed):
    """
    The embed used when bot is loading something
    """

    def __init__(self, title: str, description: Optional[str] = None):
        super().__init__(title=f"⏳ | {title}", description=description, color=Color.blue())


class SuccessEmbed(Embed):
    """
    The embed used when successful
    """

    def __init__(self, title: str, description: Optional[str] = None):
        super().__init__(title=f"✅ | {title}", description=description, color=Color.green())


class InfoEmbed(Embed):
    """
    The embed used when bot needs to inform something
    """

    def __init__(self, title: str, description: Optional[str] = None):
        super().__init__(title=f"ℹ️ | {title}", description=description, color=Color.blurple())
