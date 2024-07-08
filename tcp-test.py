import json
import socket


def tcp_client(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = (host, port)

    client_socket.connect(server_address)

    message = ""

    message = json.dumps(message)

    client_socket.send(message.encode('utf-8'))


tcp_client('localhost', 6789)
