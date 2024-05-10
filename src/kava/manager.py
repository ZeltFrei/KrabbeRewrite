from logging import getLogger
from typing import List, TYPE_CHECKING, Optional

from websockets import serve, WebSocketServer, WebSocketServerProtocol

from src.kava.kava import Kava

if TYPE_CHECKING:
    from src.bot import Krabbe


class KavaManager:
    """
    Manage the connection of Kava clients.
    """
    logger = getLogger("krabbe.kava_manager")

    def __init__(self, bot: "Krabbe"):
        """
        Initialize the KavaManager instance.
        """
        self.bot: "Krabbe" = bot

        self.clients: List[Kava] = []
        self.active_clients: List[Kava] = []

        self.websocket_server: Optional[WebSocketServer] = None

    async def _process_new_connection(self, websocket: WebSocketServerProtocol):
        """
        Handle a new connection.
        :param websocket: The websocket connection.
        """
        self.logger.info("New connection from %s", websocket.remote_address)

        client = Kava(self, websocket)

        self.clients.append(client)

        await client.message_handler()

    async def start_serving(self, host: str, port: int):
        """
        Serve the Kava clients.
        :param host: The host to serve the clients.
        :param port: The port to serve the clients.
        """
        self.logger.info("Starting Kava server on %s:%d", host, port)

        self.websocket_server = await serve(self._process_new_connection, host, port)

    def close(self):
        """
        Close the Kava server.
        """
        self.logger.info("Closing Kava server")

        for client in self.clients:
            client.close()

        self.active_clients.clear()
        self.clients.clear()

        if self.websocket_server:
            self.websocket_server.close()
            self.websocket_server = None
