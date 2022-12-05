import json

import asyncio
import websockets


async def send_receive():
	async with websockets.connect(
			'wss://notification.coster.id/notification/B_r6qBs8S8eWwK9FOltCyA',
			ping_interval=5,
			ping_timeout=20) as websocket:
		for i in range(10):
			await websocket.send(json.dumps({
				"message": "ping"
			}))
			await asyncio.sleep(0.1)
			msg = await websocket.recv()
			print(msg)


asyncio.run(send_receive())
