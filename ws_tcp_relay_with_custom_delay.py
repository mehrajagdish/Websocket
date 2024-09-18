import asyncio
import json
import logging
import socket
import threading
import time
from asyncio import AbstractEventLoop

import websockets

from BowlingMachine import BowlingMachineResponse
from EventEnums import Events, Devices
from EventInfo import getEventInfoObject

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

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
    try:
        message = json.loads(message_from_tcp)
        if message["response"] == BowlingMachineResponse.BALLTRIGGERED.value:
            return True
    except Exception as e:
        logging.error("Trigger Received Error: ", e)
    return False


def send_feed_command_to_tcp():
    message = f"[F/{API_KEY}/3/]?"
    send_message_to_tcp(message)


def tcp_client_receive(websocket: websockets.WebSocketClientProtocol, loop: AbstractEventLoop):
    global last_trigger_time, tcp_socket, trying_to_reconnect, is_ws_connected
    try:
        while True:
            try:
                message = tcp_socket.recv(1024).decode('utf-8')
                if not message and not ping_tcp_client():
                    logging.info("TCP connection closed by server.")
                    break

                message = message.strip('"')
                if len(message.strip()) == 0:
                    logging.info("TCP: Empty message")
                    continue

                if trigger_received(message):
                    if time.time() - last_trigger_time >= TRIGGER_DELAY:
                        time.sleep(0.25)
                        send_feed_command_to_tcp()
                        message_to_be_sent = get_message_to_be_sent_to_websocket(message)
                        if message_to_be_sent:
                            asyncio.run_coroutine_threadsafe(send_message_to_websocket(websocket, message_to_be_sent),
                                                             loop)
                        last_trigger_time = time.time()
                    else:
                        logging.info(f"Skipping event, time difference: {time.time() - last_trigger_time}")
                else:
                    message_to_be_sent = get_message_to_be_sent_to_websocket(message)
                    if message_to_be_sent:
                        asyncio.run_coroutine_threadsafe(send_message_to_websocket(websocket, message_to_be_sent), loop)
            except socket.timeout:
                if not is_ws_connected:
                    logging.info("TCP Receive: Websocket connection closed")
                    break

                if not ping_tcp_client() and not trying_to_reconnect:
                    tcp_socket = handle_tcp_disconnection(websocket, loop)
            except socket.error as e:
                logging.error(f"TCP socket error: {e}")
                break

    except Exception as e:
        logging.error(f"TCP client receive error: {e}")
    finally:
        if tcp_socket:
            tcp_socket.close()
            tcp_socket = None
        if is_ws_connected and not trying_to_reconnect:
            tcp_socket = handle_tcp_disconnection(websocket, loop)


def handle_tcp_disconnection(websocket: websockets.WebSocketClientProtocol, loop: AbstractEventLoop):
    logging.info("Attempting to reconnect to TCP server...")
    global trying_to_reconnect, tcp_socket
    if trying_to_reconnect:
        return tcp_socket
    trying_to_reconnect = True
    while True:
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            tcp_socket.settimeout(TIMEOUT)
            tcp_socket.connect((TCP_IP, TCP_PORT))
            logging.info("Successfully reconnected to TCP server.")
            trying_to_reconnect = False
            threading.Thread(target=tcp_client_receive, args=(websocket, loop)).start()
            return tcp_socket
        except Exception as e:
            logging.error(f"Reconnection attempt failed: {e}")
            if tcp_socket:
                tcp_socket.close()
                tcp_socket = None
        time.sleep(3)


def send_message_to_tcp(message: str):
    global tcp_socket
    if tcp_socket:
        try:
            tcp_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            logging.error(f"Error sending message to TCP server: {e}")


def start_tcp_client(websocket: websockets.WebSocketClientProtocol, loop: AbstractEventLoop) -> socket.socket | None:
    global tcp_socket

    if tcp_socket:
        return tcp_socket

    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    tcp_socket.settimeout(TIMEOUT)
    try:
        tcp_socket.connect((TCP_IP, TCP_PORT))
        logging.info("Successfully connected to TCP server.")
        threading.Thread(target=tcp_client_receive, args=(websocket, loop)).start()
        return tcp_socket
    except Exception as e:
        logging.error(f"Error connecting to TCP server: {e}")
        tcp_socket.close()
        tcp_socket = None
        return None


def ping_tcp_client() -> bool:
    global ping_tcp_socket
    try:
        ping_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ping_tcp_socket.settimeout(5)
        ping_tcp_socket.connect((TCP_IP, TCP_PORT))
        ping_tcp_socket.close()
        return True
    except socket.error as e:
        logging.error(e)
        return False


def feed_command_received_from_websocket(message_from_websocket) -> bool:
    eventInfo = getEventInfoObject(message_from_websocket)

    if not eventInfo.header.bayInfo.isForAllBays and eventInfo.header.bayInfo.bayId != bayId:
        return False

    if Devices.BOWLING_MACHINE.value in eventInfo.header.sentTo:
        if Events.FEED_BOWLING_MACHINE.value == eventInfo.header.eventName:
            return True
    return False


async def handle_feed_command(websocket: websockets.WebSocketClientProtocol):
    message_to_be_sent = {
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
    await send_message_to_websocket(websocket, message_to_be_sent)


async def ping_ws_server(websocket: websockets.WebSocketClientProtocol):
    global is_ws_connected
    while is_ws_connected:
        try:
            # logging.info("Trying to ping websocket server.")
            await websocket.ping()
            # logging.info("pinged.")
            await asyncio.sleep(5)  # Non-blocking sleep

        except websockets.ConnectionClosedError:
            logging.error("WebSocket connection closed while pinging.")
            is_ws_connected = False
        except Exception as e:
            logging.error(f"Error pinging WebSocket server: {e}")
            is_ws_connected = False


async def websocket_client_receive(websocket: websockets.WebSocketClientProtocol):
    global tcp_socket, is_ws_connected
    try:
        async for message in websocket:
            message_to_be_sent = get_message_to_be_sent_to_tcp(message)
            if message_to_be_sent is not None:
                send_message_to_tcp(message_to_be_sent)
            if feed_command_received_from_websocket(message):
                await handle_feed_command(websocket)

    except Exception as e:
        logging.error(f"WebSocket client receive error: {e}")
    finally:
        await websocket.close()
        is_ws_connected = False


async def send_message_to_websocket(websocket: websockets.WebSocketClientProtocol, message: dict):
    global is_ws_connected
    try:
        await websocket.send(json.dumps(message))
    except Exception as e:
        is_ws_connected = False
        logging.error(f"Error sending message to WebSocket server: {e}")


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
    global tcp_socket, is_ws_connected
    while True:
        ping_task = None
        ws_task = None
        try:
            async with websockets.connect(WS_URL) as websocket:
                loop = asyncio.get_running_loop()
                logging.info("Successfully connected to WebSocket server.")
                is_ws_connected = True
                ping_task = asyncio.create_task(ping_ws_server(websocket))
                tcp_socket = await asyncio.to_thread(start_tcp_client, websocket, loop)
                if tcp_socket:
                    ws_task = asyncio.create_task(websocket_client_receive(websocket))
                else:
                    tcp_socket = await asyncio.to_thread(handle_tcp_disconnection, websocket, loop)
                if ws_task:
                    await ws_task
        except Exception as e:
            logging.error(f"Error connecting to WebSocket server: {e}")
            is_ws_connected = False
        if ping_task:
            await ping_task
            ping_task.cancel()
        if ws_task:
            ws_task.cancel()
        await asyncio.sleep(TIMEOUT)


def main():
    asyncio.run(start_websocket_client())


if __name__ == "__main__":
    main()
