import asyncio
import json
import logging.config
import os
from typing import Optional, Any

import aioredis
from aio_pika.abc import AbstractIncomingMessage
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocket
from pydantic import parse_obj_as
from starlette.endpoints import WebSocketEndpoint
from starlette.types import ASGIApp, Receive, Scope, Send

from project.celery_utils import create_celery
from project.config import settings
from project.core import WebSocketManager, PikaClient
from project.schemas import User as UserSchema, Payload as PayloadSchema, UserValidation

redis = aioredis.from_url(os.environ.get('result_backend', "redis://127.0.0.1:6379/15"))
# setup loggers
logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
from project import tasks

# get root logger
logger = logging.getLogger(__name__)  # __name__ = "project"
loop = asyncio.get_event_loop()


def create_app() -> FastAPI:
	app = FastAPI(title="Helpdesk Notification Service",
	              version="1.0.0",
	              description="Helpdesk Notification Service",
	              contact={
		              "name": "Reza Yogaswara",
		              "url": "https://me.rezayogaswara.dev/",
		              "email": "reza.yoga@gmail.com",
	              }, )

	class RoomEventMiddleware:  # pylint: disable=too-few-public-methods
		"""Middleware for providing a global :class:`~.WebSocketManager` instance to both HTTP
		and WebSocket scopes.

		Although it might seem odd to load the broadcast interface like this (as
		opposed to, e.g. providing a global) this both mimics the pattern
		established by starlette's existing DatabaseMiddlware, and describes a
		pattern for installing an arbitrary broadcast backend (Redis PUB-SUB,
		Postgres LISTEN/NOTIFY, etc) and providing it at the level of an individual
		request.
		"""

		def __init__(self, app: ASGIApp):
			self._app = app
			self._room = WebSocketManager()

		async def __call__(self, scope: Scope, receive: Receive, send: Send):
			if scope["type"] in ("lifespan", "http", "websocket"):
				scope["room"] = self._room
			await self._app(scope, receive, send)

	app.add_middleware(RoomEventMiddleware)

	app.celery_app = create_celery()

	html_broadcast = """
	<!DOCTYPE html>
	<html>
	    <head>
	        <title>Clients</title>
	    </head>
	    <body onload="add_user(event)">
	        <h1 id="h1-title">Clients</h1>
	        <select user_id="select_token" style="width:30%" onchange="add_user(this)">
	          <option selected="selected" value="-">Select Token</option>
			  <option value="user1.0cc175b9c0f1b6a831c399e269772661">Token #1 (Valid)</option>
			  <option value="user2.92eb5ffee6ae2fec3ad71c777531578f">Token #2 (Valid)</option>
			  <option value="user3.4a8a08f09d37b73795649038408b5f33">Token #3 (Valid)</option>
			  <option value="user4.e1671797c52e15f763380b45e841ec32">Token #4 (Invalid)</option>
			  <option value="user5.8fa14cdd754f91cc6554c9e71929cce7">Token #5 (Invalid)</option>
			</select>
	        <hr />
	        <div id="token"></div>
	        <div id="message"></div>
	        <script>
	            var ws = null;
	            var token = null;
	            function add_user(select_object) {
	                var token = select_object.value;
	                if (token !== undefined) {		                
	                	// notifier.rezayogaswara.dev
		                const ws_url = '/ws';
					    const ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://localhost:8005' + ws_url);
		                ws.onmessage = function(event) {
		                    console.log(event.data);
		                    document.getElementById('message').innerHTML = document.getElementById('message').innerHTML 
		                    + "<hr />" + event.data;
		                };
	                    document.getElementById('token').innerHTML = token;
	                }
	            }
	        </script>
	    </body>
	</html>
	"""

	def log_incoming_message(message: dict):
		logger.info(f"Received message: {message}")

	pika_client = PikaClient(log_incoming_message)

	@app.get("/")
	async def get():
		return HTMLResponse(html_broadcast)

	@classmethod
	@app.websocket_route("/ws", name="ws")
	class WebSocketApp(WebSocketEndpoint):
		"""Live connection to the global :class:`~.Room` instance, via WebSocket.
		    """

		encoding: str = "text"
		session_name: str = ""
		count: int = 0

		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.room: Optional[WebSocketManager] = None
			self.user_id: Optional[str] = None

		@classmethod
		def get_next_user_id(cls):
			"""Returns monotonically increasing numbered usernames in the form
				'user_[number]'
			"""
			user_id: str = f"user_{cls.count}"
			cls.count += 1
			return user_id

		async def on_connect(self, websocket):
			"""Handle a new connection.

			New users are assigned a user ID and notified of the room's connected
			users. The other connected users are notified of the new user's arrival,
			and finally the new user is added to the global :class:`~.Room` instance.
			"""
			logger.info("Connecting new user...")
			room: Optional[WebSocketManager] = self.scope.get("room")
			if room is None:
				raise RuntimeError(f"Global `Room` instance unavailable!")
			self.room = room
			self.user_id = self.get_next_user_id()
			await websocket.accept()
			await websocket.send_json(
				{"type": "ROOM_JOIN", "data": {"user_id": self.user_id}}
			)
			await self.room.broadcast_user_joined(self.user_id)
			self.room.add_user(self.user_id, websocket)

		async def on_disconnect(self, _websocket: WebSocket, _close_code: int):
			"""Disconnect the user, removing them from the :class:`~.Room`, and
			notifying the other users of their departure.
			"""
			if self.user_id is None:
				raise RuntimeError(
					"RoomLive.on_disconnect() called without a valid user_id"
				)
			self.room.remove_user(self.user_id)
			await self.room.broadcast_user_left(self.user_id)

		async def on_receive(self, _websocket: WebSocket, msg: Any):
			"""Handle incoming message: `msg` is forwarded straight to `broadcast_message`.
			"""
			if self.user_id is None:
				raise RuntimeError("RoomLive.on_receive() called without a valid user_id")
			if not isinstance(msg, str):
				raise ValueError(f"RoomLive.on_receive() passed unhandleable data: {msg}")
			await self.room.broadcast_message(self.user_id, msg)

	async def validate_auth_token(auth_token: str) -> UserValidation:
		logger.info(f"Validating token: {auth_token}")
		user = await redis.get(auth_token)

		if user is not None:
			u = parse_obj_as(UserSchema, json.loads(user))
			return UserValidation(is_validated=True, user_id=u.id)
		return UserValidation(is_validated=False, user_id=None)

	@app.post('/publish-payload-to-rmq')
	async def publish_payload_to_rmq(request: Request, payload: PayloadSchema):
		await pika_client.init_connection()
		await request.app.pika_client.publish_async(
			jsonable_encoder(payload),
		)

		return {"status": "published"}

	@app.get('/consume-payload-from-rmq')
	async def consume_payload_from_rmq(request: Request):
		connection = await request.app.pika_client.consume(loop)
		channel = await connection.channel()
		queue = await channel.declare_queue(settings.RABBITMQ_SERVICE_QUEUE_NAME, durable=True)
		await queue.consume(on_message, no_ack=False)
		return {"status": "consuming"}

	async def on_message(message: AbstractIncomingMessage) -> None:
		# async with message.process():
		# 	key_list = list(websocket_manager.active_connections.keys())
		# 	payload = parse_obj_as(PayloadSchema, json.loads(message.body))
		#
		# 	if payload.broadcast:
		# 		await websocket_manager.broadcast(jsonable_encoder(payload))
		# 	else:
		# 		r = sorted(payload.recipients)
		# 		active_user_in_websocket = sorted(key_list)
		# 		intersection = set(r).intersection(set(active_user_in_websocket))
		# 		if len(intersection) > 0:
		# 			for user_id in intersection:
		# 				await websocket_manager.send_message_by_user_id(user_id, jsonable_encoder(payload))
		pass

	@app.on_event("startup")
	async def startup():
		await pika_client.init_connection()
		task = loop.create_task(pika_client.consume(loop))
		await task

	app.pika_client = pika_client
	return app
