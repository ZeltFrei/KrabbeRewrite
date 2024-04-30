from typing import Optional, TYPE_CHECKING

import disnake
from disnake import Embed
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.classes.mongo_object import MongoObject
from src.errors import FailedToResolve

if TYPE_CHECKING:
    from src.bot import Krabbe


class ChannelSettings(MongoObject):
    collection_name = "channel_settings"

    def __init__(
            self,
            bot: "Krabbe",
            database: AsyncIOMotorDatabase,
            user_id: int,
            channel_name: Optional[str] = None,
            user_limit: Optional[int] = None,
            bitrate: Optional[int] = None,
            rtc_region: Optional[str] = None,
            nsfw: Optional[bool] = None,
            soundboard_enabled: Optional[bool] = None,
            media_allowed: Optional[bool] = None,
            slowmode_delay: Optional[int] = None
    ):
        super().__init__(bot, database)

        self.user_id: int = user_id

        self._user: Optional[disnake.User] = None

        self.resolved: bool = False

        self.channel_name: Optional[str] = channel_name

        self.user_limit: Optional[int] = user_limit

        self.bitrate: Optional[int] = bitrate
        self.rtc_region: Optional[str] = rtc_region
        self.nsfw: Optional[bool] = nsfw
        self.soundboard_enabled: Optional[bool] = soundboard_enabled
        self.media_allowed: Optional[bool] = media_allowed
        self.slowmode_delay: Optional[int] = slowmode_delay

    def unique_identifier(self) -> dict:
        return {"user_id": self.user_id}

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "channel_name": self.channel_name,
            "user_limit": self.user_limit,
            "bitrate": self.bitrate,
            "rtc_region": self.rtc_region,
            "nsfw": self.nsfw,
            "soundboard_enabled": self.soundboard_enabled,
            "media_allowed": self.media_allowed,
            "slowmode_delay": self.slowmode_delay
        }

    def reset(self):
        """
        Reset the settings to default values.
        This method does not update the database. Use the upsert method to update the database.
        """
        self.channel_name = None
        self.user_limit = None
        self.bitrate = None
        self.rtc_region = None
        self.soundboard_enabled = None
        self.media_allowed = None
        self.slowmode_delay = None

    @property
    def user(self) -> disnake.User:
        """
        Get the user object associated with the channel settings object.

        :raises FailedToResolve: If the user object cannot be resolved.
        :return: The user object.
        """
        if self._user is None:
            self._user = self.bot.get_user(self.user_id)

        elif self._user.id != self.user_id:
            self._user = self.bot.get_user(self.user_id)

        if self._user:
            return self._user

        raise FailedToResolve(f"Failed to resolve user {self.user_id}")

    def is_resolved(self) -> bool:
        """
        Check if the channel settings object is resolved.

        :return: True if the channel settings object is resolved, False otherwise.
        """
        return self.resolved

    def as_embed(self) -> Embed:
        """
        Generate a visual presentation as an embed for this channel settings object.

        :return: The embed object.
        """
        embed = Embed(
            title="⚙️ | 頻道設定",
            color=disnake.Color.blurple(),
            description=f"**用戶**: {self.user.mention}\n"
        )

        embed.add_field(name="✒️ 頻道名稱", value=self.channel_name or "未設定", inline=True)
        embed.add_field(name="🔢 用戶上限", value=self.user_limit or "未設定", inline=True)
        embed.add_field(
            name="📶 比特率", value=f"{self.bitrate // 1000} Kbps" if self.bitrate else "未設定", inline=True
            )
        embed.add_field(name="🌍 RTC 地區", value=self.rtc_region or "未設定", inline=True)
        embed.add_field(name="🔞 NSFW", value=self.nsfw or "未設定", inline=True)
        embed.add_field(name="🔊 音效板", value=self.soundboard_enabled or "未設定", inline=True)
        embed.add_field(name="🎥 媒體允許", value=self.media_allowed or "未設定", inline=True)
        embed.add_field(name="⏳ 慢速模式延遲", value=self.slowmode_delay or "未設定", inline=True)

        return embed

    @classmethod
    async def get_settings(cls, bot: "Krabbe", database: AsyncIOMotorDatabase, user_id: int) -> "ChannelSettings":
        """
        Gets the settings for the specified user. A default ChannelSettings object is created if the user has no settings stored.
        :param bot: The bot instance.
        :param database: The database instance.
        :param user_id: The user ID.
        :return: The ChannelSettings object.
        """
        if settings := await cls.find_one(bot, database, user_id=user_id):
            return settings

        return cls(bot, database, user_id=user_id)
