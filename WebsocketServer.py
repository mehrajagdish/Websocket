import asyncio
import logging
import websockets

CLIENTS = set()
messages = asyncio.Queue()

# Configure logging
logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


async def handler(websocket):
    CLIENTS.add(websocket)
    logging.info(f"New client connected: {websocket.remote_address}")
    try:
        while True:
            message = await websocket.recv()
            logging.info(f"Received message: {message} from {websocket.remote_address}")
            messageMap = {"sender": websocket, "message": message}
            await messages.put(messageMap)
    except websockets.ConnectionClosed:
        logging.info(f"Client disconnected: {websocket.remote_address}")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    finally:
        CLIENTS.remove(websocket)
        logging.info(f"Client removed: {websocket.remote_address}")


async def broadcast(message):
    logging.info(f"Broadcasting to {len(CLIENTS)} clients")
    tasks = []
    for websocket in CLIENTS.copy():
        if message.get("sender") != websocket:
            tasks.append(websocket.send(message.get("message")))

    # Run all send operations concurrently
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Error during broadcast: {str(result)}")


async def broadcast_messages():
    while True:
        message = await messages.get()
        logging.info(f"Broadcasting message: {message.get('message')}")
        await broadcast(message)


async def main():
    server = await websockets.serve(handler, port=3000, ping_interval=30, ping_timeout=15)
    logging.info("Server started on port 3000")
    try:
        await broadcast_messages()
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
    finally:
        server.close()
        await server.wait_closed()
        logging.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
