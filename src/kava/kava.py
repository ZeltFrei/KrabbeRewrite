import json
from typing import TYPE_CHECKING

from websockets import WebSocketServerProtocol, ConnectionClosed, Data

if TYPE_CHECKING:
    from src.kava.manager import KavaManager


class Kava:
    """
    Present a instance of connected Kava client.
    """

    def __init__(self, manager: "KavaManager", websocket: WebSocketServerProtocol):
        """
        Initialize the Kava instance.
        :param manager: The manager that accepted the connection.
        """
        self.manager: "KavaManager" = manager
        self.websocket: WebSocketServerProtocol = websocket

    async def on_websocket_message(self, message: Data):
        data = json.load(message)

        match data["type"]:
            # TODO: Implement the rest of the message types
            case _:
                self.manager.logger.warning("Unknown message type %s", data["type"])

    async def message_handler(self):
        try:
            async for message in self.websocket:
                _ = self.manager.bot.loop.create_task(self.on_websocket_message(message))
        except ConnectionClosed:
            self.close()
        finally:
            pass

    def close(self):
        self.websocket.close()
        self.manager.clients.remove(self)
        self.manager.active_clients.remove(self)
