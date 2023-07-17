import asyncio
import json
import websockets
from EventInfo import getEventInfoObject, getEventInfoDict
from EventEnums import Events, Devices
from RecordVideoAndUploadUtils import uploadVideo, checkIfBetterShot, getAllPlayerVideoIds, recordVideoWithLogo
import os

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bayId"]

CURRENT_VIDEO_FILE_NAME = "video.avi"
CURRENT_VIDEO_DIR_PATH = os.path.join(bayId, "CurrentVideo")
CURRENT_VIDEO_FULL_PATH = os.path.join(CURRENT_VIDEO_DIR_PATH, CURRENT_VIDEO_FILE_NAME)
ALL_PLAYERS_VIDEOS_DIR_PATH = os.path.join(bayId, "AllPlayersVideos")
LOGO_PATH = "./Logo/MicrosoftTeams-image.png"
VIDEO_INDEX = 0


async def client():
    uri = "ws://localhost:3000"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                eventInfo = getEventInfoObject(message)
                eventInfoDict = getEventInfoDict(message)

                if not eventInfo.header.bayInfo.isForAllBays:
                    if eventInfo.header.bayInfo.bayId != bayId:
                        continue

                if Devices.RECORDER.value in eventInfo.header.sentTo:

                    if eventInfo.header.eventName == Events.THROW_BALL.value:
                        recordVideoWithLogo(CURRENT_VIDEO_FULL_PATH, LOGO_PATH, VIDEO_INDEX)
                    elif eventInfo.header.eventName == Events.CURRENT_BALL_INFO.value:
                        scoreOnCurrentBall = eventInfo.data.value.score
                        currentPlayerId = eventInfo.data.value.scoredBy.id

                        checkIfBetterShot(ALL_PLAYERS_VIDEOS_DIR_PATH, CURRENT_VIDEO_FULL_PATH, CURRENT_VIDEO_FILE_NAME,
                                          "Player_" + currentPlayerId, scoreOnCurrentBall)

                    elif eventInfo.header.eventName == Events.CURRENT_BALL_VIDEO_URL.value:
                        videoUrl = uploadVideo(CURRENT_VIDEO_FULL_PATH, CURRENT_VIDEO_FILE_NAME)
                        eventInfoDict["header"]["sentBy"] = Devices.RECORDER.value
                        eventInfoDict["header"]["sentTo"] = [Devices.PLAYER_APP.value]
                        eventInfoDict["data"]["value"]["videoUrl"] = videoUrl
                        await websocket.send(json.dumps(eventInfoDict))

                    elif eventInfo.header.eventName == Events.GAME_ENDED.value:
                        playerIds = getAllPlayerVideoIds(ALL_PLAYERS_VIDEOS_DIR_PATH)
                        eventInfoDict["header"]["sentBy"] = Devices.RECORDER.value
                        eventInfoDict["header"]["sentTo"] = [Devices.PLAYER_APP.value]
                        eventInfoDict["data"]["value"] = playerIds
                        await websocket.send(json.dumps(eventInfoDict))

            except ConnectionError as e:
                print(f"Connection Error: {e}")
            except json.decoder.JSONDecodeError as e:
                print(f"Invalid JSON: {e}")
            except Exception as e:
                print(f"Error: {e}")


asyncio.run(client())
