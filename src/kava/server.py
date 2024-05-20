import asyncio
import json
import uuid
from logging import getLogger
from typing import Dict, List, Callable, Coroutine, Any, TYPE_CHECKING, Optional

import websockets
from websockets import WebSocketServerProtocol, WebSocketServer, ConnectionClosedError

if TYPE_CHECKING:
    from src.bot import Krabbe


class Request:
    def __init__(self, client: 'ServerSideClient', request_id: str, data: Dict[str, Any]):
        self.client = client
        self.id = request_id
        self.data = data

    async def respond(self, response_data: Dict[str, Any]) -> None:
        """
        Respond to the request.
        :param response_data: The data to respond with.
        :return: None
        """
        response = {
            "type": "response",
            "id": self.id,
            "data": response_data
        }

        await self.client.send(response)


class ServerSideClient:
    def __init__(self, websocket: WebSocketServerProtocol, bot_user_id: int, bot_user_name: str):
        self.pending_responses: Dict[str, asyncio.Future] = {}

        self.websocket: WebSocketServerProtocol = websocket

        self.bot_user_id: int = bot_user_id
        self.bot_user_name: str = bot_user_name

    @property
    def invite_link(self) -> str:
        return f"https://discord.com/oauth2/authorize?client_id={self.bot_user_id}&permissions=274881333248&scope=bot"

    async def request(self, endpoint: str, **kwargs: Any) -> Any:
        """
        Send a request to the client.
        :param endpoint: The endpoint to send the request to.
        :param kwargs: The data to send with the request.
        :return: The response from the client.
        """
        request_id = str(uuid.uuid4())

        future = asyncio.Future()
        self.pending_responses[request_id] = future

        message = {
            "type": "request",
            "id": request_id,
            "endpoint": endpoint,
            "data": kwargs
        }

        await self.websocket.send(json.dumps(message))

        return await future

    async def _handle_response(self, message: Dict[str, Any]) -> None:
        """
        Handle a response from the client.
        Calls the future associated with the request ID to stop request blocking.
        :param message: The message to handle.
        :return: None
        """
        request_id = message['id']

        if request_id in self.pending_responses:
            self.pending_responses[request_id].set_result(message['data'])
            del self.pending_responses[request_id]

    async def send(self, data: Dict[str, Any]) -> None:
        await self.websocket.send(json.dumps(data))


class KavaServer:
    logger = getLogger("kava.server")

    def __init__(self, bot: "Krabbe", host: str = "localhost", port: int = 8765):
        self.bot = bot
        self.host = host
        self.port = port
        self.server: Optional[WebSocketServer] = None
        self.handlers: Dict[str, List[Callable[..., Coroutine[Any, Any, None]]]] = {}
        self.clients: Dict[int, ServerSideClient] = {}

    async def _handle_request(self, client: ServerSideClient, request: Dict[str, Any]) -> None:
        """
        Handles a request from a client. Should be called when a request is received.
        :param client: The client that sent the request.
        :param request: The request data.
        :return: None
        """
        self.logger.debug(f"Handling request {request}")

        endpoint = request["endpoint"]
        request_id = request["id"]
        data = request["data"]

        request_obj = Request(client, request_id, data)

        if endpoint in self.handlers:
            for handler in self.handlers[endpoint]:
                _ = self.bot.loop.create_task(handler(request_obj, **data))
        else:
            await request_obj.respond({"status": "error", "message": "No handler for endpoint"})

    async def _handle_messages(self, client: ServerSideClient) -> None:
        """
        Handles messages from a websocket connection.
        :param client: The client to handle messages for.
        :return: None
        """
        self.logger.info(f"Start handling messages from {client.websocket.remote_address}")

        try:
            async for message in client.websocket:
                data = json.loads(message)

                if data['type'] == "request":
                    _ = self.bot.loop.create_task(self._handle_request(client, data))
                elif data['type'] == "response":
                    await client._handle_response(data)
        except ConnectionClosedError:
            self.logger.info(f"Connection from {client.websocket.remote_address} closed.")
        finally:
            self.clients.pop(client.bot_user_id)

    async def _handle_new_connection(self, websocket: WebSocketServerProtocol):
        """
        Handle a new connection.
        :param websocket: The websocket connection.
        :return None
        """
        self.logger.info(f"New connection from {websocket.remote_address}")

        await websocket.send(
            json.dumps({"type": "request", "id": "initial", "endpoint": "get_client_info", "data": {}})
        )

        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)  # timeout as needed
            client_info = json.loads(response)

            if client_info['type'] == 'response' and client_info['id'] == 'initial':
                client = ServerSideClient(websocket, **client_info['data'])
                self.clients[client_info['data']['bot_user_id']] = client

                await self._handle_messages(client)
        except asyncio.TimeoutError:
            self.logger.warning(f"Client {websocket.remote_address} did not respond in time.")
            await websocket.close()
        except TypeError:
            self.logger.warning(f"Client {websocket.remote_address} did not send the correct data.")
            await websocket.close()

    def add_handler(self, endpoint: str, handler: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """
        Add a handler for a specific endpoint.
        :param endpoint: The endpoint to add the handler for.
        :param handler: The handler to add.
        :return: None
        """
        self.logger.debug(f"Adding handler for endpoint {endpoint}")

        if endpoint not in self.handlers:
            self.handlers[endpoint] = []

        self.handlers[endpoint].append(handler)

    async def start(self) -> None:
        self.logger.info(f"Starting Kava server on {self.host}:{self.port}")

        self.server = await websockets.serve(self._handle_new_connection, self.host, self.port)

    def stop(self) -> None:
        self.logger.info("Stopping Kava server")

        if self.server is not None:
            self.server.close()
            self.bot.loop.run_until_complete(self.server.wait_closed())
            self.server = None
