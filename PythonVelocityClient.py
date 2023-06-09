import asyncio
import json
import websockets
from SendVelocity import get_velocity
from EventInfo import getEventInfoObject, getEventInfoDict
from EventEnums import Events, Devices

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bay-id"]

async def client():
    uri = "ws://localhost:3000"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                print(message)
                eventInfo = getEventInfoObject(message)
                eventInfoDict = getEventInfoDict(message)
                if eventInfo.header.bayId == bayId and eventInfo.header.sentTo == Devices.DETECTOR.value:
                    if eventInfo.header.eventName == Events.THROW_BALL.value:
                        await websocket.send(get_velocity())
            except ConnectionError:
                print("Connection Error")
            except json.decoder.JSONDecodeError:
                print("Invalid JSON")
            except Exception:
                print("error")


asyncio.run(client())
