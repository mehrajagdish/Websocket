import asyncio
import logging
import time
from datetime import datetime
import websockets
import pytz  # Import pytz for timezone handling

CLIENTS = set()
messages = asyncio.Queue()

# Set IST timezone
IST = pytz.timezone('Asia/Kolkata')


class ISTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=IST)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            s = dt.isoformat()
        return s


# Configure logging with IST timezone
logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Update the logging formatter to use IST
for handler in logging.root.handlers:
    handler.setFormatter(ISTFormatter(handler.formatter._fmt, handler.formatter.datefmt))


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
    for websocket in CLIENTS.copy():
        try:
            if message.get("sender") != websocket:
                await websocket.send(message.get("message"))
        except websockets.ConnectionClosed:
            logging.warning(f"Failed to send message to {websocket.remote_address}: Connection closed")
        except Exception as e:
            logging.error(f"Failed to send message to {websocket.remote_address}: {str(e)}")

    end_time = time.time()  # End time
    total_time = end_time - start_time
    logging.info(f"Time taken to broadcast message: {total_time:.4f} seconds")


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
