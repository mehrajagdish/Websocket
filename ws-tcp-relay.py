import asyncio
import json
import socket
import threading

import websockets

from BowlingMachine import BowlingMachineResponse
from EventEnums import Events, Devices
from EventInfo import getEventInfoObject

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bayId"]
API_KEY = config["machineApiKey"]


def tcp_client_receive(tcp_socket, websocket):
    try:
        while True:
            message = tcp_socket.recv(1024).decode('utf-8')
            if message and message.strip() != '':
                print(f"Received from TCP server: {message}")
                messageToBeSent = getMessageToBeSentToWebsocket(message)
                if messageToBeSent:
                    asyncio.run(send_message_to_websocket(websocket, messageToBeSent))
    except Exception as e:
        print(f"TCP client receive error: {e}")
    finally:
        tcp_socket.close()


def send_message_to_tcp(tcp_socket, message):
    try:
        tcp_socket.send(message.encode('utf-8'))
    except Exception as e:
        print(f"Error sending message to TCP server: {e}")


def start_tcp_client(websocket):
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_socket.connect(('192.168.4.1', 8384))
        threading.Thread(target=tcp_client_receive, args=(tcp_socket, websocket)).start()
        return tcp_socket
    except Exception as e:
        print(f"Error connecting to TCP server: {e}")
        tcp_socket.close()
        return None


async def websocket_client_receive(websocket, tcp_socket):
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


async def start_websocket_client():
    while True:
        try:
            async with websockets.connect('ws://192.168.0.245:3000') as websocket:
                tcp_socket = start_tcp_client(websocket)
                if tcp_socket:
                    await websocket_client_receive(websocket, tcp_socket)
                else:
                    await asyncio.sleep(5)
        except Exception as e:
            print(f"Error connecting to WebSocket server: {e}")
        await asyncio.sleep(3)


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


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_websocket_client())
    loop.run_forever()


if __name__ == "__main__":
    main()
