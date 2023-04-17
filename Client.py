import websockets
import asyncio


# The main function that will handle connection and communication
# with the server
async def listen():
    url = "ws://localhost:3000"
    # Connect to the server
    async with websockets.connect(url) as ws:
        # Send a greeting message
        # Stay alive forever, listening to incoming msgs
        while True:
            await ws.send("Client")
            msg = await ws.recv()
            print(msg)
            # time.sleep(5)


# Start the connection
asyncio.get_event_loop().run_until_complete(listen())
