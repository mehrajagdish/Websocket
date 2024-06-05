import socket


def tcp_client(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = (host, port)

    client_socket.connect(server_address)

    message = "Hi"

    client_socket.send(message.encode('utf-8'))


tcp_client('192.168.4.1', 8384)
