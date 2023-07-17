import asyncio
import json
import websockets
from SendVelocity import get_velocity
from EventInfo import getEventInfoObject
from EventEnums import Events, Devices

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bayId"]


async def client():
    uri = "ws://localhost:3000"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                # print(message)
                eventInfo = getEventInfoObject(message)
                # eventInfoDict = getEventInfoDict(message)
                if not eventInfo.header.bayInfo.isForAllBays:
                    if eventInfo.header.bayInfo.bayId != bayId:
                        continue
                if Devices.DETECTOR.value in eventInfo.header.sentTo:
                    if eventInfo.header.eventName == Events.THROW_BALL.value:
                        await websocket.send(get_velocity())
            except ConnectionError:
                print("Connection Error")
            except json.decoder.JSONDecodeError:
                print("Invalid JSON")
            # except Exception:
            #     print("error")


asyncio.run(client())
