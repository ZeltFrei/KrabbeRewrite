from typing import Optional, TYPE_CHECKING

import disnake
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.mongo_objects import MongoObject

if TYPE_CHECKING:
    from src.bot import Krabbe


class ChannelSettings(MongoObject):
    collection_name = "channel_settings"

    def __init__(self, bot: "Krabbe", database: AsyncIOMotorDatabase, user_id: int):
        super().__init__(bot, database)

        self.user_id: int = user_id

        self._user: Optional[disnake.User] = None

    def unique_identifier(self) -> dict:
        return {"user_id": self.user_id}

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id
        }

    @property
    def user(self):
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
