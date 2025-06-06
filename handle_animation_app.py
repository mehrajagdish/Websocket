import asyncio
import websockets
import subprocess
import json
import sys
import psutil
import traceback

from EventEnums import Devices, Events
from EventInfo import getEventInfoObject

CONFIG_PATH = "./config.json"

try:
    with open(CONFIG_PATH) as fp:
        config = json.load(fp)
except Exception as e:
    print(f"[ERROR] Failed to load config: {e}")
    sys.exit(1)

bayId = config.get("bayId")
WS_URL = config.get("websocketServerURI")
BATCH_FILE_PATH = config.get("batchFilePath")

if not (bayId and WS_URL and BATCH_FILE_PATH):
    print("[ERROR] Missing required configuration values.")
    sys.exit(1)

app_process = None


def kill_process_tree(pid):
    """Kills a process and all of its children."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except Exception as e:
                print(f"[WARNING] Failed to kill child PID {child.pid}: {e}")
        parent.kill()
        print(f"[INFO] Killed process tree for PID {pid}")
    except psutil.NoSuchProcess:
        print(f"[WARNING] Process with PID {pid} no longer exists.")
    except Exception as e:
        print(f"[ERROR] Failed to kill process tree: {e}")


async def listen():
    global app_process
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("[INFO] Connected to WebSocket server.")
            async for message in websocket:
                try:
                    eventInfo = getEventInfoObject(message)
                except Exception as e:
                    print(f"[ERROR] Failed to parse event: {e}")
                    traceback.print_exc()
                    continue

                try:
                    if not eventInfo.header.bayInfo.isForAllBays and eventInfo.header.bayInfo.bayId != bayId:
                        continue

                    if Devices.ANIMATION_APP_HANDLER.value in eventInfo.header.sentTo:
                        if Events.START_APPLICATION.value == eventInfo.header.eventName:
                            if app_process is None:
                                try:
                                    print("[INFO] Starting application via batch file...")
                                    app_process = subprocess.Popen(BATCH_FILE_PATH, shell=True)
                                    print(f"[INFO] Application started with PID {app_process.pid}")
                                except Exception as e:
                                    print(f"[ERROR] Failed to start application: {e}")
                                    app_process = None

                        elif Events.CLOSE_APPLICATION.value == eventInfo.header.eventName:
                            print("[INFO] Close event received. Terminating application...")
                            if app_process:
                                try:
                                    kill_process_tree(app_process.pid)
                                    app_process.wait(timeout=5)
                                    print("[INFO] Application and batch file terminated.")
                                except Exception as e:
                                    print(f"[ERROR] Failed to close application: {e}")
                                finally:
                                    app_process = None
                            else:
                                print("[INFO] No application running.")
                except Exception as e:
                    print(f"[ERROR] Unexpected error during event handling: {e}")
                    traceback.print_exc()

    except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
        print(f"[WARNING] WebSocket connection issue: {e}")
        raise  # Let main() handle the reconnect logic
    except Exception as e:
        print(f"[ERROR] Unexpected error in listen loop: {e}")
        traceback.print_exc()


async def main():
    while True:
        try:
            await listen()
        except Exception as e:
            print(f"[INFO] Reconnecting in 5 seconds due to error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Script interrupted by user.")
        if app_process:
            try:
                kill_process_tree(app_process.pid)
            except Exception as e:
                print(f"[ERROR] Failed to kill process on exit: {e}")
