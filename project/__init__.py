import asyncio
import json
import logging
import logging.config
import os

import aioredis
from aio_pika.abc import AbstractIncomingMessage
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import parse_obj_as

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

	app.debug = True
	app.celery_app = create_celery()

	html_broadcast = """
	<!DOCTYPE html>
	<html>
	    <head>
	        <title>Clients</title>
	    </head>
	    <body onload="connect(event)">
	        <h1 id="h1-title">Clients</h1>
	        <select user_id="select_token" style="width:30%" onchange="connect(this)">
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
	            function connect(select_object) {
	                var token = select_object.value;
	                if (token !== undefined) {
		                ws = new WebSocket("wss://notifier.rezayogaswara.dev/notification/" + token);
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

	websocket_manager = WebSocketManager()
	pika_client = PikaClient(log_incoming_message)

	@app.get("/")
	async def get():
		return HTMLResponse(html_broadcast)

	@app.websocket("/notification/{token}")
	async def notification(websocket: WebSocket, token: str):
		user_validation = await validate_auth_token(token)

		if user_validation.is_validated:
			await websocket_manager.connect(user_validation.user_id, websocket)
			try:
				while True:
					data = await websocket.receive_json()
					websocket_manager.broadcast(data)
			except WebSocketDisconnect:
				websocket_manager.disconnect(user_validation.user_id)
				await websocket_manager.notify_user_left(user_validation.user_id)

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
		async with message.process():
			key_list = list(websocket_manager.active_connections.keys())
			payload = parse_obj_as(PayloadSchema, json.loads(message.body))

			if payload.broadcast:
				await websocket_manager.broadcast(jsonable_encoder(payload))
			else:
				r = sorted(payload.recipients)
				active_user_in_websocket = sorted(key_list)
				intersection = set(r).intersection(set(active_user_in_websocket))
				if len(intersection) > 0:
					for user_id in intersection:
						await websocket_manager.send_message_by_user_id(user_id, jsonable_encoder(payload))

	@app.post("/broadcast", response_model=PayloadSchema)
	async def post_broadcast(data: PayloadSchema):
		await websocket_manager.broadcast(data)
		return data

	@app.on_event("startup")
	async def startup():
		await pika_client.init_connection()
		task = loop.create_task(pika_client.consume(loop))
		await task

	app.pika_client = pika_client
	return app
