from typing import Optional

from disnake import Embed, Color


class ErrorEmbed(Embed):
    """
    The embed used when errors
    """

    def __init__(self, title: str, description: Optional[str] = None,
                 author_name: str = None, author_icon_url: str = None, *args, **kwargs):
        super().__init__(title=f"❌ | {title}", description=description, color=Color.red(), *args, **kwargs)

        if author_name and author_icon_url:
            self.set_author(name=author_name, icon_url=author_icon_url)


class WarningEmbed(Embed):
    """
    The embed used when bot needs to warn something
    """

    def __init__(self, title: str, description: Optional[str] = None,
                 author_name: str = None, author_icon_url: str = None, *args, **kwargs):
        super().__init__(title=f"⚠️ | {title}", description=description, color=Color.yellow(), *args, **kwargs)

        if author_name and author_icon_url:
            self.set_author(name=author_name, icon_url=author_icon_url)


class LoadingEmbed(Embed):
    """
    The embed used when bot is loading something
    """

    def __init__(self, title: str, description: Optional[str] = None,
                 author_name: str = None, author_icon_url: str = None, *args, **kwargs):
        super().__init__(title=f"⏳ | {title}", description=description, color=Color.blue(), *args, **kwargs)

        if author_name and author_icon_url:
            self.set_author(name=author_name, icon_url=author_icon_url)


class SuccessEmbed(Embed):
    """
    The embed used when successful
    """

    def __init__(self, title: str, description: Optional[str] = None,
                 author_name: str = None, author_icon_url: str = None, *args, **kwargs):
        super().__init__(title=f"✅ | {title}", description=description, color=Color.green(), *args, **kwargs)

        if author_name and author_icon_url:
            self.set_author(name=author_name, icon_url=author_icon_url)


class InfoEmbed(Embed):
    """
    The embed used when bot needs to inform something
    """

    def __init__(self, title: str, description: Optional[str] = None,
                 author_name: str = None, author_icon_url: str = None, *args, **kwargs):
        super().__init__(title=f"ℹ️ | {title}", description=description, color=Color.blurple(), *args, **kwargs)

        if author_name and author_icon_url:
            self.set_author(name=author_name, icon_url=author_icon_url)


class ChannelNotificationEmbed(Embed):
    def __init__(self, left_message: str, right_message: str, image_url: Optional[str] = None, *args, **kwargs):
        super().__init__(color=Color.blurple(), *args, **kwargs)

        self.add_field(name="📢 Krabbe+ 2", value=left_message, inline=True)
        self.add_field(name="📢 系統通知", value=right_message, inline=True)

        if image_url:
            self.set_image(url=image_url)


class VoiceSetupEmbed(Embed):
    def __init__(self, status: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None,
                 *args, **kwargs):
        super().__init__(color=Color.blurple(), title=title, description=description, *args, **kwargs)

        self.set_author(name="安裝導引" + (f"〡{status}" if status else ""), icon_url="https://i.imgur.com/lsTtd9c.png")
