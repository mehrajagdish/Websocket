import asyncio
import logging
import time
from datetime import datetime
import websockets
import pytz  # Import pytz for timezone handling

CLIENTS = set()
messages = asyncio.Queue()

# Configure logging with IST timezone
logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


# Function to handle individual client connection
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


# Function to broadcast messages to all clients
async def broadcast(message):
    start_time = time.time()  # Start time
    logging.info(f"Broadcasting to {len(CLIENTS)} clients")

    # Create a list of tasks for sending messages
    broadcast_tasks = []
    for websocket in CLIENTS.copy():
        if message.get("sender") != websocket:
            broadcast_tasks.append(send_message(websocket, message.get("message")))

    # Run tasks concurrently, handle errors without blocking other clients
    results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)

    # Log any errors encountered while broadcasting
    for websocket, result in zip(CLIENTS.copy(), results):
        if isinstance(result, Exception):
            logging.error(f"Failed to send message to {websocket.remote_address}: {str(result)}")

    end_time = time.time()  # End time
    total_time = end_time - start_time
    logging.info(f"Time taken to broadcast message: {total_time:.4f} seconds")


# Helper function to send message to a single client
async def send_message(websocket, message):
    try:
        await websocket.send(message)
    except websockets.ConnectionClosed:
        logging.warning(f"Failed to send message to {websocket.remote_address}: Connection closed")
    except Exception as e:
        logging.error(f"Failed to send message to {websocket.remote_address}: {str(e)}")


# Function to process messages from the queue and broadcast them
async def broadcast_messages():
    while True:
        message = await messages.get()
        logging.info(f"Processing message for broadcast: {message.get('message')}")
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
