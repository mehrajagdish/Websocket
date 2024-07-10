import asyncio
import json
import socket
import threading
import time
from asyncio import AbstractEventLoop

import websockets

from BowlingMachine import BowlingMachineResponse
from EventEnums import Events, Devices
from EventInfo import getEventInfoObject

CONFIG_PATH = "./config.json"
with open(CONFIG_PATH) as fp:
    config = json.load(fp)

bayId = config["bayId"]
API_KEY = config["machineApiKey"]
TRIGGER_DELAY = config["triggerDelay"]
WS_URL = config["websocketServerURI"]
TCP_IP = config["tcpIP"]
TCP_PORT = config["tcpPort"]
TIMEOUT = 3.0

tcp_socket = None
last_trigger_time = time.time()


def trigger_received(message_from_tcp: str) -> bool:
    print("Checking if trigger received")
    try:
        message = json.loads(message_from_tcp)
        if message["response"] == BowlingMachineResponse.BALLTRIGGERED.value:
            print("Trigger Received")
            return True
        print("Trigger Not Received")
    except Exception as e:
        print(e)
    return False


def send_feed_command_to_tcp(tcp_socket: socket.socket):
    message = f"[F/{API_KEY}/3/]?"
    send_message_to_tcp(tcp_socket, message)


def tcp_client_receive(tcp_socket: socket.socket, websocket: websockets.WebSocketClientProtocol,
                       loop: AbstractEventLoop):
    global last_trigger_time
    try:
        while True:
            try:
                message = tcp_socket.recv(1024).decode('utf-8')
                print("TCP Client Received: ", message)
                if not message:
                    print("TCP connection closed by server.")
                    break

                message = message.strip('"')
                if len(message.strip()) == 0:
                    print("TCP: Empty message")
                    continue

                if trigger_received(message):
                    if time.time() - last_trigger_time >= TRIGGER_DELAY:
                        time.sleep(0.25)
                        send_feed_command_to_tcp(tcp_socket)
                        message_to_be_sent = get_message_to_be_sent_to_websocket(message)
                        if message_to_be_sent:
                            asyncio.run_coroutine_threadsafe(
                                send_message_to_websocket(websocket, message_to_be_sent), loop
                            )
                        last_trigger_time = time.time()
                    else:
                        print("Skipping event, time difference: ", time.time() - last_trigger_time)
                else:
                    message_to_be_sent = get_message_to_be_sent_to_websocket(message)
                    if message_to_be_sent:
                        asyncio.run_coroutine_threadsafe(
                            send_message_to_websocket(websocket, message_to_be_sent), loop
                        )
            except socket.timeout:
                print("TCP socket timeout")
            except socket.error as e:
                print(f"TCP socket error: {e}")
                break

    except Exception as e:
        print(f"TCP client receive error: {e}")
    finally:
        if tcp_socket:
            tcp_socket.close()
        asyncio.run_coroutine_threadsafe(handle_tcp_disconnection(websocket), loop)


async def handle_tcp_disconnection(websocket: websockets.WebSocketClientProtocol):
    print("Attempting to reconnect to TCP server...")
    global tcp_socket
    while True:
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.settimeout(TIMEOUT)
            tcp_socket.connect((TCP_IP, TCP_PORT))
            print("Successfully reconnected to TCP server.")
            loop = asyncio.get_running_loop()
            threading.Thread(target=tcp_client_receive, args=(tcp_socket, websocket, loop)).start()
            return
        except Exception as e:
            print(f"Reconnection attempt failed: {e}")
            if tcp_socket:
                tcp_socket.close()
        await asyncio.sleep(3)


def send_message_to_tcp(tcp_socket: socket.socket, message: str):
    if tcp_socket:
        try:
            print("Sending message to TCP server :" + message)
            tcp_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message to TCP server: {e}")


def start_tcp_client(websocket: websockets.WebSocketClientProtocol) -> socket.socket:
    global tcp_socket
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.settimeout(TIMEOUT)
    try:
        tcp_socket.connect((TCP_IP, TCP_PORT))
        print("Successfully connected to TCP server.")
        loop = asyncio.get_running_loop()
        threading.Thread(target=tcp_client_receive, args=(tcp_socket, websocket, loop)).start()
        return tcp_socket
    except Exception as e:
        print(f"Error connecting to TCP server: {e}")
        tcp_socket.close()
        asyncio.run_coroutine_threadsafe(handle_tcp_disconnection(websocket), asyncio.get_running_loop())
        return None


async def websocket_client_receive(websocket: websockets.WebSocketClientProtocol):
    global tcp_socket
    try:
        async for message in websocket:
            print(f"Received from WebSocket server: {message}")
            message_to_be_sent = get_message_to_be_sent_to_tcp(message)
            if message_to_be_sent is not None:
                send_message_to_tcp(tcp_socket, message_to_be_sent)
    except Exception as e:
        print(f"WebSocket client receive error: {e}")
    finally:
        await websocket.close()


async def send_message_to_websocket(websocket: websockets.WebSocketClientProtocol, message: dict):
    try:
        await websocket.send(json.dumps(message))
    except Exception as e:
        print(f"Error sending message to WebSocket server: {e}")


def get_message_to_be_sent_to_tcp(message_from_websocket: str) -> str:
    eventInfo = getEventInfoObject(message_from_websocket)

    if not eventInfo.header.bayInfo.isForAllBays and eventInfo.header.bayInfo.bayId != bayId:
        return None

    if Devices.BOWLING_MACHINE.value in eventInfo.header.sentTo:
        if Events.BOWLING_MACHINE_STATUS.value == eventInfo.header.eventName:
            return f"[S/{API_KEY}/]?"
        elif Events.SET_BOWLING_MACHINE_PARAMETERS.value == eventInfo.header.eventName:
            return (f"[A/{API_KEY}/{eventInfo.data.value.speed}"
                    f"/{eventInfo.data.value.mode}/{eventInfo.data.value.swing}/]?")
        elif Events.FEED_BOWLING_MACHINE.value == eventInfo.header.eventName:
            return f"[F/{API_KEY}/3/]?"
    return None


def get_message_to_be_sent_to_websocket(message_from_tcp: str) -> dict:
    message = json.loads(message_from_tcp)
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
            async with websockets.connect(WS_URL) as websocket:
                print("Successfully connected to WebSocket server.")
                tcp_socket = start_tcp_client(websocket)
                if tcp_socket:
                    await websocket_client_receive(websocket)
                else:
                    await handle_tcp_disconnection(websocket)
        except Exception as e:
            print(f"Error connecting to WebSocket server: {e}")
        await asyncio.sleep(TIMEOUT)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_websocket_client())
    loop.run_forever()


if __name__ == "__main__":
    main()
