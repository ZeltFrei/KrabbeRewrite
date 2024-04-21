import logging

from colorlog import ColoredFormatter
from disnake import Intents
from disnake.ext.commands import InteractionBot


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
        super().__init__(intents=Intents.all())

        self.logger = setup_logging()
        self.__load_extensions()

    def __load_extensions(self) -> None:
        """
        Load all extensions from extensions.json
        :return: Boolean if function was successful
        """
        with open("configs/icons.json", "r", encoding="utf-8") as f:
            extensions = f.read()

        for extension in extensions:
            self.logger.info(f"Loading extension {extension}")
            self.load_extension(extension)
            self.logger.info(f"Loaded extension {extension}")
