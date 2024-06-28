import asyncio
import json
import socket
import threading

import websockets

from BowlingMachine import BowlingMachineResponse  # Assuming these imports are valid
from EventEnums import Events, Devices  # Assuming these imports are valid
from EventInfo import getEventInfoObject  # Assuming these imports are valid

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bayId"]
API_KEY = config["machineApiKey"]

tcp_socket = None


def tcp_client_receive(tcp_socket, websocket):
    try:
        while True:
            message = tcp_socket.recv(1024).decode('utf-8')
            if not message:
                print("TCP connection closed by server.")
                break
            asyncio.run(send_message_to_websocket(websocket, message))
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
            send_message_to_tcp(tcp_socket, message)
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
