import asyncio

import websockets


async def send_receive():
	async with websockets.connect(
			'wss://notifier.rezayogaswara.dev/notification/user1.0cc175b9c0f1b6a831c399e269772661',
			ping_interval=5,
			ping_timeout=20) as websocket:
		for i in range(10):
			await websocket.send(str(i))
			await asyncio.sleep(0.1)
			msg = await websocket.recv()
			print(msg)


asyncio.run(send_receive())
