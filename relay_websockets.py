import asyncio
import websockets

async def relay_messages():
    while True:
        try:
            async with websockets.connect('ws://192.168.48.169:3000') as source_ws:
                async with websockets.connect('ws://192.168.0.173:3000') as destination_ws:
                    print("Connected to both source and destination WebSocket servers.")
                    while True:
                        message = await source_ws.recv()
                        await destination_ws.send(message)
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}. Reconnecting...")
            await asyncio.sleep(5)  # Wait before reconnecting
        except Exception as e:
            print(f"An error occurred: {e}. Reconnecting...")
            await asyncio.sleep(5)  # Wait before reconnecting

asyncio.get_event_loop().run_until_complete(relay_messages())
