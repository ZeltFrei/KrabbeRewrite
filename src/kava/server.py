import asyncio
import json
import uuid
from typing import Dict, List, Callable, Coroutine, Any, TYPE_CHECKING, Optional

import websockets
from websockets import WebSocketServerProtocol, WebSocketServer

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
    def __init__(self, websocket: WebSocketServerProtocol):
        self.websocket = websocket
        self.pending_responses: Dict[str, asyncio.Future] = {}

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

    async def handle_response(self, message: Dict[str, Any]) -> None:
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
    def __init__(self, bot: "Krabbe", host: str = "localhost", port: int = 8765):
        self.bot = bot
        self.host = host
        self.port = port
        self.server: Optional[WebSocketServer] = None
        self.handlers: Dict[str, List[Callable[[Request, Any], Coroutine[Any, Any, None]]]] = {}
        self.clients: List[ServerSideClient] = []

    async def _handle_request(self, client: ServerSideClient, request: Dict[str, Any]) -> None:
        """
        Handles a request from a client. Should be called when a request is received.
        :param client: The client that sent the request.
        :param request: The request data.
        :return: None
        """
        endpoint = request["endpoint"]
        request_id = request["id"]
        data = request["data"]

        request_obj = Request(client, request_id, data)

        if endpoint in self.handlers:
            for handler in self.handlers[endpoint]:
                _ = self.bot.loop.create_task(handler(request_obj, **data))
        else:
            await request_obj.respond({"status": "error", "message": "No handler for endpoint"})

    async def _handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """
        Handles a new connection from a client.
        :param websocket: The websocket connection.
        :return: None
        """
        client = ServerSideClient(websocket)
        self.clients.append(client)

        try:
            async for message in websocket:
                data = json.loads(message)

                if data['type'] == "request":
                    _ = self.bot.loop.create_task(self._handle_request(client, data))
                elif data['type'] == "response":
                    await client.handle_response(data)
        finally:
            self.clients.remove(client)

    def add_handler(self, endpoint: str, handler: Callable[[Request, Any], Coroutine[Any, Any, None]]) -> None:
        """
        Add a handler for a specific endpoint.
        :param endpoint: The endpoint to add the handler for.
        :param handler: The handler to add.
        :return: None
        """
        if endpoint not in self.handlers:
            self.handlers[endpoint] = []

        self.handlers[endpoint].append(handler)

    async def start(self) -> None:
        self.server = await websockets.serve(self._handle_connection, self.host, self.port)

    def stop(self) -> None:
        if self.server is not None:
            self.server.close()
            self.bot.loop.run_until_complete(self.server.wait_closed())
            self.server = None
