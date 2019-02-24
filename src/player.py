#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 21 11:21:01 2019
"""

from threading import Thread
import socket
import sys,os
import queue
import message
import utils
import random
# import pickle 
import time
#import netifaces as ni
from books import Books
from hashlib import sha1
from enum import Enum


STATE_INIT = 0
STATE_UPDATE = 1
STATE_INTERESTED = 2
STATE_REQUEST = 3
STATE_CONFIRM_WRITE = 4
STATE_HUB_RECONNECT = 5
STATE_HUB_DISCONNECTED = 6
STATE_WAIT_QUEUE = 10


class PlayerQMsgEnum(Enum):
    QUEUE_MSG_CONNECT_PLAYERS = 0
    QUEUE_MSG_INTERESTED = 1
    QUEUE_MSG_BITFIELD = 2
    QUEUE_MSG_BITFIELD_REGISTER = 3
    QUEUE_MSG_REQUEST = 4
    QUEUE_MSG_BOOK_RECEIVED = 5
    QUEUE_MSG_PAYLOAD_READ = 6
    QUEUE_MSG_PAYLOAD_WRITE = 7
    QUEUE_MSG_REGISTER_HUB_QUEUE = 8
    QUEUE_MSG_NOTIFY_HUB_PLAYER_DEAD = 9
    QUEUE_MSG_REINIT_HUB_CNX = 10
    
    
    
    
    
    
def main(root_dir, meta_file_path, player_id):
    """
     Read .libr file, get Meta Info and Generate player_id for out player (client).
     Contact Hub and get player list.
     Initiate connection with players and handshake.
    """
    meta_file = utils.Metainfo(meta_file_path)
    book_list = []
    if player_id is None :
        print('Create player id')
        player_id = utils.generate_player_id() 
    print(meta_file.get_file_name())
        
    print(player_id.decode("utf-8"))
    if os.path.exists(root_dir):
        player_dir = root_dir+'\\'+player_id.decode("utf-8")
        if not os.path.exists(player_dir):
            os.mkdir(player_dir)            
        list_file = os.listdir(player_dir)
        
        if len(list_file) > 0 :            
            for file in list_file:
                book_list.append(Books(player_dir+'\\'+file, meta_file))
        else:
            print('Create new stuff')
            book_list.append(Books(player_dir+'\\'+meta_file.get_file_name(), meta_file))
            
    print(book_list[0].get_bitfield())
    
    # get the ip address
    #interface_id = ni.gateways()['default'][2][1]
    #print(ni.interfaces())
    #ip = ni.ifaddresses(interface_id)[2][0]['addr']

    ip = 'localhost'
    listening_port = random.randint(7000, 8000)
    count = 0    
    
    while True:
        try:      
            player_cnx = PlayerConnectionManager(player_id, ip, listening_port, meta_file, book_list[0])
            player_manager_queue = player_cnx.get_player_manager_queue()
            break
        except:
            count += 1
            listening_port = random.randint(7000,8000)
            if count > 50:
                print('Client: can not get a connection port. Terminate.')
                sys.exit(-1)
                break    
    
    count = 0
    
    while True :
        try :
            HubCommunication(meta_file, player_id, listening_port, book_list[0], player_manager_queue)
            print('Player ' + str(player_id) + ' connected to hub')
            break
        except:            
            count += 1
            print('Connection to hub attemp ' + str(count) + ' fail.')
            #time.sleep(5)
            if count > 5:
                print('Can not connect to the hub. Terminate.')
                sys.exit(-1)
                break
    
    # hub_connect_send = Thread(handle = HubCommunication.communicate_with_hub(s, meta_file, player_id, listen_port), args(q,))
    # hub_connect_send.setDaemon = True
    # hub_connect_send.start()
    
    # player_connect = Thread(PlayerCommunication.handshakes(self, s, listen_port, player_id, meta_file, max_connections), args(q,))
    # hub_connect_send.setDaemon = True
    # hub_connect_send.start()
    
    
  
         
class HubCommunication(object): 
    """
    Obtain hub's port and hub's ip along with file info hash form the metafile
    Establish a connection with the hub and obtain list of players
    """
    def __init__(self, meta_file, player_id, listening_port, book, manager_queue):
        self.hub_port = meta_file.get_hub_port() # Get hub's port
        self.hub_ip = meta_file.get_hub_ip() # Get hub's ip
        
        self.hub_port = 8001
        self.hub_ip = 'localhost'     
        
        self.info_hash = meta_file.get_info_hash() # Info hash from the metafile
        self.meta_file = meta_file
        self.player_id = player_id # My player id
        self.listening_port = listening_port # My listen port
        self.book = book
        
        self.manager_q = manager_queue
        self.hub_q = queue.Queue()
        self.hub_interval = 0
        self.hub_min_interval = 0
        self.hub_cnx_status = 'NOT_CONNECTED'
        
        self.hub_socket = socket.create_connection((self.hub_ip, self.hub_port)) # Create connection with the hub
        print('Start connection with hub')
        self.hub_send().start()
        self.hub_listening().start()
        self.register_hub_queue_with_player_manager()
        
    def get_hub_queue(self):
        return self.hub_queue    
        
    def register_hub_queue_with_player_manager(self):
        self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_REGISTER_HUB_QUEUE, self.hub_q))
        
    def hub_send(self):         
        def client():
            state = STATE_INIT
            while(True):
                if state == STATE_INIT:
                    file_size = self.meta_file.get_stuff_size()
                    book_size = self.meta_file.get_book_length()
                    left = self.meta_file.get_stuff_size() - self.book.get_downloaded_stuff_size()
                    print(self.meta_file.get_stuff_size())
                    print(self.book.get_downloaded_stuff_size())
                    print(left)                   
                    
                    print('Left to download ' + str(left))
                    msg = message.HubNotifyMsg(
                                self.meta_file.get_info_hash(),
                                self.player_id,
                                self.listening_port,
                                self.book.get_downloaded_stuff_size(),
                                0,
                                left,
                                b'start').msg_encode()                      
 
                    try:
                        self.hub_socket.sendall(msg)
                        print('Player ' + str(self.player_id) + ' sent notification to hub')
                        state = STATE_WAIT_QUEUE
                    except:
                        state = STATE_HUB_RECONNECT
                        print('The hub is disconnected')
                        self.hub_q.put((PlayerQMsgEnum.QUEUE_MSG_REINIT_HUB_CNX, STATE_INIT))                       
                    
                elif state == STATE_HUB_RECONNECT :
                    try:
                        self.hub_socket = socket.create_connection((self.hub_ip, self.hub_port)) # Create connection with the hub
                        self.hub_listening().start()
                        state = STATE_WAIT_QUEUE                        
                    except:
                        print('Cannot connect to hub')
                        

                    
                elif state == STATE_WAIT_QUEUE :
                    qmsg_id, info = self.hub_q.get()
                    # a list of dead players is received
                    if qmsg_id.value == PlayerQMsgEnum.QUEUE_MSG_NOTIFY_HUB_PLAYER_DEAD.value:
                        list_players = []
                        print('Dead player ' + str(info))
                        for player in info:
                           list_players.append(player['ip']+b'/'+str(player['port']).encode())
                        print(list_players)   
                        if len(list_players):
                            msg = message.PlayerInvalidAddrMsg(list_players).msg_encode()
                            try:
                                self.hub_socket.sendall(msg)
                            except:    
                                state = STATE_HUB_RECONNECT
                                print('The hub is disconnected')
                                #resend info in the queue to deal with after hub reconnection
                                self.hub_q.put((qmsg_id, info))
                                
                    elif qmsg_id.value == PlayerQMsgEnum.QUEUE_MSG_REINIT_HUB_CNX.value:
                        state = info
                    
        t = Thread(target=client)
        return t   
        
    def hub_listening(self):
        def client():
            remain = b''
            while True:
                try:
                    msg = utils.read_socket_buffer(self.hub_socket)
                except:
                    print('Hub is disconnected')
                    self.hub_cnx_status = 'NOT_CONNECTED'
                    break
                if msg != b'':
                    #print(msg)
                    #print('got sth')
                    full_msg = remain + msg
                    status, remain, objMsg = message.ComMessage.msg_decode(full_msg)  
                    if status == 0:
                        print('Player ' + str(self.player_id) + ' receive answer from hub')                   
                        if objMsg.get_message_type() == 'hub answer':
                            err_msg = objMsg.get_error()
                            warn_msg = objMsg.get_warning()
                            self.hub_interval = objMsg.get_interval()
                            self.hub_min_interval = objMsg.get_interval_min()
                            nb_seeder = objMsg.get_complete()                    
                            nb_leecher = objMsg.get_incomplete()                        
                            list_players = objMsg.get_players()
                            if len(list_players):
                                #send list of players to the Player manager
                                print('List_player' + str(list_players))
                                self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_CONNECT_PLAYERS,list_players))
                            else:
                                print('Player ' + str(self.player_id) + 'no player to connect to')

        t = Thread(target=client)
        return t  
        
        
        
class PlayerConnectionManager(object):
    """ Manage the listening port and accept connection from other players
    Initiate communication with other player from the hub list
    """
    def __init__(self, player_id, ip, listening_port, meta_file, book):
        self.player_id = player_id
        self.listening_port = listening_port
        self.meta_file = meta_file
        self.book = book
        self.server_socket = socket.socket()
        self.server_socket.bind((ip, listening_port))       
        self.server_socket.listen()    
        print('Player ' + str(self.player_id) + ' listening ' + str(ip) + ':' + str(listening_port))
        self.q = queue.Queue()
        self.hub_q = None
        self.players_info = {}
        self.connect_players().start()
        self.player_waiting_connection().start()
        self.manage_player_request().start()
        
    def get_player_manager_queue(self):
        return self.q

    def player_waiting_connection(self):
        """ Waiting for new client to connect to the listening port
        """
        def client():
            print('Waiting for client connection')
            while True:       
                client_socket, addr = self.server_socket.accept()   
                print("Received connection", client_socket)            
                client = PlayerCommunicationServer(self.player_id, self.book, client_socket, addr, self.meta_file, 50)

        t = Thread(target=client)
        return t           

    def manage_player_request(self):
        """ Waiting for new client to connect to the listening port
        """
        def handle():
            while True:
                self.make_request()
                time.sleep(5)

        t = Thread(target=handle)
        return t

    def is_existing_player(self, player):
        key = player['player_id']
        if key in self.players_info.keys():
            if self.players_info[key]['ip'] == player['ip'] and self.players_info[key]['port'] == player['port']:
                return True
            else:
                return False
        else:
            return False

    def connect_players(self):
        def queue_consumer():
            while True:
                q_msg_id, info = self.q.get()
                
                if q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_REGISTER_HUB_QUEUE.value:
                    print('Hub has registered its queue')
                    self.hub_q = info
                                
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_CONNECT_PLAYERS.value:
                    print('Manager receive queue message to connect players' + str(q_msg_id))               
                    list_player = info
                    if len(list_player):
                        dead_player_list = []
                        for player in list_player:
                            if self.is_existing_player(player):
                                print('Existing player ' + str(player['player_id']))
                                existing_player = self.players_info[player['player_id']]['player_com']
                            else:
                                print('Try to connect to player ' + str(player['player_id']))
                                self.players_info[player['player_id']] = {'bitfield':None, 'status':'NOT_CONNECTED','book_request':None, 'delay':[]}

                                try:
                                    new_player = PlayerCommunicationClient(self.player_id,
                                                                           player['ip'],
                                                                           player['port'], player['player_id'],
                                                                           self.meta_file,
                                                                           self.q,
                                                                           self.book,
                                                                           30)

                                    self.players_info[player['player_id']]['ip'] = player['ip']
                                    self.players_info[player['player_id']]['port'] = player['port']
                                    self.players_info[player['player_id']]['seeder'] = player['complete']
                                    self.players_info[player['player_id']]['player_com'] = new_player
                                except:
                                    print('Player cannot connect to player server ' + str(player['player_id']))
                                    dead_player_list.append(player)
                                    
                        if len(dead_player_list):                       
                            if self.hub_q is not None:
                                self.hub_q.put((PlayerQMsgEnum.QUEUE_MSG_NOTIFY_HUB_PLAYER_DEAD, dead_player_list))
                                    
                                    
                    else:
                        print('No players in the list')


                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_BITFIELD_REGISTER.value:
                    print('Manager received bitfield to register')
                    client_player_id, bitfield = info
                    #print(client_player_id)
                    #print(self.players_info)
                    self.players_info[client_player_id]['bitfield'] = bitfield
                    if self.players_info[client_player_id]['status'] == 'NOT_CONNECTED':
                        self.players_info[client_player_id]['status'] = 'STANDBY'

                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_BOOK_RECEIVED.value:
                    client_player_id, book_index, delay = info
                    print('Manager receive confirmation of book ' + str(book_index) + ' from player ' + str(client_player_id))


                    if client_player_id in self.players_info.keys():
                        if self.players_info[client_player_id]['book_request'] == book_index:
                            self.players_info[client_player_id]['delay'].append(delay)
                            if len(self.players_info[client_player_id]['delay']) > 10:
                                self.players_info[client_player_id]['delay'].pop(0)
                            self.players_info[client_player_id]['book_request'] = None
                            self.players_info[client_player_id]['status'] = 'STANDBY'

        t = Thread(target=queue_consumer)
        return t 
    
    def get_active_player_number(self):
        nb_active = 0
        for player_id in self.players_info.keys():            
            if self.players_info[player_id]['status'] == 'ACTIVE':
                nb_active += 1
        return nb_active

    def get_standby_player_number(self):
        nb_standby = 0
        for player_id in self.players_info.keys():
            if self.players_info[player_id]['status'] == 'STANDBY':
                nb_standby += 1
        return nb_standby

    def check_book_not_requested(self, book_index):
        is_requested = True
        for player_id in self.players_info.keys():            
            if self.players_info[player_id]['status'] == 'ACTIVE':
                if self.players_info[player_id]['book_request'] == book_index:
                    is_requested = False
        return is_requested        
        
    def make_request(self):
        #print(self.players_info)
        nb_active_players = self.get_active_player_number()
        #print('There are '+ str(nb_active_players) + ' active players')
        loop = 0
        while nb_active_players < 4 and self.get_standby_player_number():
            #print('Loop ' + str(loop))
            book_count = {}
            for player_id in self.players_info.keys():
                if self.players_info[player_id]['status'] == 'STANDBY':
                    self.players_info[player_id]['missing_book'] = self.book.match_bitfield(self.players_info[player_id]['bitfield'])
            
            #get the count of book presence amoung the different players
            for player_id in self.players_info.keys():
                if self.players_info[player_id]['status'] == 'STANDBY':
                    for book_no in self.players_info[player_id]['missing_book']:    
                        if book_no in book_count.keys():
                            book_count[book_no] += 1
                        else:
                            book_count[book_no] = 1
            
            #get the list of book_index by increasing frequence number among the other players
            freq_key=[]            
            for key, value in sorted(book_count.items(), key=lambda item: (item[1], item[0])):
                freq_key.append(key)          
            
            
            #freq_key.reverse()

            if len(freq_key):
                for book_index in freq_key:

                    list_book_owner = []
                    if self.check_book_not_requested(book_index) == True:
                        #print('the book is available')
                        for player_id in self.players_info.keys():            
                            if self.players_info[player_id]['status'] == 'STANDBY':
                                if book_index in self.players_info[player_id]['missing_book']:
                                    list_book_owner.append(player_id)
                        if len(list_book_owner):         
                            break
                            
                if len(list_book_owner):
                    print('Book index: ' + str(book_index) + ' has players')
                    picked_player_id = random.choice(list_book_owner)               
                    print('Manager send request to player')    
                    self.players_info[picked_player_id]['player_com'].get_client_queue().put((PlayerQMsgEnum.QUEUE_MSG_REQUEST, book_index))
                    self.players_info[picked_player_id]['book_request'] = book_index
                    self.players_info[picked_player_id]['status'] = 'ACTIVE'
                else:
                    #print('No more players available')
                    break
            else :
                # There are no book to fetch
                #print('No book to fetch')
                break
                
            nb_active_players = self.get_active_player_number()
            print('There are '+ str(nb_active_players) + ' active players')
            loop += 1
        #print('Exit make request')


class PlayerCommunicationClient(object):
    """
    Manage communication with one player server.
    Initiate two threads to listen and send to the  player server.
    """
    def __init__(self, player_id, client_ip, client_listening_port, client_player_id, meta_file, manager_queue, book, max_connections): # Maximum number of connections
       
        self.client_listening_port = client_listening_port
        self.client_player_id = client_player_id
        self.client_ip = client_ip
        self.player_id = player_id
        self.meta_file = meta_file
        self.book = book
        self.manager_queue = manager_queue
        self.info_hash = meta_file.get_info_hash()
        self.q = queue.Queue() 
        self.client_bitfield = None
        self.client_socket = socket.create_connection((self.client_ip, self.client_listening_port))
        self.handle_client_listen().start()
        self.handle_client_send().start()
        self.requested_book = None
        self.request_time = 0
        self.reception_delay = 0
        
    def get_client_queue(self):
        return self.q 
        
    def handle_client_listen(self):
        def client():
            remain = b''
            while True:
                msg = utils.read_socket_buffer(self.client_socket)
                if msg != b'':
                    full_msg = remain + msg
                    #print(full_msg)                    
                    status, remain, objMsg = message.ComMessage.msg_decode(full_msg)  
                    if status == 0:                                         
                        if objMsg.get_message_type() == 'bitfield':
                            print('Got bitfield message')
                            self.client_bitfield = objMsg.get_bitfield()
                            self.manager_queue.put((PlayerQMsgEnum.QUEUE_MSG_BITFIELD_REGISTER, (self.client_player_id, self.client_bitfield)))

                        if objMsg.get_message_type() == 'book':    
                            print('receive book message')
                            if objMsg.get_book_index() == self.requested_book:
                                payload = objMsg.get_payload()
                                if self.meta_file.get_book_hash(self.requested_book) == sha1(payload).digest():
                                    self.reception_delay = time.time()-self.request_time
                                    print('Book received in ', self.reception_delay)
                                    print('Book signature is correct')
                                    self.book.queue_write(self.requested_book, payload, (self.q, PlayerQMsgEnum.QUEUE_MSG_PAYLOAD_WRITE))

                                else:
                                    print('Book signature mismatch')
                            else:
                                print('This was not what book index I requested')
                            
        t = Thread(target=client)
        return t          
  
        
    def handle_client_send(self):
        def client():
            state = STATE_INIT

            while True:
                if state == STATE_INIT:
                    handshake_send = message.HandshakeMsg(self.player_id,self.meta_file.get_info_hash()).msg_encode()
                    self.client_socket.sendall(handshake_send)
                    print('Send handshake')
                    state = STATE_WAIT_QUEUE

                elif state == STATE_INTERESTED:
                    pass

                elif state == STATE_REQUEST:
                    print('A request from manager has been received')
                    if self.requested_book is not None:
                        self.requested_book = self.requested_book
                        request_send = message.RequestMsg(self.requested_book).msg_encode()
                        self.client_socket.sendall(request_send)
                        self.request_time = time.time()
                        state = STATE_WAIT_QUEUE

                elif state == STATE_CONFIRM_WRITE:
                    self.manager_queue.put((PlayerQMsgEnum.QUEUE_MSG_BOOK_RECEIVED, (self.client_player_id, self.requested_book, self.reception_delay)))
                    print('Confirm to manager writing of book ' + str(self.requested_book))
                    self.request_time = 0
                    self.reception_delay = 0
                    self.requested_book = None
                    state = STATE_WAIT_QUEUE

                elif state == STATE_WAIT_QUEUE:
                    q_msg_id, info = self.q.get()

                    if q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_REQUEST.value:
                        state = STATE_REQUEST
                        self.requested_book = info
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_PAYLOAD_WRITE.value:
                        state = STATE_CONFIRM_WRITE
                        
        t = Thread(target=client)
        return t  
        
    # def handshakes(self): # Handshake with others
        # for player in self.players:
            # player = socket.create_connection((self.client_ip, self.client_port))
            # handshake_send = message.HandshakeMsg(self.player_id,self.info_hash).msg_encode()
            # socket.sendall(handshake_send)
            # received_message = s.recv(1024)
            # print(received_message)
            # while True:
                # client_socket, addr =  s.accept()
                # status, remain, objMsg = message.ComMessage.msg_decode(received_message)
                # if objMsg.get_message_type == 'handshake': # Create two threads when mututal handshake happens
                    # other_not_choked = True
                    # handle_player_listen(s,client_socket, my_bitfield, other_player_choked).start()
                    # handle_player_send(s,client_socket, my_bitfield, other_player_choked).start()
            
    # def player_listen(self, my_bitfield, s): # Accept handshakes
        # while True:
            # msg = client_socket.recv(1024)
            # status, remain, objMsg = message.ComMessage.msg_decode(msg)
            # if nb_connections >> max_connections:
                  # choke_send = message.ChokeMsg().msg_encode()
                  # server_socket.sendall(choke_send)  
                  # other_not_choked = False
            # handle_player_listen(client_socket, q, my_bitfield, other_not_choked).start() # A listen thread
            # handle_player_send(client_socket, q, my_bitfield, other_not_choked).start() # A send thread

    # def handle_player_listen(self,client_socket, my_bitfield, other_player_choked): # Listen thread
        # def handle():
            # # TODO import books class for book management and bitfields
            # other_bitfield = [] # Stores bitfield of other players
            # already_received = [] 
            # remain_received = [] # Stores remains of received book messages
            # # TODO When get information from book class about bitfield, change bitfield to bytearray type from list object
            # # TODO Similar for the list
            # while True:
                # try:
                    # message = client_socket.recv(1)
                    # time.sleep(10)
                    # if message is not None:
                        # status, remain, objMsg = message.ComMessage.msg_decode(message) 
                        
                        # if objMsg.get_message_type == 'Unchoke' and nb_connections << max_connections:
                            # unchoke_send = message.UnchokeMsg().msg_encode()
                            # server_socket.sendall(unchoke_send)  
                            # other_not_choked = True
                        # elif objMsg.get_message_type == 'keep alive':  # Keep alive message
                            # time.sleep(30)
                        # elif objMsg.get_message_type == 'have': # If receive a have message from a player, update bitfield
                            # have_book_index = objMsg.get_book_index()
                            # # Update other_bitfield   
                        # elif objMsg.get_message_type == 'choke':
                            # other_not_choked = False
                        # elif objMsg.get_message_type == 'bitfield':                            
                            # other_bitfield = objMsg.get_bitfield() # Other player's bitfield
                            # count = 0
                            # count1 = 0
                            # for i in range(len(my_bitfield)): # Interested
                                # if my_bitfield[[i]] == 0 and other_bitfield[[i]] == 1: 
                                    # interested_message = message.IntererestedMsg(i).msg_encode()
                                    # client_socket.sendall(interested_message) 
                                # elif other_bitfield[[i]] is 1:
                                    # count += 1
                                    # if my_bitfield[[i]] is 1:
                                        # count1 += 1
                                # if count == count1 and count != 0: # Not interested
                                    # NotInterested_message = message.NotIntererestedMsg(i).msg_encode()
                                    # client_socket.sendall(NotInterested_message)
                        # if objMsg.get_message_type == 'book': # Book message
                            # received_book_index = objMsg.get_book_index() # Index of the received book
                            # for i in alread_received: # Check if this book has already been received
                                # if received_book_index == already_received[[i]] and book[[i]] << ObjMsg.get_payload(): # If the previously received book had less length, update the book
                                    # book[[i]]  = ObjMsg.get_payload()
                                # else:
                                    # remain_received[[i]] = remain
                            # already_received[[received_book_index]] = 1
                    # else:
                        # print("Message is None", socket)
                        # break
                # except:
                    # print("Client disconnected", socket)
                    # break

        # def handle_player_send(self,s,client_socket, my_bitfield, other_player_choked): # Send thread
            # def handle():
                # while True:
                    # try:
                        # message = client_socket.recv(1)
                        # if message is not None: 
                            # status, remain, objMsg = message.ComMessage.msg_decode(message) 
                            # if objMsg.get_message_type == 'request' and other_not_choked == True: # Book request
                                # requested_book_index = objMsg.get_book_index()
                                # if bitfield[[requested_book_index]] == 1 and Other_not_choked == True:
                                    # book_message = BookMsg(requested_book_index, book_payload).msg_encode()
                                    # client_socket.sendall(book_message)  
                        # else:
                            # print("Message is None", socket)
                            # break
                    # except:
                        # print("Client disconnected", socket)
                        # break       


class PlayerCommunicationServer(object):
    """
    Manage communication with one player as client.
    Initiate two threads to listen and send to the  player server.
    """
    def __init__(self, player_id, book, client_socket, addr, meta_file, max_connections): # Maximum number of connections
        self.addr = addr
        self.client_socket = client_socket
        self.player_id = player_id
        self.meta_file = meta_file
        self.book = book
        self.q = queue.Queue() 
        self.client_bitfield = None
        
        self.handle_client_listen().start()
        self.handle_client_send().start()
        self.client_player_id = None
        print('start listening to new client')
        
    def handle_client_listen(self):    
        def client():
            remain = b''
            while True:
                msg = utils.read_socket_buffer(self.client_socket)
                if msg != b'':
                    print(msg)
                    full_msg = remain + msg
                    status, remain, objMsg = message.ComMessage.msg_decode(full_msg)  
                    if status == 0:                                         

                        if objMsg.get_message_type() == 'handshake':
                            print('Receive handshake message')
                            self.client_player_id = objMsg.get_player_id()
                            self.q.put((PlayerQMsgEnum.QUEUE_MSG_BITFIELD,None))

                        if objMsg.get_message_type() == 'request':
                            print('Receive request message')
                            book_index = objMsg.get_book_index()
                            self.book.queue_read(book_index, (self.q, PlayerQMsgEnum.QUEUE_MSG_PAYLOAD_READ))
                            
                                                    
        t = Thread(target=client)
        return t          
        
        
    def handle_client_send(self):
        def client():
            state = STATE_INIT            
            while True:
                q_msg_id, info = self.q.get()       
                if q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_BITFIELD.value:
                    bitfield_send = message.BitfieldMsg(self.book.get_bitfield()).msg_encode()
                    print('Send bitfield')
                    self.client_socket.sendall(bitfield_send)                
            
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_PAYLOAD_READ.value :
                    print('Received payload from book')
                    book_index, payload = info
                                      
                    book_send = message.BookMsg(book_index, payload).msg_encode()
                    self.client_socket.sendall(book_send)   

        t = Thread(target=client)
        return t          
        
        
                       
if __name__== "__main__":
    root_dir = sys.argv[1]
    meta_file_path = sys.argv[2]
    player_id = sys.argv[3] 
    print(root_dir)
    print(meta_file_path)
    print(player_id)    
    
    if player_id == 'None':
        player_id = None
    else :
        player_id = player_id.encode()
  
    #player_id = b'-RO0101-7ec7150dddf3'
    main(root_dir, meta_file_path, player_id)
