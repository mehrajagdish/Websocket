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
TIMEOUT = 10.0

tcp_socket: socket.socket | None = None
ping_tcp_socket: socket.socket | None = None
last_trigger_time = time.time()
trying_to_reconnect = False
is_ws_connected = False


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


def send_feed_command_to_tcp():
    message = f"[F/{API_KEY}/3/]?"
    send_message_to_tcp(message)


def tcp_client_receive(websocket: websockets.WebSocketClientProtocol, loop: AbstractEventLoop):
    global last_trigger_time, tcp_socket
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
                        send_feed_command_to_tcp()
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
                if not ping_tcp_client() and not trying_to_reconnect:
                    asyncio.run_coroutine_threadsafe(handle_tcp_disconnection(websocket), loop)
            except socket.error as e:
                print(f"TCP socket error: {e}")
                break

    except Exception as e:
        print(f"TCP client receive error: {e}")
    finally:
        if tcp_socket:
            tcp_socket.close()
        if is_ws_connected and not trying_to_reconnect:
            asyncio.run_coroutine_threadsafe(handle_tcp_disconnection(websocket), loop)


async def handle_tcp_disconnection(websocket: websockets.WebSocketClientProtocol):
    print("Attempting to reconnect to TCP server...")
    global trying_to_reconnect, tcp_socket

    trying_to_reconnect = True
    while True:
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            tcp_socket.settimeout(TIMEOUT)
            tcp_socket.connect((TCP_IP, TCP_PORT))
            # tcp_socket.settimeout(None)
            print("Successfully reconnected to TCP server.")
            trying_to_reconnect = False
            loop = asyncio.get_running_loop()
            threading.Thread(target=tcp_client_receive, args=(websocket, loop)).start()
            return
        except Exception as e:
            print(f"Reconnection attempt failed: {e}")
            if tcp_socket:
                tcp_socket.close()
        await asyncio.sleep(3)


def send_message_to_tcp(message: str):
    global tcp_socket
    if tcp_socket:
        try:
            print("Sending message to TCP server :" + message)
            tcp_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message to TCP server: {e}")


def start_tcp_client(websocket: websockets.WebSocketClientProtocol) -> socket.socket | None:
    global tcp_socket

    if tcp_socket:
        return

    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    tcp_socket.settimeout(TIMEOUT)
    try:
        tcp_socket.connect((TCP_IP, TCP_PORT))
        # tcp_socket.settimeout(None)
        print("Successfully connected to TCP server.")
        loop = asyncio.get_running_loop()
        threading.Thread(target=tcp_client_receive, args=(websocket, loop)).start()
        return tcp_socket
    except Exception as e:
        print(f"Error connecting to TCP server: {e}")
        tcp_socket.close()
        asyncio.run_coroutine_threadsafe(handle_tcp_disconnection(websocket), asyncio.get_running_loop())
        return None


def ping_tcp_client() -> bool:
    global ping_tcp_socket
    try:
        # Create a socket
        ping_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ping_tcp_socket.settimeout(5)
        ping_tcp_socket.connect((TCP_IP, TCP_PORT))
        ping_tcp_socket.close()
        return True
    except socket.error as e:
        return False


async def websocket_client_receive(websocket: websockets.WebSocketClientProtocol):
    global tcp_socket, is_ws_connected
    try:
        async for message in websocket:
            print(f"Received from WebSocket server: {message}")
            message_to_be_sent = get_message_to_be_sent_to_tcp(message)
            if message_to_be_sent is not None:
                send_message_to_tcp(message_to_be_sent)
    except Exception as e:
        print(f"WebSocket client receive error: {e}")
    finally:
        await websocket.close()
        is_ws_connected = False



async def send_message_to_websocket(websocket: websockets.WebSocketClientProtocol, message: dict):
    try:
        await websocket.send(json.dumps(message))
    except Exception as e:
        print(f"Error sending message to WebSocket server: {e}")


def get_message_to_be_sent_to_tcp(message_from_websocket: str) -> str | None:
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


def get_message_to_be_sent_to_websocket(message_from_tcp: str) -> dict | None:
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
    global tcp_socket
    global is_ws_connected
    while True:
        try:
            async with websockets.connect(WS_URL) as websocket:
                print("Successfully connected to WebSocket server.")
                tcp_socket = start_tcp_client(websocket)
                if tcp_socket:
                    await websocket_client_receive(websocket)
                else:
                    await handle_tcp_disconnection(websocket)
                is_ws_connected = True
        except Exception as e:
            print(f"Error connecting to WebSocket server: {e}")
            is_ws_connected = False
        await asyncio.sleep(TIMEOUT)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_websocket_client())
    loop.run_forever()


if __name__ == "__main__":
    main()
