import json
import logging
from typing import Dict, Optional

import pika
from aio_pika import connect_robust
from fastapi.encoders import jsonable_encoder
from fastapi.websockets import WebSocket
from rich import inspect

from project import settings
from project.schemas import Payload as PayloadSchema, User

logger = logging.getLogger(__name__)  # __name__ = "project"


class WebSocketManager:
	def __init__(self):
		self._users: Dict[str, WebSocket] = {}
		self._user_meta: Dict[str, User] = {}

	def __len__(self) -> int:
		return len(self._users)

	def add_user(self, user_id: str, client_id: str, websocket: WebSocket):
		if user_id in self._users:
			# raise ValueError(f"User {user_id} is already in the websocket_manager")
			self.remove_user(user_id)
		logger.info("Adding user %s to websocket_manager", user_id)
		self._users[user_id] = websocket
		self._user_meta[user_id] = User(
			id=user_id, client_id=client_id
		)

	def remove_user(self, user_id: str):
		if user_id not in self._users:
			raise ValueError(f"User {user_id} is not in the websocket_manager")
		logger.info("Removing user %s from websocket_manager", user_id)
		# del self._users[user_id]
		# del self._user_meta[user_id]
		# await self._users[user_id].close()
		self._users.pop(user_id)
		self._user_meta.pop(user_id)

	def get_user(self, user_id: str) -> Optional[User]:
		"""Get metadata on a user.
		"""
		return self._user_meta.get(user_id)

	async def broadcast_by_user_id(self, user_id: str, payload: PayloadSchema):
		"""Broadcast message to all connected users.
		"""
		payload = PayloadSchema.parse_obj(payload)
		if payload:
			await self._users[user_id].send_json(jsonable_encoder(payload.message))

	async def broadcast_user_joined(self, user_id: str):
		"""Broadcast message to all connected users.
		"""
		for websocket in self._users.values():
			await websocket.send_json({"type": "USER_JOIN", "data": user_id})

	async def broadcast_user_left(self, user_id: str):
		"""Broadcast message to all connected users.
		"""
		for websocket in self._users.values():
			await websocket.send_json({"type": "USER_LEAVE", "data": user_id})

	async def broadcast_all_users(self, payload: PayloadSchema):
		"""Broadcast message to all connected users.
		"""
		payload = PayloadSchema.parse_obj(payload)
		for websocket in self._users.values():
			if payload:
				await websocket.send_json(jsonable_encoder(payload.message))

	@property
	def users(self):
		return self._users


class PikaClient:

	def __init__(self, process_callable):
		self.publish_queue_name = settings.RABBITMQ_SERVICE_QUEUE_NAME
		self.connection = pika.BlockingConnection(
			pika.ConnectionParameters('192.168.217.3', 5672, '/',
			                          pika.PlainCredentials('admin', 'Coster4dm1nP@ssw0rd')
			                          ))
		self.channel = self.connection.channel()
		self.publish_queue = self.channel.queue_declare(queue=self.publish_queue_name, durable=True, auto_delete=False)
		self.channel = self.connection.channel()
		self.callback_queue = self.publish_queue.method.queue
		self.response = None
		self.process_callable = process_callable

	async def consume(self, loop):
		connection = await connect_robust(host='192.168.217.3', port=5672, login='admin',
		                                  password='Coster4dm1nP@ssw0rd', loop=loop)

		channel = await connection.channel()
		queue = await channel.declare_queue(settings.RABBITMQ_SERVICE_QUEUE_NAME, durable=True, auto_delete=False)
		await queue.consume(self.process_incoming_message, no_ack=False, consumer_tag="notification")
		return connection

	async def process_incoming_message(self, message):
		"""Processing incoming message from RabbitMQ"""
		message.ack()
		body = message.body
		if body:
			self.process_callable(json.loads(body))

	def close(self):
		"""Close connection to RabbitMQ"""
		self.connection.close()
