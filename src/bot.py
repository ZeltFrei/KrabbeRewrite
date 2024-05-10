import json
import logging
from os import getenv
from typing import Optional

from ZeitfreiOauth import AsyncDiscordOAuthClient
from aiohttp import ClientSession
from colorlog import ColoredFormatter
from disnake import Intents, Event, VoiceState, Member, Webhook
from disnake.ext.commands import InteractionBot, CommandSyncFlags
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi

from src.classes.voice_channel import VoiceChannel
from src.errors import FailedToResolve
from src.kava.manager import KavaManager
from src.panels import setup_views


def setup_logging(debug: bool) -> logging.Logger:
    """
    Set up the logging for the bot

    :param debug: Whether to enable debug logging
    :return: The default logger for Krabbe
    """
    formatter = ColoredFormatter(
        '%(asctime)s %(log_color)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'white',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(filename="krabbe.log", encoding="utf-8", mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        handlers=[stream_handler, file_handler], level=logging.INFO
    )

    return logging.getLogger("krabbe.main")


class Krabbe(InteractionBot):
    def __init__(self):
        super().__init__(
            intents=Intents.all(),
            command_sync_flags=CommandSyncFlags.all()
        )

        self.debug: bool = bool(getenv("DEBUG"))

        self.database: AsyncIOMotorDatabase = AsyncIOMotorClient(
            getenv("MONGODB_URL"), server_api=ServerApi('1')
        ).get_database("krabbe")

        self.logger = setup_logging(self.debug)
        self.__load_extensions()

        self.webhooks_client_session: ClientSession = ClientSession()

        self.add_listener(self.__on_ready, Event.ready)
        self.add_listener(self.__on_voice_state_update, Event.voice_state_update)

        self.feedback_webhook: Optional[Webhook] = Webhook.from_url(
            getenv("FEEDBACK_WEBHOOK_URL"), session=self.webhooks_client_session
        )

        self.oauth = AsyncDiscordOAuthClient(
            getenv("OAUTH_API_KEY"), getenv("OAUTH_API_BASE_URL", "https://oauth.zeitfrei.tw/")
        )

        self.kava_manager = KavaManager(self)

    def __load_extensions(self) -> None:
        """
        Load all extensions from extensions.json

        :return: Boolean if function was successful
        """
        with open("extensions.json", "r", encoding="utf-8") as f:
            extensions = json.load(f)

        for extension in extensions:
            self.logger.info(f"Loading extension {extension}")
            self.load_extension(extension)
            self.logger.info(f"Loaded extension {extension}")

    async def __load_channels(self) -> None:
        """
        Load all voice channels from the database.

        :return: None
        """
        async for voice_channel in VoiceChannel.find(self, self.database):
            try:
                self.logger.info(f"Resolving voice channel {voice_channel.channel} with owner {voice_channel.owner}")
            except FailedToResolve:
                self.logger.warning(f"Failed to resolve voice channel {voice_channel.channel_id}, removing.")
                await voice_channel.remove()
                continue

            VoiceChannel.active_channels[voice_channel.channel_id] = voice_channel
            voice_channel.start_listeners()

            await voice_channel.restore_state()

    async def __on_ready(self) -> None:
        """
        Method executed when the bot is ready to start receiving events.

        :return: None
        """
        self.remove_listener(self.__on_ready, Event.ready)  # To prevent this from being called again

        self.logger.info(f"Logged in as {self.user.name} ({self.user.id})")

        setup_views(self)

        await self.__load_channels()

        await self.kava_manager.start_serving(getenv("KAVA_HOST", "0.0.0.0"), int(getenv("KAVA_PORT", "8090")))

    async def __on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        """
        Method executed when a voice state update event is received.

        :param member: The member whose voice state was updated.
        :param before: The voice state before the update.
        :param after: The voice state after the update.
        :return: None
        """
        if before.channel == after.channel:
            return

        if after.channel is not None:
            self.logger.info(f"{member.display_name} joined voice channel {after.channel.name}")

            self.dispatch("voice_channel_join", member, after)

        if before.channel is not None:
            self.logger.info(f"{member.display_name} left voice channel {before.channel.name}")

            self.dispatch("voice_channel_leave", member, before)
