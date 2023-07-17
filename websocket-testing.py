import asyncio
import random
import time

import websockets
import json
from EventInfo import EventInfo, BayInfo, Header, Data
from EventEnums import Events, Devices

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bayId"]


async def client():
    uri = "ws://localhost:3000"
    async with websockets.connect(uri) as websocket:
        count = 1
        while count <= 6:
            try:
                bayInfo = BayInfo(isForAllBays=False, bayId="001")
                header = Header(Devices.UNITY.value, [Devices.PLAYER_APP.value],
                                Events.CURRENT_BALL_INFO.value, bayInfo)
                data = Data(value={"scoredBy": {"id": "1", "name": "string"}, "totalBallCount": str(count),
                                   "score": str(random.choice([6, 15]))})
                event = EventInfo(header, data)

                eventJson = json.dumps(event, default=vars)
                await websocket.send(eventJson)
                time.sleep(5)
                count += 1
            except ConnectionError:
                print("Connection Error")
            except json.decoder.JSONDecodeError:
                print("Invalid JSON")
            # except Exception:
            #     print("error")


asyncio.run(client())
