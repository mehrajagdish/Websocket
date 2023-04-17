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
        await asyncio.sleep(1)
        message = await messages.get()
        await broadcast(message)


async def main():
    async with websockets.serve(handler, port=3000):
        await broadcast_messages()  # runs forever


if __name__ == "__main__":
    asyncio.run(main())
