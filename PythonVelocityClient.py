import asyncio
import json
import websockets
from SendVelocity import get_velocity
from EventInfo import getEventInfoObject, getEventInfoDict
from EventEnums import Events, Devices
import base64

async def client():
    uri = "ws://localhost:3000"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                print(message)
                eventInfo = getEventInfoObject(message)
                eventInfoDict = getEventInfoDict(message)
                if eventInfo.header.sentTo == Devices.DETECTOR.value:
                    if eventInfo.header.eventName == Events.THROW_BALL.value:
                        await websocket.send(get_velocity())
                    if eventInfo.header.eventName == Events.CURRENT_BALL_INFO.value:
                        with open(
                                "/home/dev-team/Documents/krida-python/Jagdish/CustomMultipleWebcam/ColorMaskVideos"
                                "/1681986230665.avi",
                                "rb") as videoFile:
                            videoStringList = []
                            while True:
                                video_chunk = videoFile.read(1024*1024)
                                text = base64.b64encode(video_chunk)

                                if not text:
                                    break
                                videoStringList.append(text)

                            eventInfoDict["header"]["sentTo"] = Devices.PLAYER_APP.value
                            # setattr(eventInfo.header, "sentTo", Devices.PLAYER_APP.value)
                            eventInfoDict["data"]["value"]["videoString"] = videoStringList
                            # setattr(eventInfo.data.value, "videoString", text)
                            await websocket.send(json.dumps(eventInfoDict))

            except ConnectionError:
                print("Connection Error")
            except json.decoder.JSONDecodeError:
                print("Invalid JSON")
            except Exception:
                print("error")


asyncio.run(client())
