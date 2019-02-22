#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 21 11:21:01 2019

"""

from threading import Thread
import socket
import queue
import message
import utils
import random
# import pickle 
import time

def main():
    """
     Read .libr file, get Meta Info and Generate player_id for out player (client).
     Contact Hub and get player list.
     Initiate connection with players and handshake.

    """
    
    meta_file = utils.Metainfo('file.libr')
    player_id = utils.generate_player_id() 
    listen_port = generate_port()
    max_connections = 30 
    generate_player(listen_port)
    host = socket.gethostname() # TODO Generate host names
    s = socket.socket()
    s.bind(host, port)
    s.listen()   
    q = queue.Queue(maxsize = 0) # Infinite queue
    
    hub_connect_send = Thread(handle = HubCommunication.communicate_with_hub(s, meta_file, player_id, listen_port), args(q,))
    hub_connect_send.setDaemon = True
    hub_connect_send.start()
    
    player_connect = Thread(PlayerCommunication.handshakes(self, s, listen_port, player_id, meta_file, hub_communication, max_connections), args(q,))
    hub_connect_send.setDaemon = True
    hub_connect_send.start()
    
    
def generate_port(): # Generates port and initiates player
    listen_port = random.randint(7000,8000)
    try:
        temp_conn = socket.socket()          
    except:
        generate_port()
    temp_conn.close()
    return listen_port
    
def generate_player(self, listen_port):      
    server_socket = socket.socket() # Create socket
    player_socket = server_socket.bind(('localhost', self.listen_port))
    player_socket.listen() # Act as a server          
            
class HubCommunication(object): 
    """
    Obtain hub's port and hub's ip along with file info hash form the metafile
    Establish a connection with the hub and obtain list of players
    """
    def __init__(self, s, meta_file, player_id, listen_port):
        self.hub_port = meta_file.get_hub_port() # Get hub's port
        self.hub_ip = meta_file.get_hub_ip() # Get hub's ip
        self.info_hash = meta_file.get_info_hash() # Info hash from the metafile
        self.player_id = player_id # My player id
        self.listen_port = listen_port # My listen port
        self.s = s
        self.hub_socket = s.create_connection(self.hub_ip, self.hub_port) # Create connection with the hub
        
    def communicate_with_hub(self):    
        hub_msg = message.HubNotifyMsg(self.info_hash, self.player_id, self.listen_port, 0x8000, 0x4000, 65255558, b'start').msg_encode()
        hub_socket.sendall(hub_msg) # Send message to the hub [Message contains info hash, player id and listen_port of the player]        
        while True:
            print('Waiting for hub-connection')
            hub, addr = s.accept()            
            receive_message = self.hub_socket.recv(1024)
            status, remain, hub_recv = message.ComMessage.msg_decode(hub_recv)
            players = hub_recv.players
            return(players)
            
    def hub_send(self, message):
        self.hub_socket.sendall(message)

class PlayerCommunication(object):
    """
    Handshake with every player in the list obtained from the hub.
    Initiate two threads.
    """
    def __init__(self, s, listen_port, player_id, meta_file, hub_communication, max_connections): # Maximum number of connections
        self.players = hub_communication.communicate_with_hub
        self.listen_port = listen_port
        self.player_id = player_id
        self.info_hash = meta_file.get_info_hash
        self.s = s
        
    def handshakes(self): # Handshake with others
        for player in self.players:
            id = player[b'id']
            port = player[b'port']
            player = socket.create_connection((id, port))
            handshake_send = message.HandshakeMsg(self.player_id,self.info_hash()).msg_encode()
            socket.sendall(handshake_send)
            received_message = s.recv(1024)
            print(received_message)
            while True:
                client_socket, addr =  s.accept()
                status, remain, objMsg = message.ComMessage.msg_decode(received_message)
                if objMsg.get_message_type == 'handshake': # Create two threads when mututal handshake happens
                    other_not_choked = True
                    handle_player_listen(s,client_socket, my_bitfield, other_player_choked).start()
                    handle_player_send(s,client_socket, my_bitfield, other_player_choked).start()
            
    def player_listen(self, my_bitfield, s): # Accept handshakes
        while True:
            msg = client_socket.recv(1024)
            status, remain, objMsg = message.ComMessage.msg_decode(msg)
            if nb_connections >> max_connections:
                  choke_send = message.ChokeMsg().msg_encode()
                  server_socket.sendall(choke_send)  
                  other_not_choked = False
            handle_player_listen(client_socket, q, my_bitfield, other_not_choked).start() # A listen thread
            handle_player_send(client_socket, q, my_bitfield, other_not_choked).start() # A send thread

    def handle_player_listen(self,client_socket, my_bitfield, other_player_choked): # Listen thread
        def handle():
            # TODO import books class for book management and bitfields
            other_bitfield = [] # Stores bitfield of other players
            already_received = [] 
            remain_received = [] # Stores remains of received book messages
            # TODO When get information from book class about bitfield, change bitfield to bytearray type from list object
            # TODO Similar for the list
            while True:
                try:
                    message = client_socket.recv(1)
                    time.sleep(10)
                    if message is not None:
                        status, remain, objMsg = message.ComMessage.msg_decode(message) 
                        
                        if objMsg.get_message_type == 'Unchoke' and nb_connections << max_connections:
                            unchoke_send = message.UnchokeMsg().msg_encode()
                            server_socket.sendall(unchoke_send)  
                            other_not_choked = True
                        elif objMsg.get_message_type == 'keep alive':  # Keep alive message
                            time.sleep(30)
                        elif objMsg.get_message_type == 'have': # If receive a have message from a player, update bitfield
                            have_book_index = objMsg.get_book_index()
                            # Update other_bitfield   
                        elif objMsg.get_message_type == 'choke':
                            other_not_choked = False
                        elif objMsg.get_message_type == 'bitfield':                            
                            other_bitfield = objMsg.get_bitfield() # Other player's bitfield
                            count = 0
                            count1 = 0
                            for i in range(len(my_bitfield)): # Interested
                                if my_bitfield[[i]] == 0 and other_bitfield[[i]] == 1: 
                                    interested_message = message.IntererestedMsg(i).msg_encode()
                                    client_socket.sendall(interested_message) 
                                elif other_bitfield[[i]] is 1:
                                    count += 1
                                    if my_bitfield[[i]] is 1:
                                        count1 += 1
                                if count == count1 and count != 0: # Not interested
                                    NotInterested_message = message.NotIntererestedMsg(i).msg_encode()
                                    client_socket.sendall(NotInterested_message)
                        if objMsg.get_message_type == 'book': # Book message
                            received_book_index = objMsg.get_book_index() # Index of the received book
                            for i in alread_received: # Check if this book has already been received
                                if received_book_index == already_received[[i]] and book[[i]] << ObjMsg.get_payload(): # If the previously received book had less length, update the book
                                    book[[i]]  = ObjMsg.get_payload()
                                else:
                                    remain_received[[i]] = remain
                            already_received[[received_book_index]] = 1
                    else:
                        print("Message is None", socket)
                        break
                except:
                    print("Client disconnected", socket)
                    break

        def handle_player_send(self,s,client_socket, my_bitfield, other_player_choked): # Send thread
            def handle():
                while True:
                    try:
                        message = client_socket.recv(1)
                        if message is not None: 
                            status, remain, objMsg = message.ComMessage.msg_decode(message) 
                            if objMsg.get_message_type == 'request' and other_not_choked == True: # Book request
                                requested_book_index = objMsg.get_book_index()
                                if bitfield[[requested_book_index]] == 1 and Other_not_choked == True:
                                    book_message = BookMsg(requested_book_index, book_payload).msg_encode()
                                    client_socket.sendall(book_message)  
                        else:
                            print("Message is None", socket)
                            break
                    except:
                        print("Client disconnected", socket)
                        break       
