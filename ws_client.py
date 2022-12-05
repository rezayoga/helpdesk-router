import json

import asyncio
import websockets


async def send_receive():
	async with websockets.connect(
			'wss://notification.coster.id/notification/B_r6qBs8S8eWwK9FOltCyA',
			ping_interval=10,
			ping_timeout=5) as websocket:
		for i in range(10):
			await websocket.send(json.dumps({
				"broadcast": False,
				"recipients": ["f625487c63c211ed8b03c55baead42b3"],
				"message": {"data": [
					{"message": "ping"}
				]}
			}))
			await asyncio.sleep(0.1)
			msg = await websocket.recv()
			print(msg)


asyncio.run(send_receive())
