import asyncio
import json
import os
import time

import websockets

from EventEnums import Events, Devices
from EventInfo import EventInfo, Header, Data, BayInfo
from EventInfo import getEventInfoObject, getEventInfoDict
from RecordVideoAndUploadUtils import (uploadVideo, checkIfBetterShot, getAllPlayerVideoUrls,
                                       recordVideoUsingNetworkCameraWithLogo, getCurrentVideoUrl)

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bayId"]

CURRENT_VIDEO_FILE_NAME = config["currentShotVideoName"]
CURRENT_VIDEO_DIR_PATH = os.path.join(bayId, str(config["currentVideoDirectory"]))
CURRENT_VIDEO_FULL_PATH = os.path.join(CURRENT_VIDEO_DIR_PATH, CURRENT_VIDEO_FILE_NAME)
ALL_PLAYERS_VIDEOS_DIR_PATH = os.path.join(bayId, str(config["allPlayersVideoDirectory"]))
LOGO_PATH = config["logoPath"]

RTSP_URL = config["cameraRTSP"]
WS_URI = config["websocketServerURI"]
TIME_INTERVAL_BETWEEN_EVENTS = config["timeIntervalBetweenEvents"]
VIDEO_LENGTH = config["videoLength"]

lastEvent = {}


async def getVideoRecordedEvent(forBay):
    bayInfo = BayInfo(isForAllBays=False, bayId=forBay)
    header = Header(Devices.RECORDER.value, [Devices.UNITY.value], Events.PLAY_VIDEO.value, bayInfo)
    data = Data({"value": "1"})
    event = EventInfo(header, data)

    return json.dumps(event, default=vars)


async def client():
    while True:
        async with websockets.connect(WS_URI) as websocket:
            try:
                message = await websocket.recv()
                eventInfo = getEventInfoObject(message)
                eventInfoDict = getEventInfoDict(message)

                if not eventInfo.header.bayInfo.isForAllBays:
                    if eventInfo.header.bayInfo.bayId != bayId:
                        continue

                if Devices.RECORDER.value in eventInfo.header.sentTo:

                    if eventInfo.header.eventName in lastEvent:
                        if time.time() - lastEvent[eventInfo.header.eventName] < TIME_INTERVAL_BETWEEN_EVENTS:
                            print("Skipping event", eventInfo.header.eventName)
                            print("Time Difference: ", time.time() - lastEvent[eventInfo.header.eventName])
                            continue

                    lastEvent[eventInfo.header.eventName] = time.time()

                    if eventInfo.header.eventName == Events.THROW_BALL.value:
                        recordVideoUsingNetworkCameraWithLogo(CURRENT_VIDEO_DIR_PATH, CURRENT_VIDEO_FILE_NAME,
                                                              LOGO_PATH, RTSP_URL, VIDEO_LENGTH)
                        recordedEventJson = await getVideoRecordedEvent(eventInfo.header.bayInfo.bayId)
                        await websocket.send(recordedEventJson)

                    elif eventInfo.header.eventName == Events.CURRENT_BALL_INFO.value:
                        scoreOnCurrentBall = eventInfo.data.value.score
                        currentPlayerId = eventInfo.data.value.scoredBy.id

                        checkIfBetterShot(ALL_PLAYERS_VIDEOS_DIR_PATH, CURRENT_VIDEO_FULL_PATH, CURRENT_VIDEO_FILE_NAME,
                                          "Player_" + currentPlayerId, scoreOnCurrentBall)

                    elif eventInfo.header.eventName == Events.CURRENT_BALL_VIDEO_URL.value:
                        scoreOnCurrentBall = eventInfo.data.value.score
                        videoUrl = getCurrentVideoUrl(CURRENT_VIDEO_DIR_PATH, CURRENT_VIDEO_FILE_NAME,
                                                      scoreOnCurrentBall)
                        eventInfoDict["header"]["sentBy"] = Devices.RECORDER.value
                        eventInfoDict["header"]["sentTo"] = [Devices.PLAYER_APP.value]
                        eventInfoDict["data"]["value"]["videoUrl"] = videoUrl
                        await websocket.send(json.dumps(eventInfoDict))

                    elif eventInfo.header.eventName == Events.GAME_ENDED.value:
                        playerIds = getAllPlayerVideoUrls(ALL_PLAYERS_VIDEOS_DIR_PATH)
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
