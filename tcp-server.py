import asyncio

clients = []


async def handle_tcp_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Connected with {addr}")
    clients.append(writer)

    try:
        while True:
            data = await reader.read(1024)
            message = data.decode('utf-8')
            if not message:
                break

            print(f"Received from {addr}: {message}")
            await broadcast_message(message, writer)
    except asyncio.CancelledError:
        print(f"Connection with {addr} closed.")
    finally:
        clients.remove(writer)
        writer.close()
        await writer.wait_closed()


async def broadcast_message(message, sender):
    for client in clients:
        if client != sender:
            client.write(message.encode('utf-8'))
            await client.drain()


async def start_tcp_server():
    server = await asyncio.start_server(handle_tcp_client, 'localhost', 6789, limit=2)
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()


def main():
    asyncio.run(start_tcp_server())


if __name__ == "__main__":
    main()
