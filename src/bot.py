import json
import logging

from colorlog import ColoredFormatter
from disnake import Intents, Event
from disnake.ext.commands import InteractionBot, CommandSyncFlags

from src.panels import register_views


def setup_logging() -> logging.Logger:
    """
    Set up the logging for the bot
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
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(filename="lava.log", encoding="utf-8", mode="w")
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

        self.logger = setup_logging()
        self.__load_extensions()

        self.add_listener(self.__on_ready, Event.ready)

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

    async def __on_ready(self):
        """
        Method executed when the bot is ready to start receiving events.

        :return: None
        """
        self.logger.info(f"Logged in as {self.user.name} ({self.user.id})")

        register_views(self)

        self.remove_listener(self.__on_ready, Event.ready)
