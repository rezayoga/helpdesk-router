import asyncio
import json
import logging.config
from typing import Optional

import aioredis
from aio_pika.abc import AbstractIncomingMessage
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocket
from pydantic import parse_obj_as
from starlette.endpoints import WebSocketEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from project.config import settings
from project.core import WebSocketManager, PikaClient
from project.schemas import User as UserSchema, Payload as PayloadSchema, UserValidation

# redis = aioredis.from_url(os.environ.get('result_backend', "redis://reza:reza1985@103.41.204.222:6379/15"))
# redis = aioredis.from_url(f"redis://:{quote_plus('Cost3rv3Redi5P@ssw0rd').replace('%', '%%')}@192.168.217.2:6379/0")
redis = aioredis.from_url(
	"redis://192.168.217.2:6379/0", password="Cost3rv3Redi5P@ssw0rd"
)
# setup loggers
logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

# get root logger
logger = logging.getLogger(__name__)  # __name__ = "project"
loop = asyncio.get_event_loop()
wm: WebSocketManager = None


def create_app() -> FastAPI:
	app = FastAPI(title="Helpdesk Notification Service",
	              version="1.0.0",
	              description="Helpdesk Notification Service",
	              contact={
		              "name": "Reza Yogaswara",
		              "url": "https://me.rezayogaswara.dev/",
		              "email": "reza.yoga@gmail.com",
	              })
	app.add_middleware(
		CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]
	)

	class WebSocketManagerEventMiddleware:  # pylint: disable=too-few-public-methods
		"""Middleware to add the websocket_manager to the scope."""

		def __init__(self, app: ASGIApp):
			self._app = app
			self._websocket_manager = WebSocketManager()

		async def __call__(self, scope: Scope, receive: Receive, send: Send):
			if scope["type"] in ("lifespan", "http", "websocket"):
				scope["websocket_manager"] = self._websocket_manager
			await self._app(scope, receive, send)

	app.add_middleware(WebSocketManagerEventMiddleware)

	html_broadcast = """
	<!DOCTYPE html>
	<html>
	    <head>
	        <title>Websocket Subscriber Simulator</title>
	    </head>
	    <body onload="add_user(event)">
	        <h1 id="h1-title">Clients</h1>
	        <select user_id="select_token" style="width:30%" onchange="add_user(this)">
	          <option selected="selected" value="-">Select Token</option>
			  <option value="user.jfD6puH8TnKLbxBtopU8RQ">Token #1 (Valid - user.B_r6qBs8S8eWwK9FOltCyA)</option>
			  <option value="user.jfD6puH8TnKLbxBtopU8RQ">Token #2 (Valid - user.jfD6puH8TnKLbxBtopU8RQ)</option>
			  <option value="user.2LsA4HqVS5ucd4wTdmpJgQ">Token #3 (Valid - user.2LsA4HqVS5ucd4wTdmpJgQ)</option>
			  <option value="token.b4825c7863c411ed8b03c55baead42b3">Token #4 (Valid - token.b4825c7863c411ed8b03c55baead42b3)</option>
			  <option value="user.GLBHlkW3QSqSDgZV3sKZmA">Token #5 (Valid - user.GLBHlkW3QSqSDgZV3sKZmA)</option>
			  <option value="user.4a8a08f09d37b73795649038408b5f33">Token #6 (Invalid)</option>
			  <option value="user.123/undefined">Token #7 (Invalid)</option>
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
	                	// localhost:8005
		                const ws_url = '/notification/' + token;
					    const ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://notification.coster.id' + ws_url);
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

	@app.websocket_route("/notification/{token}", name="ws")
	class NotifierApp(WebSocketEndpoint):

		encoding: str = "json"
		session_name: str = ""
		count: int = 0

		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.websocket_manager: Optional[WebSocketManager] = None
			self.user_id: Optional[str] = None

		async def on_connect(self, websocket):
			global wm
			_wm = self.scope.get("websocket_manager")
			if _wm is None:
				raise RuntimeError(f"Global `WebSocketManager` instance unavailable!")
			self.websocket_manager = _wm
			wm = self.websocket_manager
			await websocket.accept()
			token = websocket.path_params['token']
			validated_user = await NotifierApp.validate_auth_token(token)
			if validated_user.is_validated:
				self.user_id = validated_user.user.user.id
				logger.info(f"User {self.user_id} connected")
				await websocket.send_json(
					{"type": "WEBSOCKET_JOIN", "data": {"id": self.user_id,
					                                    "client": jsonable_encoder(validated_user.user)}}
				)
				await self.websocket_manager.broadcast_user_joined(self.user_id)
				self.websocket_manager.add_user(self.user_id, validated_user.user.user.id, websocket)
			else:
				logger.info(f"Invalid token {token}")
				await websocket.send_json({"type": "AUTH_ERROR", "data": {"error": "Invalid token"}})
				await websocket.close()
			# raise WebSocketDisconnect()
			# return RedirectResponse("wss://notification.coster.id/_/unauthorized")

		async def on_disconnect(self, _websocket: WebSocket, _close_code: int):
			if self.user_id is None:
				raise RuntimeError(
					"WebSocketManager.on_disconnect() called without a valid user_id"
				)
			self.websocket_manager.remove_user(self.user_id)
			await self.websocket_manager.broadcast_user_left(self.user_id)

		async def on_receive(self, _websocket: WebSocket, payload: PayloadSchema):
			if self.user_id is None:
				raise RuntimeError("WebSocketManager.on_receive() called without a valid user_id")
			if not isinstance(payload, str):
				raise ValueError(f"WebSocketManager.on_receive() passed unhandleable data: {payload}")
			await self.websocket_manager.broadcast_by_user_id(self.user_id, payload)

		@staticmethod
		async def validate_auth_token(auth_token: str) -> UserValidation:
			logger.info(f"Validating token: {auth_token}")
			user = await redis.get(auth_token)

			if user is not None:
				# logger.info(f"User {json.loads(user)} is valid {type(json.loads(user))}")
				# u = UserSchema(**json.loads(user.decode('utf-8')))
				# u = UserSchema.parse_obj(json.loads(user.decode('utf-8')))
				u = parse_obj_as(UserSchema, json.loads(user.decode('utf-8')))
				logger.info(f"User {u} is valid {type(u)}")
				return UserValidation(is_validated=True, user=u)
			return UserValidation(is_validated=False, user=None)

	@app.post('/publish-payload')
	async def publish_payload(request: Request, payload: PayloadSchema):
		await pika_client.init_connection(loop=loop)
		await request.app.pika_client.publish_async(
			jsonable_encoder(payload),
		)

		connection = await request.app.pika_client.consume(loop)
		channel = await connection.channel()
		queue = await channel.declare_queue(settings.RABBITMQ_SERVICE_QUEUE_NAME, durable=True)
		await queue.consume(on_message, no_ack=False)
		return {"status": "Message published successfully"}

	# @app.post('/publish-payload-to-rmq')
	# async def publish_payload_to_rmq(request: Request, payload: PayloadSchema):
	# 	await pika_client.init_connection(loop=loop)
	# 	await request.app.pika_client.publish_async(
	# 		jsonable_encoder(payload),
	# 	)
	#
	# 	return {"status": "published"}
	#
	# @app.get('/consume-payload-from-rmq')
	# async def consume_payload_from_rmq(request: Request):
	# 	connection = await request.app.pika_client.consume(loop)
	# 	channel = await connection.channel()
	# 	queue = await channel.declare_queue(settings.RABBITMQ_SERVICE_QUEUE_NAME, durable=True)
	# 	await queue.consume(on_message, no_ack=False)
	# 	return {"status": "consuming"}

	async def on_message(message: AbstractIncomingMessage) -> None:
		async with message.process():
			if wm is not None:
				key_list = wm.users.keys()
				payload = parse_obj_as(PayloadSchema, json.loads(message.body))

				if payload.broadcast:
					await wm.broadcast_all_users(jsonable_encoder(payload))
				else:
					r = sorted(payload.recipients)
					active_user_in_websocket = sorted(key_list)
					intersection = set(r).intersection(set(active_user_in_websocket))
					if len(intersection) > 0:
						for user_id in intersection:
							await wm.broadcast_by_user_id(user_id, jsonable_encoder(payload))

	@app.on_event("startup")
	async def startup():
		await pika_client.init_connection(loop)
		task = loop.create_task(pika_client.consume(loop))
		await task

	app.pika_client = pika_client
	return app
