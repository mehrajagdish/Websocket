import asyncio
import websockets

CLIENTS = set()
messages = asyncio.Queue()


async def handler(websocket):
    CLIENTS.add(websocket)
    try:
        while True:
            message = await websocket.recv()
            messageMap = {"sender": websocket, "message": message}
            await messages.put(messageMap)
    except websockets.ConnectionClosed:
        print("Client removed")
        CLIENTS.remove(websocket)


async def broadcast(message):
    for websocket in CLIENTS.copy():
        try:
            if message.get("sender") != websocket:
                await websocket.send(message.get("message"))
        except websockets.ConnectionClosed:
            pass


async def broadcast_messages():
    while True:
        message = await messages.get()
        await broadcast(message)


async def main():
    server = await websockets.serve(handler, "localhost", 3000)
    await asyncio.gather(server.wait_closed(), broadcast_messages())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutting down gracefully")
