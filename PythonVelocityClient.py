import asyncio
import json
import websockets
from SendVelocity import get_velocity
from EventInfo import getEventInfoObject
from EventEnums import Events, Devices


async def client():
    uri = "ws://localhost:3000"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                print(message)
                eventInfo = getEventInfoObject(message)
                if eventInfo.header.sentTo == Devices.DETECTOR.value and eventInfo.header.eventName == Events.THROW_BALL.value:
                    await websocket.send(get_velocity())
            except ConnectionError:
                print("Connection Error")
            except json.decoder.JSONDecodeError:
                print("Invalid JSON")


asyncio.run(client())
