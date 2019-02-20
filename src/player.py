import socket
import queue
import message
from threading import Thread
import utils


def main():
    """
     Read .libr file, get Meta Info and Generate player_id for out player (client).
     Contact Hub and get player list.
     Initiate connection with players and handshake.

    """

    meta_file = utils.Metainfo('file.libr')
    player_id = utils.generate_player_id()


    listen_port = 7777
    my_details = dict()
    my_details['player_id'] = player_id
    my_details['player_ip'] = socket.gethostbyname(socket.gethostname())
    my_details['info_hash'] = meta_file.get_info_hash()
    my_details['player_port'] = listen_port
    my_details['stuff_size'] = meta_file.get_stuff_size()
    player_listen(my_details).start()
    
    # Contact hub and get list of players
    hub_socket = socket.create_connection((meta_file.get_hub_ip(), meta_file.get_hub_port()))
    hub_msg = message.HubNotifyMsg(meta_file.get_info_hash(), player_id, listen_port, 0x8000, 0x4000, 65255558, b'start')\
        .msg_encode()

    hub_socket.sendall(hub_msg)

    hub_recv = hub_socket.recv(1024)
    status, remain, hub_recv = message.ComMessage.msg_decode(hub_recv)

    players = hub_recv.players

    # Handshake with every player in the list received form the hub
    
    for player in players:
        ip = player[b'ip']
        port = player[b'port']

        s = socket.create_connection((ip, port))
        handshake_send = message.HandshakeMsg(my_details['player_id'],meta_file.get_info_hash()).msg_encode()
        s.sendall(handshake_send)
        received_message = s.recv(1024)
        print(received_message)
        status, remain, objMsg = message.ComMessage.msg_decode(received_message)
        if objMsg.code is 0x00: # Create two threads when mututal handshake happens
            handle_player_listen(s, False).start()
            handle_player_send(s, False).start()

# Players who connect with the player and handshake  
            
def player_listen(my_details):
    def handle():
        server_socket_no = my_details['player_port']
        server_socket = socket.socket()
        server_socket.bind(('localhost', server_socket_no))
        server_socket.listen()
        
        while True:
            print("Waiting for connection")
            client_socket, addr = server_socket.accept()
            msg = client_socket.recv(1024)
            status, remain, objMsg = message.ComMessage.msg_decode(msg)
            if objMsg.code is 0x00:
                  handshake_send = message.HandshakeMsg(my_details['player_ip'], my_details['info_hash']).msg_encode()
                  client_socket.sendall(handshake_send)
            handle_player_listen(client_socket, q, my_details).start()
            handle_player_send(client_socket, q, my_details).start()

    t = Thread(target=handle)
    return t


# listen thread
    
def handle_player_listen(socket, my_details):
    def handle(my_details):
        print("Received connection", socket)
        other_player_choked = False
        I_am_choked = False
        size = my_details['stuff_size']
        my_bitfield = [0]*size

        while True:
            try:
                message = socket.recv(1)
                                                  
                # Decode the message
                if message is not None:
                        status, remain, objMsg = message.ComMessage.msg_decode(message)                       
                        # Handle different messages
                        if objMsg.message_code is 0x00 and other_player_choked is False: # Choke
                            chokeResp = message.ComMessage.ChokeMsg()
                            socket.sendall(chokeResp)
                            I_am_choked = True       
                            
                        elif objMsg.message_code is 0x01 and other_player_choked is True: # Unchoke
                            UnchokeResp = message.ComMessage.UnchokeMsg()
                            socket.sendall(UnchokeResp)
                            I_am_choked = False
                            
                        elif objMsg.message_code is 0x05: # Bitfield
                            other_bitfield = hex(objMsg.get_bitfield())
                            for i in range(my_bitfield):
                                if my_bitfield[[i]] is 0 and other_bitfield[[i]] is 1: # TODO Apply algorithm here to select which index to request first
                                    request_message = message.ComMessage.RequestMsg(i).msg_encode()
                                    socket.sendall(request_message)    
                                    
                        # TODO Receive book message, and update bitfield
                        
                        # TODO send player invalid address to hub
                else:
                    print("Message is None", socket)
                    break
            except:
                print("Client disconnected", socket)
                break
        q.put()

    t = Thread(target=handle, args = [my_details])
    return t

# Send thread
    
def handle_player_send(socket, receiver):
    def handle():
        print("Received connection", socket)

        if not receiver:
            #TODO Initiate handshake here (SENDER)
            pass

        while True:
            try:
                message = socket.recv(1)
                #TODO Decode the message
                if message is not None:
                    #TODO Handle different messages
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


if __name__== "__main__":
  main()