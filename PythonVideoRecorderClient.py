import asyncio
import json
import websockets
from EventInfo import getEventInfoObject, getEventInfoDict
from EventEnums import Events, Devices
from RecordVideoAndUpload import recordVideo, uploadVideo

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
                if eventInfo.header.bayId == bayId and eventInfo.header.sentTo == Devices.RECORDER.value:
                    if eventInfo.header.eventName == Events.THROW_BALL.value:
                        recordVideo("./Videos/")
                    if eventInfo.header.eventName == Events.CURRENT_BALL_INFO.value:
                        videoId = ""
                        if eventInfo.data.value.score == "6":
                            videoId = uploadVideo("./Videos/video.avi")
                        eventInfoDict["header"]["sentBy"] = Devices.RECORDER.value
                        eventInfoDict["header"]["sentTo"] = Devices.PLAYER_APP.value
                        eventInfoDict["data"]["value"]["videoId"] = videoId
                        await websocket.send(json.dumps(eventInfoDict))

            except ConnectionError:
                print("Connection Error")
            except json.decoder.JSONDecodeError:
                print("Invalid JSON")
            except Exception:
                print("error")


asyncio.run(client())
