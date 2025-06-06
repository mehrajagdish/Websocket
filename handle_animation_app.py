import asyncio
import websockets
import subprocess
import json
import sys
import psutil

from EventEnums import Devices, Events
from EventInfo import getEventInfoObject

CONFIG_PATH = "./config.json"
with open(CONFIG_PATH) as fp:
    config = json.load(fp)

bayId = config["bayId"]
WS_URL = config["websocketServerURI"]
BATCH_FILE_PATH = config["batchFilePath"]

app_process = None


def kill_process_tree(pid):
    """Kills a process and all of its children."""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass


async def listen():
    global app_process
    async with websockets.connect(WS_URL) as websocket:
        print("Connected to WebSocket server.")
        async for message in websocket:
            eventInfo = getEventInfoObject(message)

            if not eventInfo.header.bayInfo.isForAllBays and eventInfo.header.bayInfo.bayId != bayId:
                continue

            if Devices.ANIMATION_APP_HANDLER.value in eventInfo.header.sentTo:
                if Events.START_APPLICATION.value == eventInfo.header.eventName:
                    if app_process is None:
                        print("Starting application via batch file...")
                        app_process = subprocess.Popen(BATCH_FILE_PATH, shell=True)
                        print(f"Application started with PID {app_process.pid}")

                elif Events.CLOSE_APPLICATION.value == eventInfo.header.eventName:
                    print("Closing application and exiting...")
                    if app_process:
                        kill_process_tree(app_process.pid)
                        app_process.wait()
                        print("Application and batch file terminated.")
                        app_process = None
                    else:
                        print("No application running.")


async def main():
    while True:
        try:
            await listen()
        except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
            print(f"Connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Script interrupted by user.")
        if app_process:
            kill_process_tree(app_process.pid)
