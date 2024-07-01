import asyncio
import json
import socket
import threading
import time

import websockets

from BowlingMachine import BowlingMachineResponse
from EventEnums import Events, Devices
from EventInfo import getEventInfoObject

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bayId"]
API_KEY = config["machineApiKey"]
TRIGGER_DELAY = config["triggerDelay"]

tcp_socket = None

last_trigger_time = time.time()


def triggerReceived(messageFromTCP):
    message = json.loads(messageFromTCP)
    if message["response"] == BowlingMachineResponse.BALLTRIGGERED.value:
        return True
    return False


def send_feed_command_to_tcp(tcp_socket):
    message = f"[F/{API_KEY}/3/]?"
    send_message_to_tcp(tcp_socket, message)


def tcp_client_receive(tcp_socket, websocket):
    global last_trigger_time
    try:
        while True:
            message = tcp_socket.recv(1024).decode('utf-8')
            print("TCP: Message received: " + message)
            if not message:
                print("TCP connection closed by server.")
                break
            if triggerReceived(message) and time.time() - last_trigger_time >= TRIGGER_DELAY:
                send_feed_command_to_tcp(tcp_socket)
                asyncio.run(send_message_to_websocket(websocket, message))
                last_trigger_time = time.time()
            else:
                print("Skipping event, time difference: ", time.time() - last_trigger_time)
    except Exception as e:
        print(f"TCP client receive error: {e}")
    finally:
        tcp_socket.close()
        asyncio.run(handle_tcp_disconnection(websocket))


async def handle_tcp_disconnection(websocket):
    print("Attempting to reconnect to TCP server...")
    global tcp_socket
    while True:
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.connect(('localhost', 6789))
            print("Successfully reconnected to TCP server.")
            threading.Thread(target=tcp_client_receive, args=(tcp_socket, websocket)).start()
            return
        except Exception as e:
            print(f"Reconnection attempt failed: {e}")
            tcp_socket.close()
        await asyncio.sleep(3)


def send_message_to_tcp(tcp_socket, message):
    if tcp_socket:
        try:
            tcp_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message to TCP server: {e}")


def start_tcp_client(websocket):
    global tcp_socket
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_socket.connect(('localhost', 6789))
        print("Successfully connected to TCP server.")
        threading.Thread(target=tcp_client_receive, args=(tcp_socket, websocket)).start()
        return tcp_socket
    except Exception as e:
        print(f"Error connecting to TCP server: {e}")
        tcp_socket.close()
        asyncio.run(handle_tcp_disconnection(websocket))
        return None


async def websocket_client_receive(websocket):
    global tcp_socket
    try:
        async for message in websocket:
            print(f"Received from WebSocket server: {message}")
            messageToBeSent = getMessageToBeSentToTCP(message)
            if messageToBeSent is not None:
                send_message_to_tcp(tcp_socket, messageToBeSent)
    except Exception as e:
        print(f"WebSocket client receive error: {e}")
    finally:
        await websocket.close()


async def send_message_to_websocket(websocket, message):
    try:
        await websocket.send(json.dumps(message))
    except Exception as e:
        print(f"Error sending message to WebSocket server: {e}")


def getMessageToBeSentToTCP(messageFromWebsocket):
    eventInfo = getEventInfoObject(messageFromWebsocket)

    if not eventInfo.header.bayInfo.isForAllBays:
        if eventInfo.header.bayInfo.bayId != bayId:
            return

    if Devices.BOWLING_MACHINE.value in eventInfo.header.sentTo:
        if Events.BOWLING_MACHINE_STATUS.value == eventInfo.header.eventName:
            return f"[S/{API_KEY}/]?"
        elif Events.SET_BOWLING_MACHINE_PARAMETERS.value == eventInfo.header.eventName:
            return (f"[A/{API_KEY}/{eventInfo.data.value.speed}"
                    f"/{eventInfo.data.value.mode}/{eventInfo.data.value.swing}/]?")
        elif Events.FEED_BOWLING_MACHINE.value == eventInfo.header.eventName:
            return f"[F/{API_KEY}/3/]?"


def getMessageToBeSentToWebsocket(messageFromTCP):
    message = json.loads(messageFromTCP)
    if message["response"] == BowlingMachineResponse.BALLTRIGGERED.value:
        return {
            "header": {
                "sentBy": Devices.TRIGGER.value,
                "sentTo": [
                    Devices.RECORDER.value,
                    Devices.DETECTOR.value
                ],
                "eventName": Events.THROW_BALL.value,
                "bayInfo": {
                    "isForAllBays": False,
                    "bayId": bayId
                }
            },
            "data": {
                "value": "1"
            }
        }

    elif message["response"] == BowlingMachineResponse.READY.value:
        return {
            "header": {
                "sentBy": Devices.BOWLING_MACHINE.value,
                "sentTo": [
                    Devices.PLAYER_APP.value,
                    "detector"
                ],
                "eventName": Events.BOWLING_MACHINE_STATUS.value,
                "bayInfo": {
                    "isForAllBays": False,
                    "bayId": bayId
                }
            },
            "data": {
                "value": {
                    "active": True
                }
            }
        }

    return None


async def start_websocket_client():
    while True:
        try:
            async with websockets.connect('ws://localhost:3000') as websocket:
                print("Successfully connected to WebSocket server.")
                tcp_socket = start_tcp_client(websocket)
                if tcp_socket:
                    await websocket_client_receive(websocket)
                else:
                    await handle_tcp_disconnection(websocket)
        except Exception as e:
            print(f"Error connecting to WebSocket server: {e}")
        await asyncio.sleep(3)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_websocket_client())
    loop.run_forever()


if __name__ == "__main__":
    main()
