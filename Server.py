import asyncio
import websockets
import GenerateRandomVelocity

async def handler(ws, path):
    connected_clients.append(ws)
    while True:
        data = await ws.recv()
        print(data)
        reply = GenerateRandomVelocity.get_random_velocity()
        for client in connected_clients:
            await client.send(reply)


if __name__ == "__main__":
    connected_clients = []
    start_server = websockets.serve(handler, port=3000)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
