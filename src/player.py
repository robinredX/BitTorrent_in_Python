from threading import Thread
import binascii
import socket
import queue
import os

import message
import utils


def main():
    #Read .libr file, get Meta Info and Generate player for out player (client).

    meta_file = utils.Metainfo('file.libr')
    player_id = utils.generate_player_id()

    q = queue.Queue()
    c = consumer(q)
    c.daemon = True
    c.start()
    listen_port = 7777
    player_listen(q, listen_port).start()

    #TODO Contact Hub for Players list and report peer_id & port

    hub_socket = socket.create_connection((meta_file.get_hub_ip(), meta_file.get_hub_port()))


    player_list = []

    #TODO connect and Handshake per player

    for player in player_list:
        ip = player[b'ip']
        port = player[b'port']

        s = socket.create_connection((ip, port))
        handle_player_listen(s, q, False).start()
        handle_player_send(s, q, False).start()


def player_listen(q, port):
    def handle():
        server_socket_no = port
        server_socket = socket.socket()
        server_socket.bind(('localhost', server_socket_no))
        server_socket.listen()

        while True:
            print("Waiting for connection")
            client_socket, addr = server_socket.accept()
            handle_player_listen(client_socket, q, True).start()
            handle_player_send(client_socket, q, True).start()

    t = Thread(target=handle)
    return t


def handle_player_listen(socket, q, receiver):
    def handle():
        print("Received connection", socket)

        if receiver:
            #TODO wait for handshake here (RECEIVING)
            pass

        while True:
            try:
                message = socket.recv(1)
                # Decode the message
                if message is not None:
                    # Handle different messages
                    if message == 'magic_move':
                        # q.put()
                        pass
                    else:
                        print(message)
                else:
                    print("Client disconnected", socket)
                    break
            except:
                print("Client disconnected", socket)
                break
        q.put()

    t = Thread(target=handle)
    return t


def handle_player_send(socket, q, receiver):
    def handle():
        print("Received connection", socket)

        if not receiver:
            #TODO Initiate handshake here (SENDER)
            pass

        while True:
            try:
                message = socket.recv(1)
                # Decode the message
                if message is not None:
                    # Handle different messages
                    if message == 'magic_move':
                        # q.put()
                        pass
                    else:
                        print(message)
                else:
                    print("Client disconnected", socket)
                    break
            except:
                print("Client disconnected", socket)
                break
        q.put()

    t = Thread(target=handle)
    return t


def consumer(q):
    def consume():
        while True:
            c, i, by = q.get()
            if c == "RENDER":
                d.render_clean()
            if c == "MOVE":
                d.move_value_right(i, by)
            if c == "ADD":
                d.add_value(i, by)

    t = Thread(target=consume)
    return t


if __name__== "__main__":
  main()
