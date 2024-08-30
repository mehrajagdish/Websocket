import asyncio
import json
import os
import threading
import time

import websockets
from websockets.exceptions import ConnectionClosedError

from EventEnums import Events, Devices
from EventInfo import EventInfo, Header, Data, BayInfo
from EventInfo import getEventInfoObject, getEventInfoDict
from RecordVideoAndUploadUtils import (checkIfBetterShot, getAllPlayerVideoUrls,
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
is_ws_connected = False


async def getVideoRecordedEvent(forBay):
    bayInfo = BayInfo(isForAllBays=False, bayId=forBay)
    header = Header(Devices.RECORDER.value, [Devices.UNITY.value], Events.PLAY_VIDEO.value, bayInfo)
    data = Data({"value": "1"})
    event = EventInfo(header, data)

    return json.dumps(event, default=vars)


async def ping_ws_server(websocket: websockets.WebSocketClientProtocol):
    global is_ws_connected
    while is_ws_connected:
        try:
            await websocket.ping()
            await asyncio.sleep(5)  # Non-blocking sleep
        except ConnectionClosedError:
            print("WebSocket connection closed while pinging.")
            is_ws_connected = False
            break
        except Exception as e:
            print(f"Error pinging WebSocket server: {e}")
            is_ws_connected = False
            break


async def handleMessage(message, websocket):
    eventInfo = getEventInfoObject(message)
    eventInfoDict = getEventInfoDict(message)

    if not eventInfo.header.bayInfo.isForAllBays:
        if eventInfo.header.bayInfo.bayId != bayId:
            return

    if Devices.RECORDER.value in eventInfo.header.sentTo:

        if eventInfo.header.eventName in lastEvent:
            if time.time() - lastEvent[eventInfo.header.eventName] < TIME_INTERVAL_BETWEEN_EVENTS:
                print("Skipping event", eventInfo.header.eventName)
                print("Time Difference: ", time.time() - lastEvent[eventInfo.header.eventName])
                return

        lastEvent[eventInfo.header.eventName] = time.time()

        if eventInfo.header.eventName == Events.THROW_BALL.value:
            recordVideoUsingNetworkCameraWithLogo(CURRENT_VIDEO_DIR_PATH, CURRENT_VIDEO_FILE_NAME,
                                                  LOGO_PATH, RTSP_URL, VIDEO_LENGTH)
            recordedEventJson = await getVideoRecordedEvent(eventInfo.header.bayInfo.bayId)
            await websocket.send(recordedEventJson)

        elif eventInfo.header.eventName == Events.CURRENT_BALL_INFO.value:
            scoreOnCurrentBall = eventInfo.data.value.score
            currentPlayerId = eventInfo.data.value.scoredBy.id

            checkIfBetterShot(ALL_PLAYERS_VIDEOS_DIR_PATH, CURRENT_VIDEO_FULL_PATH,
                              CURRENT_VIDEO_FILE_NAME,
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


async def client():
    global is_ws_connected
    while True:
        try:
            async with websockets.connect(WS_URI) as websocket:
                print(f"Connected to websocket at {WS_URI}")

                is_ws_connected = True
                # Start ping_ws_server as a background task
                ping_task = asyncio.create_task(ping_ws_server(websocket))

                try:
                    while True:
                        message = await websocket.recv()
                        await handleMessage(message, websocket)
                except ConnectionClosedError:
                    print("Connection closed, attempting to reconnect...")
                except json.decoder.JSONDecodeError as e:
                    print(f"Invalid JSON: {e}")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    print(f"Error: {e}")

                # Wait for the ping task to finish if the WebSocket connection closes
                # ping_task.cancel()
                await ping_task

        except ConnectionError as e:
            print(f"Connection Error: {e}")
            is_ws_connected = False
            print("Reconnecting to WebSocket server in 5 seconds...")
        except asyncio.CancelledError:
            print("Client task was cancelled")
            break
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected, closing the client.")
            break
        except Exception as e:
            print(f"Error: {e}")
            is_ws_connected = False
            print("Reconnecting to WebSocket server in 5 seconds...")

        await asyncio.sleep(5)


async def main():
    try:
        await client()
    except asyncio.CancelledError:
        print("Main task was cancelled")
    finally:
        print("Shutting down gracefully...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Process interrupted by user, exiting.")
