from typing import Optional

import disnake
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.bot import Krabbe
from src.classes.mongo_object import MongoObject


class ChannelSettings(MongoObject):
    collection_name = "channel_settings"

    def __init__(self, bot: Krabbe, database: AsyncIOMotorDatabase, user_id: int):
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

    async def resolve(self, bot: Krabbe):
        """
        Resolves the user object.

        :param bot: The Krabbe bot instance.
        """
        self._user = await bot.getch_user(self.user_id)

        return self
