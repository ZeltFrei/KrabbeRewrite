from typing import Optional, TYPE_CHECKING

import disnake
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.classes.mongo_object import MongoObject

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
            channel_activity: Optional[str] = None,
            password: Optional[str] = None,
            user_limit: Optional[int] = None,
            bitrate: Optional[int] = None,
            rtc_region: Optional[str] = None,
            nsfw: Optional[bool] = None,
            soundboard_enabled: Optional[bool] = None,
            text_channel_enabled: Optional[bool] = None,
            media_allowed: Optional[bool] = None,
            slowmode_delay: Optional[int] = None
    ):
        super().__init__(bot, database)

        self.user_id: int = user_id

        self._user: Optional[disnake.User] = None

        self.channel_name: Optional[str] = channel_name
        self.channel_activity: Optional[str] = channel_activity

        self.password: Optional[str] = password
        self.user_limit: Optional[int] = user_limit

        self.bitrate: Optional[int] = bitrate
        self.rtc_region: Optional[str] = rtc_region
        self.nsfw: Optional[bool] = nsfw
        self.soundboard_enabled: Optional[bool] = soundboard_enabled
        self.text_channel_enabled: Optional[bool] = text_channel_enabled
        self.media_allowed: Optional[bool] = media_allowed
        self.slowmode_delay: Optional[int] = slowmode_delay

    def unique_identifier(self) -> dict:
        return {"user_id": self.user_id}

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "channel_name": self.channel_name,
            "channel_activity": self.channel_activity,
            "password": self.password,
            "user_limit": self.user_limit,
            "bitrate": self.bitrate,
            "rtc_region": self.rtc_region,
            "nsfw": self.nsfw,
            "soundboard_enabled": self.soundboard_enabled,
            "text_channel_enabled": self.text_channel_enabled,
            "media_allowed": self.media_allowed,
            "slowmode_delay": self.slowmode_delay
        }

    def reset(self):
        """
        Reset the settings to default values.
        This method does not update the database. Use the upsert method to update the database.
        """
        self.channel_name = None
        self.channel_activity = None
        self.password = None
        self.user_limit = None
        self.bitrate = None
        self.rtc_region = None
        self.soundboard_enabled = None
        self.text_channel_enabled = None
        self.media_allowed = None
        self.slowmode_delay = None

    @property
    def user(self) -> disnake.User:
        if self._user is None:
            raise ValueError("User is not resolved yet. Consider calling the resolve method.")
        return self._user

    async def resolve(self) -> "ChannelSettings":
        """
        Resolves the user object.

        :return: The resolved ChannelSettings object.
        """
        self._user = await self.bot.getch_user(self.user_id)

        return self

    @classmethod
    async def get_settings(cls, bot: "Krabbe", database: AsyncIOMotorDatabase, user_id: int) -> "ChannelSettings":
        """
        Gets the settings for the specified user. A default ChannelSettings object is created if the user has no settings stored.
        Note that this method will automatically resolve the settings object.
        :param bot: The bot instance.
        :param database: The database instance.
        :param user_id: The user ID.
        :return: The ChannelSettings object.
        """
        if settings := await cls.find_one(bot, database, user_id=user_id):
            await settings.resolve()
            return settings

        settings = cls(bot, database, user_id=user_id)

        await settings.resolve()
        return cls(bot, database, user_id=user_id)
