import asyncio
from os import getenv

from dotenv import load_dotenv

from src.bot import Krabbe


def main() -> None:
    """
    The main entry point
    :return:
    """
    load_dotenv()

    bot = Krabbe()

    bot.run(getenv("BOT_TOKEN"))


if __name__ == "__main__":
    main()
