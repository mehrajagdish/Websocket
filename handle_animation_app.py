import asyncio
import websockets
import subprocess
import json
import sys

from EventEnums import Devices, Events
from EventInfo import getEventInfoObject

CONFIG_PATH = "./config.json"
with open(CONFIG_PATH) as fp:
    config = json.load(fp)

bayId = config["bayId"]
WS_URL = config["websocketServerURI"]

# Path to your batch file
BATCH_FILE_PATH = config["websocketServerURI"]

# Global to hold the subprocess.Popen object for the started application
app_process = None


async def listen():
    global app_process
    async with websockets.connect(WS_URL) as websocket:
        print("Connected to WebSocket server.")
        async for message in websocket:
            print(f"Received message: {message}")
            eventInfo = getEventInfoObject(message)
            if not eventInfo.header.bayInfo.isForAllBays and eventInfo.header.bayInfo.bayId != bayId:
                return None
            if Devices.ANIMATION_APP_HANDLER.value in eventInfo.header.sentTo:
                if Events.START_APPLICATION.value == eventInfo.header.eventName:
                    if app_process is None:
                        print("Starting application via batch file...")
                        # Start the batch file and keep the handle
                        # Using shell=True to run batch file, capture the process
                        app_process = subprocess.Popen([BATCH_FILE_PATH], shell=True)
                        print(f"Application started with PID {app_process.pid}")
                elif Events.CLOSE_APPLICATION.value == eventInfo.header.eventName:
                    print("Closing application and exiting...")
                    if app_process:
                        # Terminate the process
                        app_process.terminate()
                        try:
                            app_process.wait(timeout=5)
                            print("Application closed gracefully.")
                        except subprocess.TimeoutExpired:
                            print("Force killing the application.")
                            app_process.kill()
                        app_process = None
                    else:
                        print("No application running.")
                    # Exit script
                    sys.exit(0)


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
        if app_process is not None:
            app_process.terminate()
