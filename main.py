from os import getenv

from src.bot import Krabbe


def main() -> None:
    """
    The main entry point
    :return:
    """

    bot = Krabbe()

    bot.run(getenv("BOT_TOKEN"))


if __name__ == "__main__":
    main()
