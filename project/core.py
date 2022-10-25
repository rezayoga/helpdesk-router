import json
import logging
import os
import uuid
from typing import Dict

import aio_pika
import pika
from aio_pika import connect_robust
from aio_pika.abc import AbstractRobustConnection
from fastapi.encoders import jsonable_encoder
from fastapi.websockets import WebSocket

from project import settings
from project.schemas import Payload as PayloadSchema

logger = logging.getLogger(__name__)  # __name__ = "project"


async def send_personal_message(data: PayloadSchema, websocket: WebSocket):
	await websocket.send_json(jsonable_encoder(data))


class WebSocketManager:
	def __init__(self):
		self.active_connections: Dict[str, WebSocket] = {}

	async def close_all_connections(self):
		for connection in self.active_connections:
			await self.active_connections[connection].close()
		self.active_connections.clear()

	async def notify_user_left(self, user_id: str):
		for connection in self.active_connections:
			if connection != user_id:
				await self.active_connections[connection].send_json({
					"message": f"{user_id} has left"
				})

	async def broadcast(self, data: PayloadSchema):
		for connection in self.active_connections:
			payload = PayloadSchema.parse_obj(data)
			if payload:
				await self.active_connections[connection].send_json(jsonable_encoder(payload.message))

	async def send_message_by_user_id(self, user_id: str, data: PayloadSchema):
		payload = PayloadSchema.parse_obj(data)
		if payload:
			await self.active_connections[user_id].send_json(jsonable_encoder(payload.message))

	async def connect(self, user_id: str, websocket: WebSocket):
		await websocket.accept()
		exist: WebSocket = self.active_connections.get(user_id)
		if exist:
			await exist.close()
			self.active_connections[user_id] = websocket
		else:
			self.active_connections[user_id] = websocket

	def disconnect(self, user_id: str):
		self.active_connections.pop(user_id)
		logger.info("===============================================================")
		logger.info(f"Disconnected: {user_id}")
		logger.info("===============================================================")


class PikaClient:

	def __init__(self, process_callable):
		self.connection = None
		self.process_callable = process_callable

	async def init_connection(self) -> AbstractRobustConnection:
		"""Initiate connection to RabbitMQ"""
		self.connection = await connect_robust(
			os.environ.get("RABBITMQ_URL", "amqp://reza:reza@rezayogaswara.com:5672")
		)

		return self.connection

	async def consume(self, loop):
		"""Setup message listener with the current running loop"""
		connection = await connect_robust(host='rezayogaswara.com', port=5672, login='reza', password='reza', loop=loop)
		channel = await connection.channel()
		queue = await channel.declare_queue(settings.RABBITMQ_SERVICE_QUEUE_NAME, durable=True, auto_delete=False)
		# await queue.consume(self.process_incoming_message, no_ack=False)
		return connection

	# async def process_incoming_message(self, message):
	# 	"""Processing incoming message from RabbitMQ"""
	# 	message.ack()
	# 	body = message.body
	# 	if body:
	# 		self.process_callable(json.loads(body))

	async def publish_async(self, message: dict):
		"""Method to publish message to RabbitMQ"""
		async with self.connection:
			channel = await self.connection.channel()
			await channel.default_exchange.publish(
				aio_pika.Message(
					body=json.dumps(message).encode(),
					delivery_mode=aio_pika.DeliveryMode.PERSISTENT
				),
				routing_key=settings.RABBITMQ_SERVICE_QUEUE_NAME
			)

	def publish(self, message: dict):
		"""Method to publish message to RabbitMQ"""
		self.channel.basic_publish(
			exchange='',
			routing_key=self.publish_queue_name,
			properties=pika.BasicProperties(
				reply_to=self.callback_queue,
				correlation_id=str(uuid.uuid4())
			),
			body=json.dumps(message)
		)
