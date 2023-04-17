import asyncio
import json
import websockets
from SendVelocity import get_velocity
from EventInfo import getEventInfoObject


async def client():
    uri = "ws://localhost:3000"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                print(message)
                eventInfo = getEventInfoObject(message)
                if eventInfo.header.sentTo == "Detector" and eventInfo.header.eventName == "throwBall":
                    await websocket.send(get_velocity())
            except ConnectionError and json.decoder.JSONDecodeError:
                print("error")


asyncio.run(client())
